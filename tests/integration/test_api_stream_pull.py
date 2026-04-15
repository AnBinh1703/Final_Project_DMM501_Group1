from __future__ import annotations

import asyncio
from pathlib import Path

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_request


def test_stream_pull_returns_scored_events_without_labels(monkeypatch) -> None:
    model_path = Path("artifacts/models/final_model.joblib")
    assert model_path.exists()
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    async def run() -> None:
        async with LifespanManager(app):
            r = await asgi_request(app, method="GET", url="/stream/pull?pace_ms=1000&max_events=25")
            assert r.status_code == 200
            body = r.json()
            assert isinstance(body.get("events"), list)
            assert len(body["events"]) >= 1
            for e in body["events"][:5]:
                assert "class_label" not in e
                assert len(e["features"]) == 30
                assert 0.0 <= float(e["risk_score"]) <= 1.0
                assert e["risk_tier"] in {"LOW", "REVIEW", "HIGH"}
                assert e["action"] in {"allow", "review", "block"}
                assert e["decision_label"] in {"ALLOW", "REVIEW", "BLOCK"}

    asyncio.run(run())

