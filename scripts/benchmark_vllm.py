"""Use vLLM's own benchmark; never substitute gateway/cache timings for generation."""

import argparse, subprocess, json, shlex
import httpx
from pathlib import Path
from datetime import datetime, timezone

p = argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--label", required=True, choices=["fp16", "awq", "gptq", "int8"])
p.add_argument("--base-url", default="http://127.0.0.1:8000")
p.add_argument("--served-model-name", default="ecommerce-model")
p.add_argument("--execute", action="store_true")
p.add_argument("--prefix-len", type=int, default=0)
p.add_argument("--reset-prefix-cache", action="store_true", help="Reset server cache before each measured run; fail if unsupported")
p.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
a = p.parse_args()
if a.prefix_len < 0 or not a.run_id or any(x in a.run_id for x in ("/", "\\", "..")):
    p.error("prefix length must be nonnegative and run-id must be a plain directory name")
commands = []
for length in (128, 512, 2048):
    for concurrency in (1, 4, 8, 16, 32):
        cmd = [
            "vllm",
            "bench",
            "serve",
            "--backend",
            "vllm",
            "--base-url",
            a.base_url,
            "--model",
            a.model,
            "--served-model-name",
            a.served_model_name,
            "--dataset-name",
            "random",
            "--random-input-len",
            str(length),
            "--random-output-len",
            "128",
            "--random-prefix-len",
            str(a.prefix_len),
            "--num-prompts",
            "100",
            "--max-concurrency",
            str(concurrency),
            "--seed",
            "42",
            "--save-result",
            "--save-detailed",
            "--percentile-metrics",
            "ttft,tpot,itl,e2el",
            "--metric-percentiles",
            "50,95,99",
            "--result-dir",
            str(Path("results/gpu-vllm") / a.run_id),
            "--result-filename",
            f"{a.label}-input{length}-c{concurrency}.json",
        ]
        commands.append(cmd)
        print(shlex.join(cmd))
        if a.execute:
            if a.reset_prefix_cache:
                response = httpx.post(a.base_url.rstrip("/") + "/reset_prefix_cache", timeout=30, trust_env=False)
                response.raise_for_status()
            subprocess.run(cmd, check=True)
Path("results").mkdir(exist_ok=True)
Path("results/gpu-benchmark-plan.json").write_text(
    json.dumps(
        {
            "status": "executed_commands" if a.execute else "planned_not_run",
            "label": a.label,
            "reset_prefix_cache_before_each_run": a.reset_prefix_cache,
            "commands": commands,
            "warning": "Random-token capacity workloads, not customer-service answer quality; TTFT includes queueing and prefill, not isolated GPU prefill time.",
        },
        indent=2,
    ),
    encoding="utf-8",
)
