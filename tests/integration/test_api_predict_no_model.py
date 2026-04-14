import asyncio
from pathlib import Path

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_post_json


def test_predict_returns_503_when_model_missing(monkeypatch) -> None:
    # Explicitly set an invalid MODEL_PATH. When MODEL_PATH is set, the loader does not
    # fall back to any local default artifact.
    monkeypatch.setenv("MODEL_PATH", str(Path("artifacts/models/does_not_exist.joblib")))
    monkeypatch.delenv("FRAUD_THRESHOLD", raising=False)
    monkeypatch.delenv("MODEL_VERSION", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_post_json(app, "/predict", {"features": [0.0, 1.0, 2.0]})
            assert r.status_code == 503

    asyncio.run(run())
