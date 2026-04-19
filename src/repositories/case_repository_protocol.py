from __future__ import annotations

from typing import Any, Protocol


class CaseRepositoryProtocol(Protocol):
    @property
    def persistence_mode(self) -> str:
        ...

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
        ...

    def list_alerts(self, *, statuses: set[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        ...

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        ...

    def list_cases(self, *, statuses: set[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        ...

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        ...

    def get_case_timeline(self, case_id: str) -> list[dict[str, Any]]:
        ...

    def update_alert_status(
        self,
        *,
        alert_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        ...

    def update_case_status(
        self,
        *,
        case_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        ...

    def resolve_case(
        self,
        *,
        case_id: str,
        resolution: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        ...

    def review_queue_size(self) -> int:
        ...

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
        ...

    def list_audit_events(
        self,
        *,
        limit: int = 200,
        actor: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        ...
