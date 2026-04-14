from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedModel:
    model: object
    threshold: float
    model_version: str
    n_features: int | None = None
    feature_columns: list[str] | None = None
    model_type: str | None = None
    dataset_path: str | None = None
    selection_timestamp_utc: str | None = None
