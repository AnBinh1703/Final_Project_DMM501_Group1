from __future__ import annotations

from typing import Any

from src.repositories.case_repository_protocol import CaseRepositoryProtocol


class CaseService:
    def __init__(self, repository: CaseRepositoryProtocol) -> None:
        self._repository = repository

    @property
    def persistence_mode(self) -> str:
        return str(self._repository.persistence_mode)

    def create_from_prediction(
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
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        if risk_tier not in {"REVIEW", "HIGH"}:
            return None, None

        return self._repository.create_alert_case(
            request_id=request_id,
            transaction_id=transaction_id,
            transaction_timestamp=transaction_timestamp,
            features=features,
            amount=amount,
            channel=channel,
            risk_score=risk_score,
            risk_tier=risk_tier,
            decision_recommendation=decision_recommendation,
            legacy_action=legacy_action,
            reason_codes=reason_codes,
            model_version=model_version,
            model_type=model_type,
            score_semantics=score_semantics,
        )

    def list_alerts(self, *, statuses: set[str] | None, limit: int) -> list[dict[str, Any]]:
        return self._repository.list_alerts(statuses=statuses, limit=limit)

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        return self._repository.get_alert(alert_id)

    def update_alert_status(
        self,
        *,
        alert_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return self._repository.update_alert_status(
            alert_id=alert_id,
            case_status=case_status,
            analyst_note=analyst_note,
            actor=actor,
        )

    def list_cases(self, *, statuses: set[str] | None, limit: int) -> list[dict[str, Any]]:
        return self._repository.list_cases(statuses=statuses, limit=limit)

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        return self._repository.get_case(case_id)

    def update_case_status(
        self,
        *,
        case_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        return self._repository.update_case_status(
            case_id=case_id,
            case_status=case_status,
            analyst_note=analyst_note,
            actor=actor,
        )

    def resolve_case(
        self,
        *,
        case_id: str,
        resolution: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        return self._repository.resolve_case(
            case_id=case_id,
            resolution=resolution,
            analyst_note=analyst_note,
            actor=actor,
        )

    def get_case_timeline(self, case_id: str) -> list[dict[str, Any]]:
        return self._repository.get_case_timeline(case_id)

    def review_queue_size(self) -> int:
        return self._repository.review_queue_size()

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
        self._repository.append_audit_event(
            event_type=event_type,
            actor=actor,
            role=role,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            request_id=request_id,
            case_id=case_id,
            alert_id=alert_id,
            details=details,
        )

    def list_audit_events(
        self,
        *,
        limit: int = 200,
        actor: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._repository.list_audit_events(
            limit=limit,
            actor=actor,
            event_type=event_type,
        )
