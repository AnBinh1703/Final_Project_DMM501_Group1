from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _write_synthetic_creditcard_csv(path: Path, *, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    n_rows = 640

    df = pd.DataFrame(
        {
            "Time": rng.uniform(0.0, 172800.0, size=n_rows),
            **{f"V{i}": rng.normal(0.0, 1.0, size=n_rows) for i in range(1, 29)},
            "Amount": np.clip(rng.lognormal(mean=3.0, sigma=1.0, size=n_rows), 0.1, 25000.0),
        }
    )

    # Ensure enough labeled fraud rows for sampling tests.
    labels = np.zeros(n_rows, dtype=int)
    labels[:80] = 1
    rng.shuffle(labels)
    df["Class"] = labels

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


@pytest.fixture(scope="session")
def integration_dataset_csv(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dataset_root = tmp_path_factory.mktemp("integration-dataset")
    dataset_csv = dataset_root / "creditcard.csv"
    _write_synthetic_creditcard_csv(dataset_csv)
    return dataset_csv


@pytest.fixture(autouse=True)
def _integration_dataset_env(monkeypatch: pytest.MonkeyPatch, integration_dataset_csv: Path) -> None:
    monkeypatch.setenv("DATASET_CSV_PATH", str(integration_dataset_csv))
    # Keep integration tests deterministic by ensuring risk-tier coverage in sampled flows.
    monkeypatch.setenv("REVIEW_THRESHOLD", "0.0")
    monkeypatch.setenv("FRAUD_THRESHOLD", "0.0")
