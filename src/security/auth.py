from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Callable

from fastapi import Depends, Header, HTTPException, Request

from src.security.audit import append_audit_event_from_request

ALLOWED_ROLES = {"viewer", "analyst", "admin"}
READ_ROLES = ("viewer", "analyst", "admin")
ANALYST_ROLES = ("analyst", "admin")
ADMIN_ROLES = ("admin",)


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def auth_enabled() -> bool:
    return _as_bool(os.getenv("API_AUTH_ENABLED"), False)


@dataclass(frozen=True)
class AuthContext:
    token: str | None
    role: str
    actor: str


def _parse_token_role_mapping(raw: str | None) -> dict[str, str]:
    text = str(raw or "").strip()
    if not text:
        return {}

    mapping: dict[str, str] = {}
    chunks = [c.strip() for c in text.split(",") if c.strip()]
    for chunk in chunks:
        if ":" not in chunk:
            raise RuntimeError(
                "Invalid API_TOKENS format. Expected comma-separated 'token:role' pairs, for example "
                "'viewer-token:viewer,analyst-token:analyst'."
            )
        token, role = chunk.split(":", 1)
        token = token.strip()
        role = role.strip().lower()
        if not token:
            raise RuntimeError("API_TOKENS contains an empty token value")
        if role not in ALLOWED_ROLES:
            raise RuntimeError(f"API_TOKENS contains unsupported role '{role}'. Allowed: {sorted(ALLOWED_ROLES)}")
        mapping[token] = role
    return mapping


def validate_auth_configuration() -> None:
    if not auth_enabled():
        return

    mapping = _parse_token_role_mapping(os.getenv("API_TOKENS"))
    if not mapping:
        raise RuntimeError(
            "API_AUTH_ENABLED=true requires API_TOKENS to be set. "
            "Example: viewer-token:viewer,analyst-token:analyst,admin-token:admin"
        )


def _extract_token(authorization: str | None, x_api_key: str | None) -> str | None:
    bearer = str(authorization or "").strip()
    if bearer:
        prefix = "bearer "
        if bearer.lower().startswith(prefix):
            token = bearer[len(prefix) :].strip()
            if token:
                return token

    api_key = str(x_api_key or "").strip()
    return api_key or None


def _masked(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:3]}***{token[-3:]}"


async def get_auth_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_actor: str | None = Header(default=None),
) -> AuthContext:
    actor = str(x_actor).strip() if x_actor is not None and str(x_actor).strip() else "anonymous"

    if not auth_enabled():
        ctx = AuthContext(token=None, role="admin", actor=actor)
        request.state.auth_context = ctx
        return ctx

    mapping = _parse_token_role_mapping(os.getenv("API_TOKENS"))
    if not mapping:
        raise HTTPException(status_code=500, detail="API auth enabled but API_TOKENS is not configured")

    token = _extract_token(authorization=authorization, x_api_key=x_api_key)
    if token is None:
        append_audit_event_from_request(
            request,
            event_type="AUTH_MISSING_TOKEN",
            status_code=401,
            actor=actor,
            details={"message": "Missing bearer token or x-api-key"},
        )
        raise HTTPException(status_code=401, detail="Missing authentication token")

    role = mapping.get(token)
    if role is None:
        append_audit_event_from_request(
            request,
            event_type="AUTH_INVALID_TOKEN",
            status_code=401,
            actor=actor,
            details={"masked_token": _masked(token)},
        )
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    resolved_actor = actor if actor != "anonymous" else f"{role}:token"
    ctx = AuthContext(token=token, role=role, actor=resolved_actor)
    request.state.auth_context = ctx
    return ctx


def require_roles(*roles: str) -> Callable[..., Any]:
    required = {str(r).strip().lower() for r in roles if str(r).strip()}
    if not required:
        required = set(ALLOWED_ROLES)

    async def _dependency(request: Request, ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.role in required:
            return ctx

        append_audit_event_from_request(
            request,
            event_type="RBAC_FORBIDDEN",
            status_code=403,
            actor=ctx.actor,
            role=ctx.role,
            details={"required_roles": sorted(required), "actual_role": ctx.role},
        )
        raise HTTPException(status_code=403, detail=f"Insufficient role. Required one of: {sorted(required)}")

    return _dependency
