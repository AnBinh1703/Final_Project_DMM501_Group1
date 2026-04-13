from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from src.api.main import app
from src.pipelines.train_pipeline import run_training
from tests.integration.asgi_client import LifespanManager, asgi_post_json, asgi_request


def _train_to_tmp(tmp_path: Path) -> Path:
    artifacts_dir = tmp_path / "artifacts"
    result = run_training(
        data_path=None,
        artifacts_dir=str(artifacts_dir),
        target_col="Class",
        min_precision=0.1,
        n_samples_if_synthetic=500,
        fast=True,
    )
    return Path(result["model_path"])


def test_predict_200_when_model_loaded(monkeypatch, tmp_path: Path) -> None:
    model_path = _train_to_tmp(tmp_path)

    # Force a deterministic threshold behavior for the test.
    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("MODEL_VERSION", "test-model")
    monkeypatch.setenv("FRAUD_THRESHOLD", "0.0")

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
            assert body["model_version"] == "test-model"
            assert 0.0 <= float(body["fraud_probability"]) <= 1.0
            assert int(body["fraud_label"]) == 1  # threshold=0.0 => always 1

            metrics = await asgi_request(app, method="GET", url="/metrics")
            assert metrics.status_code == 200
            text = metrics.text
            assert "api_requests_total" in text
            assert "api_request_latency_seconds_bucket" in text

    asyncio.run(run())


def test_predict_422_on_feature_length_mismatch(monkeypatch, tmp_path: Path) -> None:
    model_path = _train_to_tmp(tmp_path)
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    async def run() -> None:
        async with LifespanManager(app):
            health = await asgi_request(app, method="GET", url="/health")
            assert health.status_code == 200
            expected_features = int(health.json()["expected_features"])
            r = await asgi_post_json(app, "/predict", {"features": [0.0] * (expected_features + 1)})
            assert r.status_code == 422

    asyncio.run(run())
