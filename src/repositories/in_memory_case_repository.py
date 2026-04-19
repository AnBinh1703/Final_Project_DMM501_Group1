from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.repositories.case_lifecycle import ACTIVE_REVIEW_STATUSES, VALID_CASE_STATUSES, status_to_event


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_alert_id() -> str:
    return f"ALERT-{uuid4().hex[:12].upper()}"


def _new_case_id() -> str:
    return f"CASE-{uuid4().hex[:12].upper()}"


def _new_audit_id() -> str:
    return f"AUD-{uuid4().hex[:16].upper()}"


def _timeline_event(
    *,
    event_type: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "event_type": str(event_type),
        "event_time_utc": _utc_now_iso(),
        "actor": str(actor),
        "details": details or {},
    }


class InMemoryCaseRepository:
    """
    Demo-grade in-memory persistence for alert and case workflow state.

    The repository intentionally keeps data only in process memory. It is sufficient for
    local demos and API integration tests, but not a production persistence layer.
    """

    def __init__(self) -> None:
        self._alerts: dict[str, dict[str, Any]] = {}
        self._cases: dict[str, dict[str, Any]] = {}
        self._alert_order: list[str] = []
        self._case_order: list[str] = []
        self._audit_events: list[dict[str, Any]] = []

    @property
    def persistence_mode(self) -> str:
        return "in_memory_demo"

    def create_alert_case(
        self,
        *,
        request_id: str,
        transaction_id: str | None,
        transaction_timestamp: str,
        features: list[float] | None,
        amount: float | None,
        channel: str | None,
        risk_score: float,
        risk_tier: str,
        decision_recommendation: str,
        legacy_action: str,
        reason_codes: list[str],
        model_version: str,
        model_type: str | None,
        score_semantics: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        created_at = _utc_now_iso()
        alert_id = _new_alert_id()
        case_id = _new_case_id()
        status = "NEW"

        timeline = [
            _timeline_event(
                event_type="TRANSACTION_RECEIVED",
                actor="system",
                details={
                    "request_id": request_id,
                    "transaction_id": transaction_id,
                    "timestamp": transaction_timestamp,
                    "amount": amount,
                    "channel": channel,
                },
            ),
            _timeline_event(
                event_type="RISK_SCORED",
                actor="system",
                details={
                    "risk_score": risk_score,
                    "risk_tier": risk_tier,
                    "score_semantics": score_semantics,
                    "model_version": model_version,
                    "model_type": model_type,
                },
            ),
            _timeline_event(
                event_type="FLAGGED",
                actor="system",
                details={
                    "risk_tier": risk_tier,
                    "decision_recommendation": decision_recommendation,
                    "reason_codes": list(reason_codes),
                },
            ),
            _timeline_event(
                event_type="ALERT_CREATED",
                actor="system",
                details={
                    "alert_id": alert_id,
                    "case_id": case_id,
                },
            ),
            _timeline_event(
                event_type="CASE_ASSIGNED",
                actor="system",
                details={
                    "case_status": status,
                },
            ),
        ]

        case_record: dict[str, Any] = {
            "case_id": case_id,
            "alert_id": alert_id,
            "request_id": request_id,
            "transaction_id": transaction_id,
            "transaction_timestamp": transaction_timestamp,
            "features": list(features) if features is not None else [],
            "amount": amount,
            "channel": channel,
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "decision_recommendation": decision_recommendation,
            "legacy_action": legacy_action,
            "reason_codes": list(reason_codes),
            "case_status": status,
            "analyst_note": None,
            "created_at": created_at,
            "updated_at": created_at,
            "timeline": timeline,
            "model_version": model_version,
            "model_type": model_type,
            "score_semantics": score_semantics,
        }

        alert_record: dict[str, Any] = {
            "alert_id": alert_id,
            "case_id": case_id,
            "request_id": request_id,
            "transaction_id": transaction_id,
            "transaction_timestamp": transaction_timestamp,
            "amount": amount,
            "channel": channel,
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "decision_recommendation": decision_recommendation,
            "legacy_action": legacy_action,
            "reason_codes": list(reason_codes),
            "case_status": status,
            "analyst_note": None,
            "created_at": created_at,
            "updated_at": created_at,
        }

        self._cases[case_id] = case_record
        self._alerts[alert_id] = alert_record
        self._case_order.insert(0, case_id)
        self._alert_order.insert(0, alert_id)

        return dict(alert_record), self._copy_case(case_record)

    def list_alerts(self, *, statuses: set[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for alert_id in self._alert_order:
            alert = self._alerts.get(alert_id)
            if alert is None:
                continue
            if statuses and str(alert.get("case_status")) not in statuses:
                continue
            out.append(dict(alert))
            if len(out) >= limit:
                break
        return out

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        alert = self._alerts.get(str(alert_id))
        return dict(alert) if alert is not None else None

    def list_cases(self, *, statuses: set[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for case_id in self._case_order:
            case = self._cases.get(case_id)
            if case is None:
                continue
            if statuses and str(case.get("case_status")) not in statuses:
                continue
            out.append(self._copy_case(case, include_timeline=False))
            if len(out) >= limit:
                break
        return out

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        case = self._cases.get(str(case_id))
        return self._copy_case(case) if case is not None else None

    def get_case_timeline(self, case_id: str) -> list[dict[str, Any]]:
        case = self._cases.get(str(case_id))
        if case is None:
            return []
        return [dict(e) for e in case.get("timeline", [])]

    def update_alert_status(
        self,
        *,
        alert_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        alert = self._alerts.get(str(alert_id))
        if alert is None:
            return None, None

        case = self._apply_case_status(
            case_id=str(alert["case_id"]),
            case_status=case_status,
            analyst_note=analyst_note,
            actor=actor,
        )
        if case is None:
            return None, None

        updated_alert = self._alerts.get(str(alert_id))
        return (dict(updated_alert) if updated_alert is not None else None), self._copy_case(case)

    def update_case_status(
        self,
        *,
        case_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        case = self._apply_case_status(
            case_id=case_id,
            case_status=case_status,
            analyst_note=analyst_note,
            actor=actor,
        )
        return self._copy_case(case) if case is not None else None

    def resolve_case(
        self,
        *,
        case_id: str,
        resolution: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        case = self._apply_case_status(
            case_id=case_id,
            case_status=resolution,
            analyst_note=analyst_note,
            actor=actor,
        )
        if case is None:
            return None

        # Append explicit closure event for resolved outcomes.
        if resolution in {"CONFIRMED_FRAUD", "FALSE_POSITIVE", "BLOCKED", "RELEASED", "RESOLVED"}:
            case["timeline"].append(
                _timeline_event(
                    event_type="CASE_CLOSED",
                    actor=actor,
                    details={"resolution": resolution},
                )
            )
            case["updated_at"] = _utc_now_iso()
            alert = self._alerts.get(str(case["alert_id"]))
            if alert is not None:
                alert["updated_at"] = case["updated_at"]

        return self._copy_case(case)

    def review_queue_size(self) -> int:
        return sum(1 for c in self._cases.values() if str(c.get("case_status")) in ACTIVE_REVIEW_STATUSES)

    def append_audit_event(
        self,
        *,
        event_type: str,
        actor: str,
        role: str | None,
        endpoint: str | None,
        method: str | None,
        status_code: int | None,
        request_id: str | None,
        case_id: str | None,
        alert_id: str | None,
        details: dict[str, Any] | None,
    ) -> None:
        event = {
            "audit_id": _new_audit_id(),
            "event_time_utc": _utc_now_iso(),
            "event_type": str(event_type),
            "actor": str(actor),
            "role": str(role) if role is not None else None,
            "endpoint": str(endpoint) if endpoint is not None else None,
            "method": str(method) if method is not None else None,
            "status_code": int(status_code) if status_code is not None else None,
            "request_id": str(request_id) if request_id is not None else None,
            "case_id": str(case_id) if case_id is not None else None,
            "alert_id": str(alert_id) if alert_id is not None else None,
            "details": dict(details or {}),
        }
        self._audit_events.insert(0, event)

    def list_audit_events(
        self,
        *,
        limit: int = 200,
        actor: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        actor_norm = str(actor).strip() if actor is not None else None
        event_type_norm = str(event_type).strip().upper() if event_type is not None else None
        for event in self._audit_events:
            if actor_norm and str(event.get("actor")) != actor_norm:
                continue
            if event_type_norm and str(event.get("event_type", "")).upper() != event_type_norm:
                continue
            out.append(dict(event))
            if len(out) >= int(limit):
                break
        return out

    def _apply_case_status(
        self,
        *,
        case_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        resolved_status = str(case_status).strip().upper()
        if resolved_status not in VALID_CASE_STATUSES:
            raise ValueError(f"Unsupported case_status '{case_status}'. Allowed: {sorted(VALID_CASE_STATUSES)}")

        case = self._cases.get(str(case_id))
        if case is None:
            return None

        case["case_status"] = resolved_status
        case["updated_at"] = _utc_now_iso()
        if analyst_note is not None:
            case["analyst_note"] = str(analyst_note)

        case["timeline"].append(
            _timeline_event(
                event_type=status_to_event(resolved_status),
                actor=str(actor or "analyst"),
                details={"case_status": resolved_status, "analyst_note": case.get("analyst_note")},
            )
        )

        alert = self._alerts.get(str(case.get("alert_id")))
        if alert is not None:
            alert["case_status"] = resolved_status
            alert["updated_at"] = case["updated_at"]
            if analyst_note is not None:
                alert["analyst_note"] = str(analyst_note)

        return case

    @staticmethod
    def _copy_case(case: dict[str, Any], *, include_timeline: bool = True) -> dict[str, Any]:
        copied = dict(case)
        if include_timeline:
            copied["timeline"] = [dict(e) for e in case.get("timeline", [])]
        else:
            copied.pop("timeline", None)
        return copied
