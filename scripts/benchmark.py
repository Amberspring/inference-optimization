"""Real HTTP closed-loop benchmark. Mock timings are gateway timings, never GPU throughput."""

import argparse, asyncio, json, time, platform, math, uuid
from pathlib import Path
import httpx


def percentile(values, p):
    return sorted(values)[max(0, math.ceil(p * len(values)) - 1)] if values else None


async def bench(url, n, c, hot, task):
    sem = asyncio.Semaphore(c)
    rows = []
    run_id = uuid.uuid4().hex[:12]
    async with httpx.AsyncClient(
        timeout=15, limits=httpx.Limits(max_connections=c)
    ) as client:
        health = (await client.get(url + "/health")).json()

        # Warmup omitted from measured rows; fresh model/corpus version isolates separate runs.
        async def one(i):
            async with sem:
                query = (
                    f"退货怎么办？测试批次{run_id}"
                    if hot
                    else f"取消订单流程，测试批次{run_id}编号{i}"
                )
                start = time.perf_counter()
                try:
                    response = await client.post(
                        url + "/ask", json={"query": query, "task": task}
                    )
                    body = response.json()
                    status = response.status_code
                    tokens = (body.get("usage") or {}).get("completion_tokens")
                    rows.append(
                        {
                            "i": i,
                            "latency_ms": (time.perf_counter() - start) * 1000,
                            "status": status,
                            "cached": body.get("cached", False),
                            "degraded": body.get("degraded", False),
                            "output_tokens": tokens,
                        }
                    )
                except httpx.HTTPError as e:
                    rows.append(
                        {
                            "i": i,
                            "latency_ms": (time.perf_counter() - start) * 1000,
                            "status": 0,
                            "error": type(e).__name__,
                        }
                    )

        start = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(n)))
        elapsed = time.perf_counter() - start
    lat = [r["latency_ms"] for r in rows]
    success = [r for r in rows if r["status"] == 200 and not r.get("degraded")]
    token_rows = [r for r in success if r.get("output_tokens") is not None]
    return {
        "status": "measured",
        "hardware": platform.platform(),
        "server": health,
        "scope": "gateway_mock_cpu" if health["backend"] == "mock" else "http_serving",
        "workload": "hot" if hot else "unique",
        "concurrency": c,
        "requests": n,
        "elapsed_seconds": elapsed,
        "successful_qps": len(success) / elapsed,
        "p50_ms": percentile(lat, 0.5),
        "p95_ms": percentile(lat, 0.95),
        "p99_ms": percentile(lat, 0.99),
        "error_or_degraded_rate": 1 - len(success) / n,
        "cache_hits": sum(r.get("cached", False) for r in rows),
        "output_tokens_per_second": sum(r["output_tokens"] for r in token_rows)
        / elapsed
        if len(token_rows) == len(success) and success
        else None,
        "rows": rows,
    }


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8002")
    p.add_argument("--requests", type=int, default=100)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--hot", action="store_true")
    p.add_argument("--task", default="customer")
    p.add_argument("--output", default="results/benchmark.json")
    a = p.parse_args()
    if a.requests < 1 or a.concurrency < 1:
        raise ValueError("Positive requests and concurrency required")
    out = await bench(a.url.rstrip("/"), a.requests, a.concurrency, a.hot, a.task)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}))


if __name__ == "__main__":
    asyncio.run(main())
