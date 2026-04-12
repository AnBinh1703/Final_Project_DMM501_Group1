from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PreprocessResult:
    X: np.ndarray


def preprocess_feature_vector(features: list[float]) -> np.ndarray:
    # Minimal placeholder: ensures numeric array shape (1, n_features).
    return np.asarray(features, dtype=float).reshape(1, -1)
