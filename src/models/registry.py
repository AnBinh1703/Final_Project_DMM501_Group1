from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedModel:
    model: object
    threshold_review: float
    threshold_high: float
    model_version: str
    n_features: int | None = None
    feature_columns: list[str] | None = None
    model_type: str | None = None
    dataset_path: str | None = None
    fraud_base_rate: float | None = None
    selection_timestamp_utc: str | None = None
    score_semantics: str = "risk_score_uncalibrated"
    threshold_policy: dict | None = None
    score_percentiles: list[float] | None = None
