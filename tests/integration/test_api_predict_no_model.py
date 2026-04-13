import asyncio

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_post_json


def test_predict_returns_503_when_model_missing(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)
    monkeypatch.delenv("FRAUD_THRESHOLD", raising=False)
    monkeypatch.delenv("MODEL_VERSION", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_post_json(app, "/predict", {"features": [0.0, 1.0, 2.0]})
            assert r.status_code == 503

    asyncio.run(run())
