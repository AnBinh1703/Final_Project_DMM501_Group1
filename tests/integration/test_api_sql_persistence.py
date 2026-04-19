from __future__ import annotations

import asyncio
from pathlib import Path

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_post_json, asgi_request


def test_sql_repository_persists_cases_across_app_restarts(monkeypatch, tmp_path) -> None:
    model_path = Path("artifacts/models/final_model.joblib")
    assert model_path.exists()

    db_path = tmp_path / "case_repo.sqlite"
    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("CASE_REPOSITORY_MODE", "sql")
    monkeypatch.setenv("CASE_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("CASE_DB_AUTO_MIGRATE", "true")
    monkeypatch.delenv("API_AUTH_ENABLED", raising=False)

    created_case_id: str | None = None

    async def first_boot_create_case() -> None:
        nonlocal created_case_id
        async with LifespanManager(app):
            health = await asgi_request(app, method="GET", url="/health")
            assert health.status_code == 200
            assert health.json()["case_repository_mode"] in {"sql_sqlite", "postgresql"}

            monkeypatch.setenv("INTERNAL_EVAL_TOKEN", "test-token")
            sample_resp = await asgi_request(
                app,
                method="GET",
                url="/internal/dataset/samples?n=16&strategy=fraud&seed=19",
                headers={"x-internal-token": "test-token"},
            )
            assert sample_resp.status_code == 200
            samples = sample_resp.json()["samples"]
            assert len(samples) >= 1

            for i, s in enumerate(samples):
                payload = {
                    "transaction_id": f"persist-txn-{i}",
                    "timestamp": "2026-04-18T15:10:00+00:00",
                    "amount": 1700.0,
                    "channel": "internet_banking",
                    "metadata": {"new_beneficiary": True, "device_mismatch": True, "velocity_1h": 9},
                    "features": s["features"],
                }
                r = await asgi_post_json(app, "/predict", payload)
                assert r.status_code == 200
                body = r.json()
                if body["risk_tier"] in {"REVIEW", "HIGH"}:
                    created_case_id = str(body["case_id"])
                    break

            assert created_case_id is not None, "Expected a flagged sample to create a case"

    async def second_boot_verify_case() -> None:
        async with LifespanManager(app):
            assert created_case_id is not None
            case_resp = await asgi_request(app, method="GET", url=f"/cases/{created_case_id}")
            assert case_resp.status_code == 200
            body = case_resp.json()
            assert body["case_id"] == created_case_id
            assert body["risk_tier"] in {"REVIEW", "HIGH"}

    asyncio.run(first_boot_create_case())
    asyncio.run(second_boot_verify_case())
