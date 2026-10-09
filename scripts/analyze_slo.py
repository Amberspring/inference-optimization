"""Apply explicit SLOs to saved vLLM measurements; never claim sustained capacity."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def analyze(paths, ttft_ms, e2e_ms, error_rate):
    if ttft_ms <= 0 or e2e_ms <= 0 or not 0 <= error_rate <= 1:
        raise ValueError("Positive latency budgets and error budget in [0,1] required")
    rows = []
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n, completed = data["num_prompts"], data["completed"]
        if n <= 0 or not 0 <= completed <= n:
            raise ValueError("Invalid request counts")
        numbers = [data[k] for k in ("p95_ttft_ms", "p95_e2el_ms", "request_throughput")]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in numbers):
            raise ValueError("Missing or invalid measured latency/throughput")
        rate = 1 - completed / n
        rows.append({"file": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                     "date": data.get("date"), "concurrency": data["max_concurrency"],
                     "model": data["model_id"], "requests": n, "duration_seconds": data["duration"],
                     "input_tokens": data["total_input_tokens"], "output_tokens": data["total_output_tokens"],
                     "p95_ttft_ms": numbers[0], "p95_e2e_ms": numbers[1], "rps": numbers[2], "error_rate": rate,
                     "slo_pass": completed > 0 and numbers[0] <= ttft_ms and numbers[1] <= e2e_ms and rate <= error_rate})
    passed = [r for r in rows if r["slo_pass"]]
    return {"status": "analyzed_existing_measurements", "slo": {"p95_ttft_ms": ttft_ms, "p95_e2e_ms": e2e_ms, "error_rate": error_rate},
            "best_observed": max(passed, key=lambda r: r["rps"]) if passed else None, "rows": rows,
            "limitations": "Only compare files with matching workload and server configuration. Closed-loop short runs do not establish maximum sustainable throughput; repeat longer open-loop tests before capacity claims."}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("files", nargs="+")
    p.add_argument("--ttft-ms", type=float, required=True)
    p.add_argument("--e2e-ms", type=float, required=True)
    p.add_argument("--error-rate", type=float, required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = analyze(a.files, a.ttft_ms, a.e2e_ms, a.error_rate)
    target = Path(a.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["best_observed"]))
