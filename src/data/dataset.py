from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification


def generate_synthetic_fraud_dataframe(
    n_samples: int = 12000,
    n_features: int = 20,
    fraud_ratio: float = 0.01,
    random_state: int = 42,
) -> pd.DataFrame:
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=10,
        n_redundant=4,
        n_repeated=0,
        n_classes=2,
        weights=[1.0 - fraud_ratio, fraud_ratio],
        class_sep=1.0,
        random_state=random_state,
    )

    columns = [f"feature_{i}" for i in range(n_features)]
    df = pd.DataFrame(X, columns=columns)
    df["Class"] = np.asarray(y, dtype=int)
    return df


def load_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_training_dataframe(
    data_path: str | Path | None,
    target_col: str = "Class",
    n_samples_if_synthetic: int = 12000,
) -> tuple[pd.DataFrame, str]:
    if data_path:
        path = Path(data_path)
        if path.exists():
            df = pd.read_csv(path)
            source = f"csv:{path}"
        else:
            raise FileNotFoundError(f"Dataset path not found: {path}")
    else:
        df = generate_synthetic_fraud_dataframe(n_samples=n_samples_if_synthetic)
        source = "synthetic:make_classification"

    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' missing from dataset")

    unique_target = sorted(set(df[target_col].dropna().astype(int).tolist()))
    if not set(unique_target).issubset({0, 1}):
        raise ValueError(f"Target column '{target_col}' must be binary with values 0/1")

    return df, source
