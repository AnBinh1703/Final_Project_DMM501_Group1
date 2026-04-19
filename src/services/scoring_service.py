from __future__ import annotations

import math

from src.features.preprocess import preprocess_feature_vector


def validate_feature_vector(features: list[float]) -> None:
    if any((not isinstance(v, (int, float))) or (not math.isfinite(float(v))) for v in features):
        raise ValueError("All features must be finite numeric values.")


def score_transaction(*, model: object, features: list[float]) -> float:
    if not hasattr(model, "predict_proba"):
        raise ValueError("Loaded model does not support predict_proba")

    X = preprocess_feature_vector(features)
    return float(model.predict_proba(X)[0][1])
