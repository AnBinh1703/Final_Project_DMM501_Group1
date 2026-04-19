from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from src.repositories.case_lifecycle import ACTIVE_REVIEW_STATUSES, VALID_CASE_STATUSES, status_to_event
from src.repositories.migrations import apply_migrations


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_alert_id() -> str:
    return f"ALERT-{uuid4().hex[:12].upper()}"


def _new_case_id() -> str:
    return f"CASE-{uuid4().hex[:12].upper()}"


def _new_timeline_id() -> str:
    return f"TLM-{uuid4().hex[:16].upper()}"


def _new_audit_id() -> str:
    return f"AUD-{uuid4().hex[:16].upper()}"


def _dump_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _load_json_list(raw: Any) -> list[Any]:
    if raw is None:
        return []
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    return list(parsed) if isinstance(parsed, list) else []


def _load_json_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return dict(parsed) if isinstance(parsed, dict) else {}


def _timeline_event(*, event_type: str, actor: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "timeline_id": _new_timeline_id(),
        "event_type": str(event_type),
        "event_time_utc": _utc_now_iso(),
        "actor": str(actor),
        "details": dict(details or {}),
    }


def _status_where_clause(column: str, statuses: set[str] | None) -> tuple[str, dict[str, Any]]:
    if not statuses:
        return "", {}

    values = sorted(str(s) for s in statuses)
    placeholders: list[str] = []
    params: dict[str, Any] = {}
    for idx, value in enumerate(values):
        key = f"status_{idx}"
        placeholders.append(f":{key}")
        params[key] = value

    return f" WHERE {column} IN ({', '.join(placeholders)})", params


class SQLCaseRepository:
    def __init__(
        self,
        database_url: str,
        *,
        auto_migrate: bool = True,
        migrations_dir: Path | None = None,
    ) -> None:
        if not str(database_url).strip():
            raise ValueError("database_url must be provided for SQLCaseRepository")

        self._engine: Engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
        )
        self._dialect = str(self._engine.dialect.name)

        if auto_migrate:
            resolved_dir = migrations_dir or Path(__file__).resolve().parent / "migrations"
            apply_migrations(self._engine, resolved_dir)

    @property
    def persistence_mode(self) -> str:
        if self._dialect == "postgresql":
            return "postgresql"
        return f"sql_{self._dialect}"

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
        case_status = "NEW"

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
                details={"alert_id": alert_id, "case_id": case_id},
            ),
            _timeline_event(
                event_type="CASE_ASSIGNED",
                actor="system",
                details={"case_status": case_status},
            ),
        ]

        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO cases (
                        case_id, alert_id, request_id, transaction_id, transaction_timestamp, features_json,
                        amount, channel, risk_score, risk_tier, decision_recommendation, legacy_action,
                        reason_codes_json, case_status, analyst_note, created_at, updated_at,
                        model_version, model_type, score_semantics
                    ) VALUES (
                        :case_id, :alert_id, :request_id, :transaction_id, :transaction_timestamp, :features_json,
                        :amount, :channel, :risk_score, :risk_tier, :decision_recommendation, :legacy_action,
                        :reason_codes_json, :case_status, :analyst_note, :created_at, :updated_at,
                        :model_version, :model_type, :score_semantics
                    )
                    """
                ),
                {
                    "case_id": case_id,
                    "alert_id": alert_id,
                    "request_id": request_id,
                    "transaction_id": transaction_id,
                    "transaction_timestamp": transaction_timestamp,
                    "features_json": _dump_json(list(features or [])),
                    "amount": amount,
                    "channel": channel,
                    "risk_score": float(risk_score),
                    "risk_tier": risk_tier,
                    "decision_recommendation": decision_recommendation,
                    "legacy_action": legacy_action,
                    "reason_codes_json": _dump_json(list(reason_codes)),
                    "case_status": case_status,
                    "analyst_note": None,
                    "created_at": created_at,
                    "updated_at": created_at,
                    "model_version": model_version,
                    "model_type": model_type,
                    "score_semantics": score_semantics,
                },
            )

            conn.execute(
                text(
                    """
                    INSERT INTO alerts (
                        alert_id, case_id, request_id, transaction_id, transaction_timestamp,
                        amount, channel, risk_score, risk_tier, decision_recommendation, legacy_action,
                        reason_codes_json, case_status, analyst_note, created_at, updated_at
                    ) VALUES (
                        :alert_id, :case_id, :request_id, :transaction_id, :transaction_timestamp,
                        :amount, :channel, :risk_score, :risk_tier, :decision_recommendation, :legacy_action,
                        :reason_codes_json, :case_status, :analyst_note, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "alert_id": alert_id,
                    "case_id": case_id,
                    "request_id": request_id,
                    "transaction_id": transaction_id,
                    "transaction_timestamp": transaction_timestamp,
                    "amount": amount,
                    "channel": channel,
                    "risk_score": float(risk_score),
                    "risk_tier": risk_tier,
                    "decision_recommendation": decision_recommendation,
                    "legacy_action": legacy_action,
                    "reason_codes_json": _dump_json(list(reason_codes)),
                    "case_status": case_status,
                    "analyst_note": None,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )

            for event in timeline:
                conn.execute(
                    text(
                        """
                        INSERT INTO case_timeline (timeline_id, case_id, event_type, event_time_utc, actor, details_json)
                        VALUES (:timeline_id, :case_id, :event_type, :event_time_utc, :actor, :details_json)
                        """
                    ),
                    {
                        "timeline_id": event["timeline_id"],
                        "case_id": case_id,
                        "event_type": event["event_type"],
                        "event_time_utc": event["event_time_utc"],
                        "actor": event["actor"],
                        "details_json": _dump_json(event["details"]),
                    },
                )

            alert = self._fetch_alert_conn(conn, alert_id)
            case = self._fetch_case_conn(conn, case_id, include_timeline=True)

        if alert is None or case is None:
            raise RuntimeError("Failed to load inserted alert/case records from SQL repository")

        return alert, case

    def list_alerts(self, *, statuses: set[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where_clause, params = _status_where_clause("case_status", statuses)
        query = f"""
            SELECT
                alert_id, case_id, request_id, transaction_id, transaction_timestamp,
                amount, channel, risk_score, risk_tier, decision_recommendation, legacy_action,
                reason_codes_json, case_status, analyst_note, created_at, updated_at
            FROM alerts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """
        with self._engine.begin() as conn:
            rows = conn.execute(text(query), {**params, "limit": int(limit)}).mappings().all()
            return [self._map_alert_row(r) for r in rows]

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        with self._engine.begin() as conn:
            return self._fetch_alert_conn(conn, alert_id)

    def list_cases(self, *, statuses: set[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        where_clause, params = _status_where_clause("case_status", statuses)
        query = f"""
            SELECT
                case_id, alert_id, request_id, transaction_id, transaction_timestamp, features_json,
                amount, channel, risk_score, risk_tier, decision_recommendation, legacy_action,
                reason_codes_json, case_status, analyst_note, created_at, updated_at,
                model_version, model_type, score_semantics
            FROM cases
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit
        """
        with self._engine.begin() as conn:
            rows = conn.execute(text(query), {**params, "limit": int(limit)}).mappings().all()
            return [self._map_case_row(r, timeline=None) for r in rows]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._engine.begin() as conn:
            return self._fetch_case_conn(conn, case_id, include_timeline=True)

    def get_case_timeline(self, case_id: str) -> list[dict[str, Any]]:
        with self._engine.begin() as conn:
            return self._fetch_case_timeline_conn(conn, case_id)

    def update_alert_status(
        self,
        *,
        alert_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        with self._engine.begin() as conn:
            existing_alert = self._fetch_alert_conn(conn, alert_id)
            if existing_alert is None:
                return None, None

            case = self._apply_case_status_conn(
                conn,
                case_id=str(existing_alert["case_id"]),
                case_status=case_status,
                analyst_note=analyst_note,
                actor=actor,
                add_case_closed_event=False,
            )
            if case is None:
                return None, None

            alert = self._fetch_alert_conn(conn, alert_id)
            return alert, case

    def update_case_status(
        self,
        *,
        case_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        with self._engine.begin() as conn:
            return self._apply_case_status_conn(
                conn,
                case_id=case_id,
                case_status=case_status,
                analyst_note=analyst_note,
                actor=actor,
                add_case_closed_event=False,
            )

    def resolve_case(
        self,
        *,
        case_id: str,
        resolution: str,
        analyst_note: str | None,
        actor: str,
    ) -> dict[str, Any] | None:
        with self._engine.begin() as conn:
            return self._apply_case_status_conn(
                conn,
                case_id=case_id,
                case_status=resolution,
                analyst_note=analyst_note,
                actor=actor,
                add_case_closed_event=True,
            )

    def review_queue_size(self) -> int:
        statuses = sorted(ACTIVE_REVIEW_STATUSES)
        placeholders = [f":s{i}" for i in range(len(statuses))]
        params = {f"s{i}": status for i, status in enumerate(statuses)}
        query = f"SELECT COUNT(*) FROM cases WHERE case_status IN ({', '.join(placeholders)})"
        with self._engine.begin() as conn:
            count = conn.execute(text(query), params).scalar_one()
        return int(count)

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
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO audit_events (
                        audit_id, event_time_utc, event_type, actor, role, endpoint, method,
                        status_code, request_id, case_id, alert_id, details_json
                    ) VALUES (
                        :audit_id, :event_time_utc, :event_type, :actor, :role, :endpoint, :method,
                        :status_code, :request_id, :case_id, :alert_id, :details_json
                    )
                    """
                ),
                {
                    "audit_id": _new_audit_id(),
                    "event_time_utc": _utc_now_iso(),
                    "event_type": str(event_type),
                    "actor": str(actor or "system"),
                    "role": str(role) if role is not None else None,
                    "endpoint": str(endpoint) if endpoint is not None else None,
                    "method": str(method) if method is not None else None,
                    "status_code": int(status_code) if status_code is not None else None,
                    "request_id": str(request_id) if request_id is not None else None,
                    "case_id": str(case_id) if case_id is not None else None,
                    "alert_id": str(alert_id) if alert_id is not None else None,
                    "details_json": _dump_json(dict(details or {})),
                },
            )

    def list_audit_events(
        self,
        *,
        limit: int = 200,
        actor: str | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {"limit": int(limit)}

        if actor is not None and str(actor).strip():
            clauses.append("actor = :actor")
            params["actor"] = str(actor).strip()

        if event_type is not None and str(event_type).strip():
            clauses.append("UPPER(event_type) = :event_type")
            params["event_type"] = str(event_type).strip().upper()

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        query = f"""
            SELECT
                audit_id, event_time_utc, event_type, actor, role, endpoint, method,
                status_code, request_id, case_id, alert_id, details_json
            FROM audit_events
            {where}
            ORDER BY event_time_utc DESC
            LIMIT :limit
        """

        with self._engine.begin() as conn:
            rows = conn.execute(text(query), params).mappings().all()
            return [self._map_audit_row(r) for r in rows]

    def _fetch_alert_conn(self, conn: Connection, alert_id: str) -> dict[str, Any] | None:
        row = conn.execute(
            text(
                """
                SELECT
                    alert_id, case_id, request_id, transaction_id, transaction_timestamp,
                    amount, channel, risk_score, risk_tier, decision_recommendation, legacy_action,
                    reason_codes_json, case_status, analyst_note, created_at, updated_at
                FROM alerts
                WHERE alert_id = :alert_id
                """
            ),
            {"alert_id": str(alert_id)},
        ).mappings().first()
        return self._map_alert_row(row) if row is not None else None

    def _fetch_case_conn(self, conn: Connection, case_id: str, *, include_timeline: bool) -> dict[str, Any] | None:
        row = conn.execute(
            text(
                """
                SELECT
                    case_id, alert_id, request_id, transaction_id, transaction_timestamp, features_json,
                    amount, channel, risk_score, risk_tier, decision_recommendation, legacy_action,
                    reason_codes_json, case_status, analyst_note, created_at, updated_at,
                    model_version, model_type, score_semantics
                FROM cases
                WHERE case_id = :case_id
                """
            ),
            {"case_id": str(case_id)},
        ).mappings().first()
        if row is None:
            return None

        timeline = self._fetch_case_timeline_conn(conn, str(case_id)) if include_timeline else None
        return self._map_case_row(row, timeline=timeline)

    def _fetch_case_timeline_conn(self, conn: Connection, case_id: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            text(
                """
                SELECT timeline_id, case_id, event_type, event_time_utc, actor, details_json
                FROM case_timeline
                WHERE case_id = :case_id
                ORDER BY event_time_utc ASC, timeline_id ASC
                """
            ),
            {"case_id": str(case_id)},
        ).mappings().all()
        return [
            {
                "event_type": str(r["event_type"]),
                "event_time_utc": str(r["event_time_utc"]),
                "actor": str(r["actor"]),
                "details": _load_json_dict(r["details_json"]),
            }
            for r in rows
        ]

    def _apply_case_status_conn(
        self,
        conn: Connection,
        *,
        case_id: str,
        case_status: str,
        analyst_note: str | None,
        actor: str,
        add_case_closed_event: bool,
    ) -> dict[str, Any] | None:
        resolved_status = str(case_status).strip().upper()
        if resolved_status not in VALID_CASE_STATUSES:
            raise ValueError(f"Unsupported case_status '{case_status}'. Allowed: {sorted(VALID_CASE_STATUSES)}")

        existing_case = self._fetch_case_conn(conn, case_id, include_timeline=False)
        if existing_case is None:
            return None

        updated_at = _utc_now_iso()

        if analyst_note is not None:
            conn.execute(
                text(
                    """
                    UPDATE cases
                    SET case_status = :case_status, analyst_note = :analyst_note, updated_at = :updated_at
                    WHERE case_id = :case_id
                    """
                ),
                {
                    "case_id": case_id,
                    "case_status": resolved_status,
                    "analyst_note": str(analyst_note),
                    "updated_at": updated_at,
                },
            )
            conn.execute(
                text(
                    """
                    UPDATE alerts
                    SET case_status = :case_status, analyst_note = :analyst_note, updated_at = :updated_at
                    WHERE alert_id = :alert_id
                    """
                ),
                {
                    "alert_id": str(existing_case["alert_id"]),
                    "case_status": resolved_status,
                    "analyst_note": str(analyst_note),
                    "updated_at": updated_at,
                },
            )
        else:
            conn.execute(
                text(
                    """
                    UPDATE cases
                    SET case_status = :case_status, updated_at = :updated_at
                    WHERE case_id = :case_id
                    """
                ),
                {
                    "case_id": case_id,
                    "case_status": resolved_status,
                    "updated_at": updated_at,
                },
            )
            conn.execute(
                text(
                    """
                    UPDATE alerts
                    SET case_status = :case_status, updated_at = :updated_at
                    WHERE alert_id = :alert_id
                    """
                ),
                {
                    "alert_id": str(existing_case["alert_id"]),
                    "case_status": resolved_status,
                    "updated_at": updated_at,
                },
            )

        status_event = _timeline_event(
            event_type=status_to_event(resolved_status),
            actor=str(actor or "analyst"),
            details={
                "case_status": resolved_status,
                "analyst_note": str(analyst_note) if analyst_note is not None else existing_case.get("analyst_note"),
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO case_timeline (timeline_id, case_id, event_type, event_time_utc, actor, details_json)
                VALUES (:timeline_id, :case_id, :event_type, :event_time_utc, :actor, :details_json)
                """
            ),
            {
                "timeline_id": status_event["timeline_id"],
                "case_id": case_id,
                "event_type": status_event["event_type"],
                "event_time_utc": status_event["event_time_utc"],
                "actor": status_event["actor"],
                "details_json": _dump_json(status_event["details"]),
            },
        )

        if add_case_closed_event and resolved_status in {
            "CONFIRMED_FRAUD",
            "FALSE_POSITIVE",
            "BLOCKED",
            "RELEASED",
            "RESOLVED",
        }:
            close_event = _timeline_event(
                event_type="CASE_CLOSED",
                actor=str(actor or "analyst"),
                details={"resolution": resolved_status},
            )
            closed_at = close_event["event_time_utc"]

            conn.execute(
                text(
                    """
                    UPDATE cases
                    SET updated_at = :updated_at
                    WHERE case_id = :case_id
                    """
                ),
                {"case_id": case_id, "updated_at": closed_at},
            )
            conn.execute(
                text(
                    """
                    UPDATE alerts
                    SET updated_at = :updated_at
                    WHERE alert_id = :alert_id
                    """
                ),
                {
                    "alert_id": str(existing_case["alert_id"]),
                    "updated_at": closed_at,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO case_timeline (timeline_id, case_id, event_type, event_time_utc, actor, details_json)
                    VALUES (:timeline_id, :case_id, :event_type, :event_time_utc, :actor, :details_json)
                    """
                ),
                {
                    "timeline_id": close_event["timeline_id"],
                    "case_id": case_id,
                    "event_type": close_event["event_type"],
                    "event_time_utc": close_event["event_time_utc"],
                    "actor": close_event["actor"],
                    "details_json": _dump_json(close_event["details"]),
                },
            )

        return self._fetch_case_conn(conn, case_id, include_timeline=True)

    @staticmethod
    def _map_alert_row(row: Any) -> dict[str, Any]:
        return {
            "alert_id": str(row["alert_id"]),
            "case_id": str(row["case_id"]),
            "request_id": str(row["request_id"]),
            "transaction_id": row["transaction_id"],
            "transaction_timestamp": str(row["transaction_timestamp"]),
            "amount": float(row["amount"]) if row["amount"] is not None else None,
            "channel": row["channel"],
            "risk_score": float(row["risk_score"]),
            "risk_tier": str(row["risk_tier"]),
            "decision_recommendation": str(row["decision_recommendation"]),
            "legacy_action": str(row["legacy_action"]),
            "reason_codes": [str(x) for x in _load_json_list(row["reason_codes_json"])],
            "case_status": str(row["case_status"]),
            "analyst_note": row["analyst_note"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _map_case_row(row: Any, *, timeline: list[dict[str, Any]] | None) -> dict[str, Any]:
        out = {
            "case_id": str(row["case_id"]),
            "alert_id": str(row["alert_id"]),
            "request_id": str(row["request_id"]),
            "transaction_id": row["transaction_id"],
            "transaction_timestamp": str(row["transaction_timestamp"]),
            "features": [float(x) for x in _load_json_list(row["features_json"])],
            "amount": float(row["amount"]) if row["amount"] is not None else None,
            "channel": row["channel"],
            "risk_score": float(row["risk_score"]),
            "risk_tier": str(row["risk_tier"]),
            "decision_recommendation": str(row["decision_recommendation"]),
            "legacy_action": str(row["legacy_action"]),
            "reason_codes": [str(x) for x in _load_json_list(row["reason_codes_json"])],
            "case_status": str(row["case_status"]),
            "analyst_note": row["analyst_note"],
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "model_version": str(row["model_version"]),
            "model_type": row["model_type"],
            "score_semantics": str(row["score_semantics"]),
        }
        if timeline is not None:
            out["timeline"] = timeline
        return out

    @staticmethod
    def _map_audit_row(row: Any) -> dict[str, Any]:
        return {
            "audit_id": str(row["audit_id"]),
            "event_time_utc": str(row["event_time_utc"]),
            "event_type": str(row["event_type"]),
            "actor": str(row["actor"]),
            "role": row["role"],
            "endpoint": row["endpoint"],
            "method": row["method"],
            "status_code": int(row["status_code"]) if row["status_code"] is not None else None,
            "request_id": row["request_id"],
            "case_id": row["case_id"],
            "alert_id": row["alert_id"],
            "details": _load_json_dict(row["details_json"]),
        }
