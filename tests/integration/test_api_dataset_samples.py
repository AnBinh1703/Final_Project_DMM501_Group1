from __future__ import annotations

import asyncio
from pathlib import Path

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_request


def test_dataset_samples_200_and_shape(monkeypatch) -> None:
    model_path = Path("artifacts/models/final_model.joblib")
    assert model_path.exists()
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/dataset/samples?n=4&strategy=mixed&seed=7")
            assert r.status_code == 200
            body = r.json()
            assert body["n_features"] == 30
            assert body["feature_names"][0] == "Time"
            assert body["feature_names"][-1] == "Amount"
            assert isinstance(body["samples"], list)
            assert len(body["samples"]) >= 1
            for s in body["samples"]:
                assert len(s["features"]) == 30
                assert s["class_label"] in (0, 1)

    asyncio.run(run())

