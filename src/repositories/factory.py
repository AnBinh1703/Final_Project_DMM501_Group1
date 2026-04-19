from __future__ import annotations

import logging
import os

from src.repositories.case_repository_protocol import CaseRepositoryProtocol
from src.repositories.in_memory_case_repository import InMemoryCaseRepository
from src.repositories.sql_case_repository import SQLCaseRepository

LOG = logging.getLogger(__name__)


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    return default


def build_case_repository_from_env() -> CaseRepositoryProtocol:
    mode = str(os.getenv("CASE_REPOSITORY_MODE", "auto")).strip().lower()
    db_url = str(os.getenv("CASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    auto_migrate = _as_bool(os.getenv("CASE_DB_AUTO_MIGRATE"), True)

    if mode in {"in_memory", "memory", "demo"}:
        return InMemoryCaseRepository()

    if mode in {"auto", "postgres", "postgresql", "sql", "database"}:
        if not db_url:
            if mode == "auto":
                return InMemoryCaseRepository()
            raise RuntimeError(
                "CASE_DB_URL (or DATABASE_URL) is required when CASE_REPOSITORY_MODE requests SQL persistence"
            )

        try:
            repo = SQLCaseRepository(db_url, auto_migrate=auto_migrate)
        except Exception:
            if mode == "auto":
                LOG.exception("Failed to initialize SQL repository; falling back to in-memory mode")
                return InMemoryCaseRepository()
            raise

        if mode in {"postgres", "postgresql"} and not repo.persistence_mode.startswith("postgresql"):
            raise RuntimeError(
                f"CASE_REPOSITORY_MODE={mode} requires a PostgreSQL DSN, got persistence_mode={repo.persistence_mode}"
            )

        return repo

    raise ValueError(
        "Unsupported CASE_REPOSITORY_MODE. Use one of: auto, in_memory, postgres, postgresql, sql, database"
    )
