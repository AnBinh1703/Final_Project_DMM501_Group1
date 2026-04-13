import asyncio

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_request


def test_health_200(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/health")
            assert r.status_code == 200
            body = r.json()
            assert body["status"] == "ok"
            assert "model_loaded" in body

    asyncio.run(run())
