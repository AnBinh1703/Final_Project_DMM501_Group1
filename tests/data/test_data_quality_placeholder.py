from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data.dataset import load_training_dataframe


def test_synthetic_data_has_target_and_binary_labels() -> None:
    df, source = load_training_dataframe(data_path=None, target_col="Class", n_samples_if_synthetic=500)
    assert source.startswith("synthetic:")
    assert "Class" in df.columns
    assert set(df["Class"].unique()).issubset({0, 1})
    assert len(df) == 500


def test_csv_load_path_round_trip(tmp_path: Path) -> None:
    csv_path = tmp_path / "dataset.csv"
    data = pd.DataFrame(
        {
            "feature_0": [0.1, 0.2, 0.3, 0.4],
            "feature_1": [1.0, 0.0, 1.0, 0.0],
            "Class": [0, 1, 0, 1],
        }
    )
    data.to_csv(csv_path, index=False)

    loaded, source = load_training_dataframe(data_path=str(csv_path), target_col="Class")
    assert source.startswith("csv:")
    assert loaded.shape == (4, 3)
