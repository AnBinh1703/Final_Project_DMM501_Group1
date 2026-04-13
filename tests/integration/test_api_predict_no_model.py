from fastapi.testclient import TestClient

from src.api.main import app


def test_predict_returns_503_when_model_missing(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PATH", raising=False)
    monkeypatch.delenv("FRAUD_THRESHOLD", raising=False)
    monkeypatch.delenv("MODEL_VERSION", raising=False)
    with TestClient(app) as client:
        r = client.post("/predict", json={"features": [0.0, 1.0, 2.0]})
        assert r.status_code == 503
