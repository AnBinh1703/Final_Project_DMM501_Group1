from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoadedModel:
    model: object
    threshold: float
    model_version: str
    n_features: int | None = None
