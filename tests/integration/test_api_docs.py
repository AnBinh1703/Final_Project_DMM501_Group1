from fastapi.testclient import TestClient

from src.api.main import app


def test_root_redirects_to_docs(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)
    with TestClient(app) as client:
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (302, 307, 308)
        assert r.headers["location"] == "/docs"


def test_docs_available(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)
    with TestClient(app) as client:
        r = client.get("/docs")
        assert r.status_code == 200
        assert "Swagger UI" in r.text

