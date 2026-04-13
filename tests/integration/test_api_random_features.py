import asyncio

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_request


def test_random_features_default_creditcard_shape(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/features/random")
            assert r.status_code == 200
            body = r.json()
            assert body["n_features"] == 30
            assert body["mode"] == "creditcard"
            assert isinstance(body["features"], list)
            assert len(body["features"]) == 30
            assert isinstance(body["time_s"], (int, float))
            assert isinstance(body["amount"], (int, float))

    asyncio.run(run())


def test_random_features_rejects_unknown_mode(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/features/random?mode=nope")
            assert r.status_code == 422

    asyncio.run(run())


def test_random_features_creditcard_requires_30(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/features/random?mode=creditcard&n_features=20")
            assert r.status_code == 422

    asyncio.run(run())


def test_feature_schema_default_30(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/features/schema")
            assert r.status_code == 200
            body = r.json()
            assert body["n_features"] == 30
            assert body["feature_names"][0] == "Time"
            assert body["feature_names"][-1] == "Amount"

    asyncio.run(run())
