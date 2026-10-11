"""Open-loop streaming benchmark for real frozen prompts and a local vLLM endpoint."""

import argparse
import asyncio
import hashlib
import json
import math
import platform
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(p * len(values)) - 1)] if values else None


def load_workload(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("Workload is empty")
    prompts = []
    for i, row in enumerate(rows):
        prompt = row.get("prompt") or row.get("query") or row.get("question")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Workload row {i} lacks prompt/query/question")
        prompts.append({"id": str(row.get("id", i)), "prompt": prompt})
    return prompts


async def stream_one(client, url, model, item, request_id, scheduled, run_started, max_tokens):
    sent = time.perf_counter()
    row = {"request_id": request_id, "item_id": item["id"], "prompt_sha256": hashlib.sha256(item["prompt"].encode()).hexdigest(),
           "scheduled_offset_ms": (scheduled - run_started) * 1000,
           "client_lag_ms": max(0, (sent - scheduled) * 1000)}
    output, first = [], None
    try:
        async with client.stream("POST", url.rstrip("/") + "/chat/completions", json={
            "model": model, "messages": [{"role": "user", "content": item["prompt"]}], "temperature": 0,
            "max_tokens": max_tokens, "stream": True, "stream_options": {"include_usage": True},
            "chat_template_kwargs": {"enable_thinking": False},
        }) as response:
            row["status_code"] = response.status_code
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                chunk = json.loads(line[6:])
                if chunk.get("usage"):
                    row["usage"] = chunk["usage"]
                choice = (chunk.get("choices") or [{}])[0]
                content = (choice.get("delta") or {}).get("content")
                if content:
                    first = first or time.perf_counter()
                    output.append(content)
                if choice.get("finish_reason"):
                    row["finish_reason"] = choice["finish_reason"]
        finished = time.perf_counter()
        finish_reason = row.get("finish_reason")
        if finish_reason == "length":
            status = "truncated"
        elif not finish_reason:
            status = "incomplete"
        elif finish_reason != "stop":
            status = "abnormal_finish"
        else:
            status = "ok" if output else "empty_output"
        row.update(status=status,
                   ttft_ms=(first - sent) * 1000 if first else None,
                   e2e_ms=(finished - sent) * 1000, output="".join(output))
    except (httpx.HTTPError, json.JSONDecodeError) as error:
        row.update(status="error", error=type(error).__name__, e2e_ms=(time.perf_counter() - sent) * 1000)
    return row


def summarize(rows, target_rate, duration, elapsed):
    completed = [row for row in rows if row.get("status") == "ok"]
    all_finished = [row for row in rows if row.get("e2e_ms") is not None]
    ttft = [row["ttft_ms"] for row in completed if row.get("ttft_ms") is not None]
    e2e = [row["e2e_ms"] for row in completed]
    output_tokens = [(row.get("usage") or {}).get("completion_tokens") for row in completed]
    return {
        "scheduled": len(rows), "completed": len(completed), "target_request_rate": target_rate,
        "duration_seconds": duration, "elapsed_seconds": elapsed, "offered_request_rate": len(rows) / duration,
        "achieved_request_rate": len(completed) / elapsed,
        "error_rate": 1 - len(completed) / len(rows), "p50_ttft_ms": percentile(ttft, 0.5),
        "p95_ttft_ms": percentile(ttft, 0.95), "p99_ttft_ms": percentile(ttft, 0.99),
        "p50_e2e_ms": percentile(e2e, 0.5), "p95_e2e_ms": percentile(e2e, 0.95),
        "p99_e2e_ms": percentile(e2e, 0.99),
        "status_counts": {status: sum(row.get("status") == status for row in rows) for status in sorted({row.get("status") for row in rows})},
        "mean_output_tokens": sum(output_tokens) / len(output_tokens) if output_tokens and all(isinstance(x, int) for x in output_tokens) else None,
        "p95_output_tokens": percentile(output_tokens, 0.95) if output_tokens and all(isinstance(x, int) for x in output_tokens) else None,
        "p95_all_finished_e2e_ms": percentile([row["e2e_ms"] for row in all_finished], 0.95),
        "output_tokens_per_second": (sum((row.get("usage") or {}).get("completion_tokens", 0) for row in completed) / elapsed
                                     if all(row.get("usage") for row in completed) and completed else None),
    }


async def run_once(url, model, workload, rate, duration, max_in_flight, max_tokens, seed, warmup):
    limits = httpx.Limits(max_connections=max_in_flight, max_keepalive_connections=max_in_flight)
    timeout = httpx.Timeout(300)
    rng = random.Random(seed)
    order = list(workload)
    rng.shuffle(order)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, trust_env=False) as client:
        for i in range(min(warmup, len(order))):
            warmup_started = time.perf_counter()
            await stream_one(client, url, model, order[i], f"warmup-{i}", warmup_started, warmup_started, max_tokens)
        total = max(1, round(rate * duration))
        epoch = time.perf_counter()
        pending, rows = set(), []
        for i in range(total):
            scheduled = epoch + i / rate
            await asyncio.sleep(max(0, scheduled - time.perf_counter()))
            done = {task for task in pending if task.done()}
            for task in done:
                rows.append(task.result())
            pending -= done
            if len(pending) >= max_in_flight:
                rows.append({"request_id": i, "item_id": order[i % len(order)]["id"], "status": "client_overflow",
                             "scheduled_offset_ms": i / rate * 1000})
                continue
            pending.add(asyncio.create_task(stream_one(
                client, url, model, order[i % len(order)], i, scheduled, epoch, max_tokens
            )))
        if pending:
            rows.extend(await asyncio.gather(*pending))
        elapsed = time.perf_counter() - epoch
    rows.sort(key=lambda row: int(row["request_id"]) if isinstance(row["request_id"], int) else -1)
    return summarize(rows, rate, duration, elapsed), rows


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--server-manifest", required=True)
    parser.add_argument("--request-rate", type=float, required=True)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-in-flight", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.request_rate <= 0 or args.duration < 1 or args.repeats < 1 or args.max_in_flight < 1 or args.max_tokens < 1:
        parser.error("rate, duration, repeats, max-in-flight and max-tokens must be positive")
    workload = load_workload(args.workload)
    server_manifest_path = Path(args.server_manifest)
    server_manifest = json.loads(server_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(server_manifest, dict) or not server_manifest.get("launch_command"):
        parser.error("server-manifest must be a JSON object containing launch_command")
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=False)
    summaries = []
    for repeat in range(args.repeats):
        summary, rows = await run_once(args.url, args.model, workload, args.request_rate, args.duration,
                                       args.max_in_flight, args.max_tokens, args.seed + repeat, args.warmup)
        summary["repeat"] = repeat + 1
        summaries.append(summary)
        (target / f"repeat-{repeat + 1}.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "status": "measured", "created_at": datetime.now(timezone.utc).isoformat(), "model": args.model,
        "endpoint": args.url, "hardware": platform.platform(), "workload_path": str(Path(args.workload)),
        "workload_sha256": hashlib.sha256(Path(args.workload).read_bytes()).hexdigest(), "workload_items": len(workload),
        "server_manifest_path": str(server_manifest_path),
        "server_manifest_sha256": hashlib.sha256(server_manifest_path.read_bytes()).hexdigest(),
        "server": server_manifest,
        "protocol": {"arrival": "constant-rate open loop", "request_rate": args.request_rate, "duration_seconds": args.duration,
                     "repeats": args.repeats, "warmup_requests": args.warmup, "max_in_flight": args.max_in_flight,
                     "temperature": 0, "max_tokens": args.max_tokens, "stream": True, "prefix_cache": "record server launch separately"},
        "runs": summaries,
    }
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
