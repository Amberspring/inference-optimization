import asyncio, httpx, pytest
from fastapi.testclient import TestClient
from gateway.service import Engine, Settings, create_app, TTLCache


def test_cache_and_singleflight():
    async def run():
        e = Engine(Settings(mock_delay=0.02))
        try:
            rows = await asyncio.gather(*(e.ask("退货", "customer") for _ in range(10)))
            assert (
                e.upstream_calls == 1
                and sum(r.get("coalesced", False) for r in rows) == 9
            )
            assert (await e.ask("退货", "customer"))["cached"]
        finally:
            await e.close()

    asyncio.run(run())


@pytest.mark.parametrize("fault", ["oom", "timeout", "unavailable"])
def test_fault_safe_fallback_not_cached(fault):
    async def run():
        e = Engine(Settings(timeout=0.1, mock_delay=0.001))
        e.fault = fault
        try:
            row = await e.ask("query", "customer")
            assert row["degraded"] and row["refused"]
            e.fault = None
            row = await e.ask("query", "customer")
            assert not row["degraded"] and not row["cached"]
        finally:
            await e.close()

    asyncio.run(run())


def test_rate_limit_auth_metrics():
    with TestClient(create_app(Settings(rate=0, burst=1, api_key="test"))) as c:
        assert c.post("/ask", json={"query": "x"}).status_code == 401
        assert (
            c.post(
                "/ask", json={"query": "x"}, headers={"Authorization": "Bearer test"}
            ).status_code
            == 200
        )
        assert (
            c.post(
                "/ask", json={"query": "x"}, headers={"Authorization": "Bearer test"}
            ).status_code
            == 429
        )
        assert "gateway_requests_total" in c.get("/metrics").text


def test_finance_retrieval_and_refusal():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "answer": "收入100亿元 [1]",
                "refused": False,
                "citations": [
                    {"id": 1, "doc_id": "a", "page": 2, "quote": "收入100亿元"}
                ],
            },
        )

    async def run():
        e = Engine(
            Settings(), httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )
        try:
            row = await e.ask("营业收入", "finance")
            assert row["citations"][0]["page"] == 2 and e.upstream_calls == 0
        finally:
            await e.close()

    asyncio.run(run())


def test_invalid_generated_citation_falls_back():
    def handler(req):
        if req.url.path == "/query":
            return httpx.Response(
                200,
                json={
                    "answer": "收入100亿元 [1]",
                    "refused": False,
                    "citations": [
                        {"id": 1, "doc_id": "a", "page": 2, "quote": "收入100亿元"}
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": "收入999亿元 [99]"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"completion_tokens": 5},
            },
        )

    async def run():
        e = Engine(
            Settings(backend="vllm"),
            httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        try:
            row = await e.ask("营业收入", "finance")
            assert row["degraded"] and row["answer"] == "收入100亿元 [1]"
        finally:
            await e.close()

    asyncio.run(run())


def test_cache_expiry():
    async def run():
        cache = TTLCache(ttl=0.001)
        await cache.set("x", {"a": 1})
        await asyncio.sleep(0.01)
        assert await cache.get("x") is None

    asyncio.run(run())


def test_backend_truncation_and_small_model_fallback():
    def handler(req):
        fallback = req.url.port == 8003
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "fallback answer" if fallback else "incomplete"
                        },
                        "finish_reason": "stop" if fallback else "length",
                    }
                ]
            },
        )

    async def run():
        e = Engine(
            Settings(backend="vllm", fallback_url="http://127.0.0.1:8003/v1"),
            httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        try:
            row = await e.ask("订单", "customer")
            assert (
                row["degraded"]
                and row["backend"] == "small_model_fallback"
                and row["answer"] == "fallback answer"
            )
        finally:
            await e.close()

    asyncio.run(run())


def test_deadline_includes_queue():
    async def run():
        e = Engine(Settings(concurrency=1, timeout=0.05, mock_delay=0.03))
        try:
            rows = await asyncio.gather(*(e.ask(str(i), "customer") for i in range(4)))
            assert any(r["degraded"] for r in rows)
        finally:
            await e.close()

    asyncio.run(run())


def test_circuit_breaker():
    async def run():
        e = Engine(Settings())
        e.fault = "oom"
        try:
            for i in range(3):
                assert (await e.ask(str(i), "customer"))["degraded"]
            e.fault = None
            calls = e.upstream_calls
            assert (await e.ask("new", "customer"))[
                "degraded"
            ] and e.upstream_calls == calls
            e.open_until = 0
            assert not (await e.ask("recover", "customer"))["degraded"]
        finally:
            await e.close()

    asyncio.run(run())
