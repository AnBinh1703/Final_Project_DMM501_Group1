from __future__ import annotations

import asyncio
from pathlib import Path

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_post_json, asgi_request


def test_alert_case_lifecycle_endpoints(monkeypatch) -> None:
    model_path = Path("artifacts/models/final_model.joblib")
    assert model_path.exists()
    monkeypatch.setenv("MODEL_PATH", str(model_path))

    async def run() -> None:
        async with LifespanManager(app):
            # Pull fraud-labeled samples from internal dataset endpoint to increase chance of REVIEW/HIGH outcomes.
            monkeypatch.setenv("INTERNAL_EVAL_TOKEN", "test-token")
            sample_resp = await asgi_request(
                app,
                method="GET",
                url="/internal/dataset/samples?n=12&strategy=fraud&seed=13",
                headers={"x-internal-token": "test-token"},
            )
            assert sample_resp.status_code == 200
            samples = sample_resp.json()["samples"]
            assert len(samples) >= 1

            flagged: dict | None = None
            for i, s in enumerate(samples):
                payload = {
                    "transaction_id": f"txn-{i}",
                    "timestamp": "2026-04-18T10:15:30+00:00",
                    "amount": 2500.0,
                    "channel": "internet_banking",
                    "metadata": {"new_beneficiary": True, "device_mismatch": True, "velocity_1h": 7},
                    "features": s["features"],
                }
                r = await asgi_post_json(app, "/predict", payload)
                assert r.status_code == 200
                body = r.json()
                if body["risk_tier"] in {"REVIEW", "HIGH"}:
                    flagged = body
                    break

            assert flagged is not None, "Expected at least one flagged case from fraud samples"
            assert isinstance(flagged["alert_id"], str)
            assert isinstance(flagged["case_id"], str)
            assert flagged["case_status"] == "NEW"

            alert_id = str(flagged["alert_id"])
            case_id = str(flagged["case_id"])

            # Alert listing and lookup.
            alerts_resp = await asgi_request(app, method="GET", url="/alerts?limit=50")
            assert alerts_resp.status_code == 200
            alerts_body = alerts_resp.json()
            assert alerts_body["total"] >= 1
            assert any(a["alert_id"] == alert_id for a in alerts_body["alerts"])

            alert_resp = await asgi_request(app, method="GET", url=f"/alerts/{alert_id}")
            assert alert_resp.status_code == 200
            assert alert_resp.json()["case_id"] == case_id

            # Move case to IN_REVIEW via alert-status endpoint.
            in_review_resp = await asgi_post_json(
                app,
                f"/alerts/{alert_id}/status",
                {
                    "case_status": "IN_REVIEW",
                    "analyst_note": "triage started",
                    "actor": "qa-test",
                },
            )
            assert in_review_resp.status_code == 200
            in_review_case = in_review_resp.json()
            assert in_review_case["case_status"] == "IN_REVIEW"
            assert in_review_case["case_id"] == case_id

            # Resolve as false positive.
            resolve_resp = await asgi_post_json(
                app,
                f"/cases/{case_id}/resolve",
                {
                    "resolution": "FALSE_POSITIVE",
                    "analyst_note": "customer confirmed legitimate transaction",
                    "actor": "qa-test",
                },
            )
            assert resolve_resp.status_code == 200
            resolved_case = resolve_resp.json()
            assert resolved_case["case_status"] == "FALSE_POSITIVE"

            case_resp = await asgi_request(app, method="GET", url=f"/cases/{case_id}")
            assert case_resp.status_code == 200
            case_body = case_resp.json()
            assert case_body["case_status"] == "FALSE_POSITIVE"

            timeline_resp = await asgi_request(app, method="GET", url=f"/cases/{case_id}/timeline")
            assert timeline_resp.status_code == 200
            timeline = timeline_resp.json()["timeline"]
            event_types = {e["event_type"] for e in timeline}
            assert "TRANSACTION_RECEIVED" in event_types
            assert "RISK_SCORED" in event_types
            assert "ALERT_CREATED" in event_types
            assert "INVESTIGATION_STARTED" in event_types
            assert "FALSE_POSITIVE" in event_types
            assert "CASE_CLOSED" in event_types

            health = await asgi_request(app, method="GET", url="/health")
            assert health.status_code == 200
            assert "review_queue_size" in health.json()

    asyncio.run(run())
