"""Benchmark a real Redis server. No fakeredis and no flushdb; delete only own UUID keys."""

import argparse, asyncio, json, time, uuid, platform
from pathlib import Path
from redis.asyncio import Redis


async def run(url, n, concurrency):
    client = Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
    keys = []
    try:
        await client.ping()
        info = await client.info("server")
        if "redis_version" not in info:
            raise RuntimeError("No Redis server metadata")
        sem = asyncio.Semaphore(concurrency)
        rows = []
        prefix = "financial-bench:" + uuid.uuid4().hex + ":"

        async def one(i):
            async with sem:
                key = prefix + str(i)
                keys.append(key)
                value = json.dumps(
                    {
                        "answer": "synthetic financial cache payload",
                        "version": "test-only",
                    }
                )
                start = time.perf_counter()
                await client.set(key, value, ex=60)
                actual = await client.get(key)
                elapsed = time.perf_counter() - start
                assert actual == value.encode()
                rows.append(elapsed * 1000)

        start = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(n)))
        elapsed = time.perf_counter() - start
        return {
            "status": "measured",
            "scope": "actual Redis SET+GET roundtrip, not end-to-end LLM serving",
            "redis_version": info["redis_version"],
            "platform": platform.platform(),
            "n": n,
            "concurrency": concurrency,
            "roundtrips_per_second": n / elapsed,
            "p50_ms": sorted(rows)[max(0, int(n * 0.5) - 1)],
            "p95_ms": sorted(rows)[max(0, int(n * 0.95) - 1)],
            "elapsed_seconds": elapsed,
        }
    finally:
        if keys:
            await client.delete(*keys)
        await client.aclose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="redis://127.0.0.1:6379/0")
    p.add_argument("--requests", type=int, default=1000)
    p.add_argument("--concurrency", type=int, default=16)
    a = p.parse_args()
    if a.requests < 1 or a.concurrency < 1:
        raise ValueError("Positive workload required")
    result = asyncio.run(run(a.url, a.requests, a.concurrency))
    Path("results").mkdir(exist_ok=True)
    Path("results/real-redis-benchmark.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))
