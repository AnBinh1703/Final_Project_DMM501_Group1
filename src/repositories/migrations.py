from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy import text


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _split_sql_statements(script: str) -> list[str]:
    lines: list[str] = []
    for raw in script.splitlines():
        stripped = raw.strip()
        if stripped.startswith("--"):
            continue
        lines.append(raw)

    cleaned = "\n".join(lines)
    return [stmt.strip() for stmt in cleaned.split(";") if stmt.strip()]


def apply_migrations(engine: Engine, migrations_dir: Path) -> list[str]:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at_utc TEXT NOT NULL
            )
            """
        )
        rows = conn.exec_driver_sql("SELECT version FROM schema_migrations").fetchall()
        applied = {str(r[0]) for r in rows}

    applied_now: list[str] = []
    for migration in sorted(migrations_dir.glob("*.sql")):
        version = migration.name
        if version in applied:
            continue

        script = migration.read_text(encoding="utf-8")
        statements = _split_sql_statements(script)
        if not statements:
            continue

        with engine.begin() as conn:
            for stmt in statements:
                conn.exec_driver_sql(stmt)
            conn.execute(
                text("INSERT INTO schema_migrations (version, applied_at_utc) VALUES (:version, :applied_at_utc)"),
                {
                    "version": version,
                    "applied_at_utc": _utc_now_iso(),
                },
            )

        applied_now.append(version)

    return applied_now
