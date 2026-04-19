from __future__ import annotations

from typing import Any

from fastapi import Request

from src.services.case_service import CaseService


def _resolve_actor_role(request: Request) -> tuple[str, str | None]:
    ctx = getattr(request.state, "auth_context", None)
    if ctx is not None:
        actor = str(getattr(ctx, "actor", "") or "anonymous")
        role = getattr(ctx, "role", None)
        return actor, str(role) if role is not None else None

    actor = str(request.headers.get("x-actor") or "anonymous")
    return actor, None


def append_audit_event_from_request(
    request: Request,
    *,
    event_type: str,
    status_code: int | None,
    request_id: str | None = None,
    case_id: str | None = None,
    alert_id: str | None = None,
    details: dict[str, Any] | None = None,
    actor: str | None = None,
    role: str | None = None,
) -> None:
    case_service: CaseService | None = getattr(request.app.state, "case_service", None)
    if case_service is None:
        return

    try:
        resolved_actor, resolved_role = _resolve_actor_role(request)
        case_service.append_audit_event(
            event_type=event_type,
            actor=str(actor or resolved_actor),
            role=str(role) if role is not None else resolved_role,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            request_id=request_id,
            case_id=case_id,
            alert_id=alert_id,
            details=dict(details or {}),
        )
    except Exception:
        # Audit logging must never break API response flow.
        return
