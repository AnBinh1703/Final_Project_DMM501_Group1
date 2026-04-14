from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_post_json, asgi_request


def _final_model_path() -> Path:
    p = Path("artifacts/models/final_model.joblib")
    if not p.exists():
        raise RuntimeError("Expected final model artifact missing at artifacts/models/final_model.joblib")
    return p


def test_predict_200_when_model_loaded(monkeypatch) -> None:
    model_path = _final_model_path()
    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_VERSION", "final-artifact")
    monkeypatch.delenv("FRAUD_THRESHOLD", raising=False)

    async def run() -> None:
        async with LifespanManager(app):
            health = await asgi_request(app, method="GET", url="/health")
            assert health.status_code == 200
            assert health.json()["model_loaded"] is True

            expected_features = int(health.json()["expected_features"])
            features = np.zeros((expected_features,), dtype=float).tolist()

            r = await asgi_post_json(app, "/predict", {"features": features})
            assert r.status_code == 200
            body = r.json()
            assert body["model_version"] == "final-artifact"
            assert 0.0 <= float(body["fraud_probability"]) <= 1.0
            assert float(body["threshold"]) == 0.99
            assert int(body["n_features"]) == expected_features
            assert isinstance(body["feature_names"], list)
            assert len(body["feature_names"]) == expected_features

            # Same request via features_by_name must produce the same probability regardless of dict order.
            by_name = {name: 0.0 for name in reversed(body["feature_names"])}
            r2 = await asgi_post_json(app, "/predict", {"features_by_name": by_name})
            assert r2.status_code == 200
            body2 = r2.json()
            assert abs(float(body2["fraud_probability"]) - float(body["fraud_probability"])) < 1e-12

            metrics = await asgi_request(app, method="GET", url="/metrics")
            assert metrics.status_code == 200
            text = metrics.text
            assert "api_requests_total" in text
            assert "api_request_latency_seconds_bucket" in text

    asyncio.run(run())


def test_predict_422_on_feature_length_mismatch(monkeypatch) -> None:
    model_path = _final_model_path()
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    async def run() -> None:
        async with LifespanManager(app):
            health = await asgi_request(app, method="GET", url="/health")
            assert health.status_code == 200
            expected_features = int(health.json()["expected_features"])
            r = await asgi_post_json(app, "/predict", {"features": [0.0] * (expected_features + 1)})
            assert r.status_code == 422

    asyncio.run(run())
