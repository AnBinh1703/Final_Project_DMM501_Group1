from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _safe_read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _resolve_tracking_layout(artifacts_root: Path, model_path: Path) -> tuple[Path, Path, Path, Path]:
    # Preferred layout for full workflow: artifacts/models + artifacts/reports.
    if model_path.parent.name == "models":
        models_dir = model_path.parent
        reports_dir = artifacts_root / "reports"
    else:
        # Fallback layout for simpler training script writing artifacts/model.joblib.
        models_dir = artifacts_root
        reports_dir = artifacts_root

    versions_dir = (models_dir / "versions") if models_dir.name == "models" else (models_dir / "model_versions")
    index_path = versions_dir / "index.json"
    history_jsonl = reports_dir / "model_run_history.jsonl"
    latest_json = reports_dir / "latest_model_run.json"
    return versions_dir, index_path, history_jsonl, latest_json


def register_model_version(
    *,
    artifacts_root: str | Path,
    model_path: str | Path,
    model_info: dict[str, Any],
    run_context: dict[str, Any] | None = None,
    extra_artifacts: list[str | Path] | None = None,
) -> dict[str, Any]:
    """
    Create a unique model version folder and append run-tracking logs.

    Returns a dict with resolved model_version, run_id, and tracking file paths.
    """
    root = Path(artifacts_root)
    model_file = Path(model_path)
    if not model_file.exists():
        raise FileNotFoundError(f"Model artifact not found: {model_file}")

    versions_dir, index_path, history_jsonl, latest_json = _resolve_tracking_layout(root, model_file)
    versions_dir.mkdir(parents=True, exist_ok=True)

    existing_index = _safe_read_json(index_path, default=[])
    if not isinstance(existing_index, list):
        existing_index = []

    max_number = 0
    for item in existing_index:
        if isinstance(item, dict):
            try:
                max_number = max(max_number, int(item.get("version_number", 0)))
            except (TypeError, ValueError):
                continue

    version_number = max_number + 1
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    model_version = f"v{version_number:04d}_{ts}"
    run_id = f"run_{version_number:04d}_{ts}"

    version_dir = versions_dir / model_version
    version_dir.mkdir(parents=True, exist_ok=True)

    # Keep canonical artifact untouched; copy it for immutable per-run traceability.
    versioned_model_path = version_dir / model_file.name
    shutil.copy2(model_file, versioned_model_path)

    merged_model_info = dict(model_info)
    merged_model_info["model_version"] = model_version
    merged_model_info["run_id"] = run_id
    merged_model_info["version_number"] = version_number
    merged_model_info["version_created_utc"] = datetime.now(UTC).isoformat()
    merged_model_info["versioned_model_path"] = str(versioned_model_path)

    version_info_path = version_dir / "model_info.json"
    _write_json(version_info_path, merged_model_info)

    copied_extras: list[str] = []
    for artifact in extra_artifacts or []:
        src = Path(artifact)
        if src.exists() and src.is_file():
            dst = version_dir / src.name
            shutil.copy2(src, dst)
            copied_extras.append(str(dst))

    run_record = {
        "run_id": run_id,
        "model_version": model_version,
        "version_number": version_number,
        "created_utc": datetime.now(UTC).isoformat(),
        "canonical_model_path": str(model_file),
        "versioned_model_path": str(versioned_model_path),
        "model_info_path": str(version_info_path),
        "extra_artifacts": copied_extras,
        "run_context": run_context or {},
    }

    existing_index.append(run_record)
    _write_json(index_path, existing_index)
    _append_jsonl(history_jsonl, run_record)
    _write_json(latest_json, run_record)

    return {
        "run_id": run_id,
        "model_version": model_version,
        "version_number": version_number,
        "version_dir": str(version_dir),
        "index_path": str(index_path),
        "history_jsonl": str(history_jsonl),
        "latest_json": str(latest_json),
        "model_info": merged_model_info,
    }
