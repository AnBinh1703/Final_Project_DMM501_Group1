from fastapi.testclient import TestClient

from src.api.main import app


def test_predict_returns_503_when_model_missing() -> None:
    client = TestClient(app)
    r = client.post("/predict", json={"features": [0.0, 1.0, 2.0]})
    assert r.status_code == 503
