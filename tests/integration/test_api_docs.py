import asyncio

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_request


def test_root_redirects_to_docs(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/")
            assert r.status_code in (302, 307, 308)
            assert r.headers.get("location") == "/docs"

    asyncio.run(run())


def test_docs_available(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/docs")
            assert r.status_code == 200
            assert "Swagger UI" in r.text

    asyncio.run(run())
