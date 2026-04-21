from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

import numpy as np
import pandas as pd


@lru_cache(maxsize=4)
def _load_dataset_cached(path_str: str, feature_columns: tuple[str, ...], target_col: str) -> pd.DataFrame:
    usecols = list(feature_columns)
    if target_col not in usecols:
        usecols.append(target_col)
    return pd.read_csv(path_str, usecols=usecols)


def resolve_dataset_path(dataset_path: str, repo_root: Path) -> Path:
    # Metadata can be produced on Windows and consumed on Linux CI.
    # Normalize separators so "data\\archive\\creditcard.csv" resolves cross-platform.
    p = Path(dataset_path.replace("\\", "/")).expanduser()
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def resolve_effective_dataset_path(*, model_dataset_path: str | None, repo_root: Path) -> Path | None:
    env_path = os.getenv("DATASET_CSV_PATH", "").strip()
    if env_path:
        return resolve_dataset_path(env_path, repo_root=repo_root)

    if model_dataset_path and str(model_dataset_path).strip():
        return resolve_dataset_path(str(model_dataset_path).strip(), repo_root=repo_root)

    return None


def sample_dataset_rows(
    *,
    dataset_path: Path,
    feature_columns: list[str],
    n: int,
    strategy: str,
    seed: int | None,
    target_col: str = "Class",
    include_label: bool = False,
) -> list[dict]:
    if n < 1:
        raise ValueError("n must be >= 1")

    allowed = {"mixed", "fraud", "legit", "production"}
    if strategy not in allowed:
        raise ValueError(f"Invalid strategy '{strategy}'. Allowed: {sorted(allowed)}")

    df = _load_dataset_cached(str(dataset_path), tuple(feature_columns), target_col)
    if target_col not in df.columns:
        raise ValueError(f"Dataset missing target column '{target_col}'")

    rng = np.random.default_rng(seed)
    fraud_df = df[df[target_col] == 1]
    legit_df = df[df[target_col] == 0]

    if strategy == "fraud":
        pool = fraud_df
        if pool.empty:
            raise ValueError("No fraud samples found in dataset")
        idx = rng.choice(pool.index.to_numpy(), size=min(n, len(pool)), replace=False)
        picked = pool.loc[idx]
    elif strategy == "legit":
        pool = legit_df
        if pool.empty:
            raise ValueError("No legitimate samples found in dataset")
        idx = rng.choice(pool.index.to_numpy(), size=min(n, len(pool)), replace=False)
        picked = pool.loc[idx]
    elif strategy == "production":
        # Approximate production-like sampling at the observed base rate.
        # For small n, this will usually return all legitimate samples, which is the expected behavior.
        if legit_df.empty and fraud_df.empty:
            raise ValueError("Dataset contains no samples")
        p_fraud = float(len(fraud_df) / max(len(df), 1))

        rows = []
        for _ in range(n):
            want_fraud = bool(rng.random() < p_fraud)
            pool = fraud_df if want_fraud and not fraud_df.empty else legit_df if not legit_df.empty else fraud_df
            idx = rng.choice(pool.index.to_numpy(), size=1, replace=False)
            rows.append(pool.loc[idx])
        picked = pd.concat(rows, axis=0)
    else:
        n_fraud = min(max(1, n // 2), len(fraud_df)) if len(fraud_df) else 0
        n_legit = min(n - n_fraud, len(legit_df)) if len(legit_df) else 0
        parts = []
        if n_fraud:
            idx_f = rng.choice(fraud_df.index.to_numpy(), size=n_fraud, replace=False)
            parts.append(fraud_df.loc[idx_f])
        if n_legit:
            idx_l = rng.choice(legit_df.index.to_numpy(), size=n_legit, replace=False)
            parts.append(legit_df.loc[idx_l])
        if not parts:
            raise ValueError("Dataset contains no samples")
        picked = pd.concat(parts, axis=0).sample(frac=1.0, random_state=int(rng.integers(0, 2**31 - 1)))

    out: list[dict] = []
    for _, row in picked.iterrows():
        feats = [float(row[c]) for c in feature_columns]
        payload: dict = {"features": feats}
        if include_label:
            payload["class_label"] = int(row[target_col])
        out.append(payload)
    return out
