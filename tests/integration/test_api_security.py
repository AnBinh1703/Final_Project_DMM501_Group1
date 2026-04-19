from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.api.main import app
from tests.integration.asgi_client import LifespanManager, asgi_request


TOKENS = {
    "viewer": "viewer-token",
    "analyst": "analyst-token",
    "admin": "admin-token",
}


def _auth_headers(role: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    token = TOKENS[role]
    headers = {
        "authorization": f"Bearer {token}",
        "x-actor": f"itest-{role}",
    }
    if extra:
        headers.update(extra)
    return headers


async def _post_json_with_headers(url: str, payload: dict, headers: dict[str, str]):
    return await asgi_request(
        app,
        method="POST",
        url=url,
        headers={**headers, "content-type": "application/json"},
        body=json.dumps(payload).encode("utf-8"),
    )


def _configure_security_env(monkeypatch) -> None:
    model_path = Path("artifacts/models/final_model.joblib")
    assert model_path.exists()

    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("CASE_REPOSITORY_MODE", "in_memory")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv(
        "API_TOKENS",
        "viewer-token:viewer,analyst-token:analyst,admin-token:admin",
    )
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "60")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")


def test_auth_rbac_and_audit_trail(monkeypatch) -> None:
    _configure_security_env(monkeypatch)

    async def run() -> None:
        async with LifespanManager(app):
            unauthorized = await asgi_request(app, method="GET", url="/cases?limit=5")
            assert unauthorized.status_code == 401

            monkeypatch.setenv("INTERNAL_EVAL_TOKEN", "test-token")
            samples_resp = await asgi_request(
                app,
                method="GET",
                url="/internal/dataset/samples?n=10&strategy=fraud&seed=29",
                headers=_auth_headers("viewer", {"x-internal-token": "test-token"}),
            )
            assert samples_resp.status_code == 200
            samples = samples_resp.json()["samples"]
            assert len(samples) >= 1

            flagged_case_id: str | None = None
            flagged_alert_id: str | None = None
            for idx, sample in enumerate(samples):
                payload = {
                    "transaction_id": f"sec-case-{idx}",
                    "timestamp": "2026-04-18T15:30:00+00:00",
                    "amount": 2100.0,
                    "channel": "internet_banking",
                    "metadata": {"new_beneficiary": True, "device_mismatch": True, "velocity_1h": 8},
                    "features": sample["features"],
                }
                pred = await _post_json_with_headers("/predict", payload, _auth_headers("viewer"))
                assert pred.status_code == 200
                body = pred.json()
                if body["risk_tier"] in {"REVIEW", "HIGH"}:
                    flagged_case_id = str(body["case_id"])
                    flagged_alert_id = str(body["alert_id"])
                    break

            assert flagged_case_id is not None
            assert flagged_alert_id is not None

            list_cases = await asgi_request(app, method="GET", url="/cases?limit=10", headers=_auth_headers("viewer"))
            assert list_cases.status_code == 200

            forbidden = await _post_json_with_headers(
                f"/cases/{flagged_case_id}/resolve",
                {
                    "resolution": "FALSE_POSITIVE",
                    "analyst_note": "viewer should not be able to resolve",
                    "actor": "itest-viewer",
                },
                _auth_headers("viewer"),
            )
            assert forbidden.status_code == 403

            resolved = await _post_json_with_headers(
                f"/cases/{flagged_case_id}/resolve",
                {
                    "resolution": "FALSE_POSITIVE",
                    "analyst_note": "analyst resolved case",
                    "actor": "itest-analyst",
                },
                _auth_headers("analyst"),
            )
            assert resolved.status_code == 200
            assert resolved.json()["case_status"] == "FALSE_POSITIVE"

            non_admin_audit = await asgi_request(
                app,
                method="GET",
                url="/audit/events?limit=20",
                headers=_auth_headers("analyst"),
            )
            assert non_admin_audit.status_code == 403

            admin_audit = await asgi_request(
                app,
                method="GET",
                url="/audit/events?limit=100",
                headers=_auth_headers("admin"),
            )
            assert admin_audit.status_code == 200
            events = admin_audit.json()["events"]
            event_types = {e["event_type"] for e in events}
            assert "RBAC_FORBIDDEN" in event_types
            assert "CASE_RESOLVED" in event_types

    asyncio.run(run())


def test_rate_limiting_enforced(monkeypatch) -> None:
    _configure_security_env(monkeypatch)
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    async def run() -> None:
        async with LifespanManager(app):
            r1 = await asgi_request(app, method="GET", url="/cases?limit=1", headers=_auth_headers("viewer"))
            r2 = await asgi_request(app, method="GET", url="/cases?limit=1", headers=_auth_headers("viewer"))
            r3 = await asgi_request(app, method="GET", url="/cases?limit=1", headers=_auth_headers("viewer"))

            assert r1.status_code == 200
            assert r2.status_code == 200
            assert r3.status_code == 429

            admin_audit = await asgi_request(
                app,
                method="GET",
                url="/audit/events?limit=20&event_type=RATE_LIMIT_EXCEEDED",
                headers=_auth_headers("admin"),
            )
            assert admin_audit.status_code == 200
            assert admin_audit.json()["total"] >= 1

    asyncio.run(run())
