from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib

from src.models.registry import LoadedModel


def _read_metadata(model_path: Path) -> dict[str, Any]:
    candidate_paths = [
        model_path.with_name("model_info.json"),
        model_path.with_suffix(model_path.suffix + ".metadata.json"),
    ]
    for metadata_path in candidate_paths:
        if metadata_path.exists():
            try:
                return json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
    return {}


def load_model_from_path(model_path: str | Path, threshold: float | None, model_version: str | None) -> LoadedModel:
    path = Path(model_path)
    model: Any = joblib.load(path)
    metadata = _read_metadata(path)

    resolved_threshold = float(threshold if threshold is not None else metadata.get("threshold", 0.5))
    resolved_version = str(
        model_version
        if model_version is not None
        else metadata.get("model_version")
        if metadata.get("model_version")
        else path.stem
    )

    n_features = metadata.get("n_features")
    if n_features is None and hasattr(model, "n_features_in_"):
        n_features = int(getattr(model, "n_features_in_"))

    return LoadedModel(
        model=model,
        threshold=resolved_threshold,
        model_version=resolved_version,
        n_features=int(n_features) if n_features is not None else None,
        feature_columns=list(metadata.get("feature_columns")) if isinstance(metadata.get("feature_columns"), list) else None,
        model_type=str(metadata.get("model_type")) if metadata.get("model_type") is not None else None,
        dataset_path=str(metadata.get("dataset_path")) if metadata.get("dataset_path") is not None else None,
        selection_timestamp_utc=str(metadata.get("selection_timestamp_utc"))
        if metadata.get("selection_timestamp_utc") is not None
        else None,
    )


def maybe_load_model_from_env() -> LoadedModel | None:
    # If MODEL_PATH is explicitly set, follow it strictly (no fallback).
    model_path = os.getenv("MODEL_PATH")
    if model_path is not None:
        model_path = model_path.strip()
        if not model_path:
            return None

        env_threshold = os.getenv("FRAUD_THRESHOLD")
        threshold = float(env_threshold) if env_threshold is not None else None
        model_version = os.getenv("MODEL_VERSION")

        path = Path(model_path)
        if not path.exists():
            return None

        return load_model_from_path(path, threshold=threshold, model_version=model_version)

    # Otherwise: best-effort local default to the final training artifact.
    repo_root = Path(__file__).resolve().parents[2]
    default_candidates = [
        repo_root / "artifacts" / "models" / "final_model.joblib",
        repo_root / "artifacts" / "model.joblib",
    ]
    for candidate in default_candidates:
        if candidate.exists():
            return load_model_from_path(candidate, threshold=None, model_version=None)

    return None
