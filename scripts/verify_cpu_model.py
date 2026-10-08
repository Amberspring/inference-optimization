"""Validate project-one tiny model, project-two retrieval and project-three gateway over HTTP."""

import argparse, json
from pathlib import Path
import httpx

p = argparse.ArgumentParser()
p.add_argument("--model-url", default="http://127.0.0.1:8000")
p.add_argument("--gateway-url", default="http://127.0.0.1:8002")
p.add_argument("--output", default="results/tiny-model-integration.json")
a = p.parse_args()
with httpx.Client(timeout=60) as c:
    health = c.get(a.model_url + "/health")
    health.raise_for_status()
    direct = c.post(
        a.model_url + "/v1/chat/completions",
        json={
            "model": "tiny-qwen3",
            "messages": [{"role": "user", "content": "refund"}],
            "max_tokens": 16,
        },
    )
    direct.raise_for_status()
    customer = c.post(
        a.gateway_url + "/ask", json={"query": "refund", "task": "customer"}
    )
    customer.raise_for_status()
    finance = c.post(
        a.gateway_url + "/ask",
        json={"query": "星河科技2025年营业收入是多少？", "task": "finance"},
    )
    finance.raise_for_status()
    assert direct.json()["usage"]["completion_tokens"] > 0
    assert finance.json()["citations"]
    target = Path(a.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "status": "measured",
                "scope": "real_trained_random_tiny_qwen3_CPU_HTTP_integration_not_8B_quality",
                "model_health": health.json(),
                "direct_model": direct.json(),
                "gateway_customer": customer.json(),
                "gateway_finance": finance.json(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
