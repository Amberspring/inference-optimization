import asyncio, json, time
from pathlib import Path
from gateway.service import Engine, Settings


async def main():
    rows = []
    for fault in ("oom", "timeout", "unavailable"):
        e = Engine(Settings(timeout=0.05))
        e.fault = fault
        start = time.perf_counter()
        try:
            failed = await e.ask("故障演练", "customer")
            e.fault = None
            recovered = await e.ask("故障演练", "customer")
            assert failed["degraded"] and not recovered["degraded"]
            rows.append(
                {
                    "fault": fault,
                    "injection": "in_process_exception_not_real_GPU_fault",
                    "safe_fallback": failed["degraded"],
                    "recovered": not recovered["degraded"],
                    "seconds": time.perf_counter() - start,
                }
            )
        finally:
            await e.close()
    Path("results").mkdir(exist_ok=True)
    Path("results/fault-drill.json").write_text(
        json.dumps(
            {"status": "measured", "scope": "synthetic_fault_injection", "runs": rows},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    asyncio.run(main())
