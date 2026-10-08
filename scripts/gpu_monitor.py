import argparse, subprocess, time, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--seconds", type=float, default=60)
p.add_argument("--output", default="results/gpu-memory.json")
a = p.parse_args()
rows = []
end = time.monotonic() + a.seconds
while time.monotonic() < end:
    r = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,name,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in r.stdout.splitlines():
        i, name, used, util = [v.strip() for v in line.split(",")]
        rows.append(
            {
                "timestamp": time.time(),
                "gpu": i,
                "name": name,
                "used_mib": float(used),
                "utilization_percent": float(util),
            }
        )
    time.sleep(0.2)
p = Path(a.output)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(
    json.dumps(
        {
            "status": "measured",
            "scope": "nvidia-smi_total_device_usage_not_process_allocated_memory",
            "samples": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
