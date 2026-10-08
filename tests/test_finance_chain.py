import asyncio
import json
import httpx
from gateway.service import Engine, Settings


def test_numeric_finance_uses_controlled_result_and_separate_cache():
    async def check():
        requests = []
        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            if request.url.path == "/query":
                return httpx.Response(200, json={"refused": False, "answer": "20 percent", "value": "20", "unit": "percent",
                                                "citations": [{"id": 1, "quote": "20 percent"}]})
            assert body["model"] == "base-finance"
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "20 percent [1]"}}]})
        engine = Engine(Settings(backend="openai", model="ecommerce-dpo", finance_model="base-finance"),
                        httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        try:
            result = await engine.ask("growth", "auto", True)
            assert result["backend"] == "evidence_calculator" and result["value"] == "20" and len(requests) == 1
            assert requests[0]["calculate"] is True
            extractive = await engine.ask("growth", "finance")
            assert not extractive["cached"] and len(requests) == 3
            assert (await engine.ask("growth", "auto", True))["cached"]
        finally:
            await engine.close()
    asyncio.run(check())
