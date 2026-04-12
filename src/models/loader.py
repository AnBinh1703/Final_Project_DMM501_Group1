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
    resolved_version = str(model_version if model_version is not None else metadata.get("model_version", "unknown"))

    n_features = metadata.get("n_features")
    if n_features is None and hasattr(model, "n_features_in_"):
        n_features = int(getattr(model, "n_features_in_"))

    return LoadedModel(
        model=model,
        threshold=resolved_threshold,
        model_version=resolved_version,
        n_features=int(n_features) if n_features is not None else None,
    )


def maybe_load_model_from_env() -> LoadedModel | None:
    model_path = os.getenv("MODEL_PATH")
    if not model_path:
        return None

    env_threshold = os.getenv("FRAUD_THRESHOLD")
    threshold = float(env_threshold) if env_threshold is not None else None
    model_version = os.getenv("MODEL_VERSION")

    path = Path(model_path)
    if not path.exists():
        return None

    return load_model_from_path(path, threshold=threshold, model_version=model_version)
