from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

RandomFeatureMode = Literal["auto", "creditcard", "normal"]


@dataclass(frozen=True)
class RandomFeaturesResult:
    features: list[float]
    mode: str
    time_s: float | None = None
    amount: float | None = None


def generate_random_features(
    *,
    n_features: int,
    mode: RandomFeatureMode = "auto",
    seed: int | None = None,
) -> RandomFeaturesResult:
    if n_features < 1:
        raise ValueError("n_features must be >= 1")

    rng = np.random.default_rng(seed)

    resolved_mode: str
    if mode == "auto":
        resolved_mode = "creditcard" if n_features == 30 else "normal"
    else:
        resolved_mode = mode

    if resolved_mode == "creditcard":
        if n_features != 30:
            raise ValueError("creditcard mode requires n_features=30 ([Time, V1..V28, Amount])")

        time_s = float(rng.uniform(0.0, 172800.0))  # 48 hours

        # PCA-like features: Normal(0,1) with a small chance of heavier tail.
        v = rng.standard_normal(28)
        heavy_tail_mask = rng.uniform(size=28) < 0.02
        if heavy_tail_mask.any():
            v = v + heavy_tail_mask.astype(float) * rng.standard_normal(28) * 2.5

        # Amount: log-normal, skewed positive distribution.
        amount = float(math.exp(3.8 + 1.1 * float(rng.standard_normal())))
        amount = max(0.01, amount)

        features = [time_s, *[float(x) for x in v.tolist()], amount]
        return RandomFeaturesResult(features=features, mode=resolved_mode, time_s=time_s, amount=amount)

    if resolved_mode == "normal":
        x = rng.standard_normal(n_features).astype(float)
        return RandomFeaturesResult(features=[float(v) for v in x.tolist()], mode=resolved_mode)

    raise ValueError(f"Unsupported mode: {mode}")

