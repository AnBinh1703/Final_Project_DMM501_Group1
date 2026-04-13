from fastapi.testclient import TestClient

from src.api.main import app


def test_health_200(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "model_loaded" in body
