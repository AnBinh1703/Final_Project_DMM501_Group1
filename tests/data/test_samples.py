from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.dataset import load_training_dataframe
from src.data.samples import resolve_dataset_path, sample_dataset_rows


def _write_dataset_csv(tmp_path: Path, *, rows: list[dict]) -> Path:
    path = tmp_path / "dataset.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_resolve_dataset_path_absolute_round_trip(tmp_path: Path) -> None:
    abs_path = (tmp_path / "data.csv").resolve()
    assert resolve_dataset_path(str(abs_path), repo_root=tmp_path) == abs_path


def test_resolve_dataset_path_relative_resolves_under_repo_root(tmp_path: Path) -> None:
    rel = Path("data") / "dataset.csv"
    resolved = resolve_dataset_path(str(rel), repo_root=tmp_path)
    assert resolved == (tmp_path / rel).resolve()


def test_sample_dataset_rows_mixed_returns_features_and_optional_label(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(
        tmp_path,
        rows=[
            {"feature_0": 0.1, "feature_1": 1.0, "Class": 0},
            {"feature_0": 0.2, "feature_1": 0.0, "Class": 1},
            {"feature_0": 0.3, "feature_1": 1.0, "Class": 0},
            {"feature_0": 0.4, "feature_1": 0.0, "Class": 1},
        ],
    )

    rows = sample_dataset_rows(
        dataset_path=dataset_path,
        feature_columns=["feature_0", "feature_1"],
        n=3,
        strategy="mixed",
        seed=123,
        include_label=True,
    )
    assert len(rows) == 3
    assert all("features" in r and len(r["features"]) == 2 for r in rows)
    assert all("class_label" in r and r["class_label"] in (0, 1) for r in rows)


def test_sample_dataset_rows_invalid_n_raises(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(tmp_path, rows=[{"feature_0": 0.1, "Class": 0}])
    with pytest.raises(ValueError, match="n must be"):
        sample_dataset_rows(
            dataset_path=dataset_path,
            feature_columns=["feature_0"],
            n=0,
            strategy="mixed",
            seed=1,
        )


def test_sample_dataset_rows_invalid_strategy_raises(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(tmp_path, rows=[{"feature_0": 0.1, "Class": 0}])
    with pytest.raises(ValueError, match="Invalid strategy"):
        sample_dataset_rows(
            dataset_path=dataset_path,
            feature_columns=["feature_0"],
            n=1,
            strategy="nope",
            seed=1,
        )


def test_sample_dataset_rows_fraud_raises_when_no_fraud_samples(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(
        tmp_path,
        rows=[
            {"feature_0": 0.1, "feature_1": 1.0, "Class": 0},
            {"feature_0": 0.2, "feature_1": 0.0, "Class": 0},
        ],
    )
    with pytest.raises(ValueError, match="No fraud samples"):
        sample_dataset_rows(
            dataset_path=dataset_path,
            feature_columns=["feature_0", "feature_1"],
            n=2,
            strategy="fraud",
            seed=42,
        )


def test_sample_dataset_rows_production_returns_n_rows_with_all_legit(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(
        tmp_path,
        rows=[
            {"feature_0": 0.1, "feature_1": 1.0, "Class": 0},
            {"feature_0": 0.2, "feature_1": 0.0, "Class": 0},
            {"feature_0": 0.3, "feature_1": 1.0, "Class": 0},
        ],
    )

    rows = sample_dataset_rows(
        dataset_path=dataset_path,
        feature_columns=["feature_0", "feature_1"],
        n=3,
        strategy="production",
        seed=0,
    )
    assert len(rows) == 3


def test_load_training_dataframe_missing_path_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError, match="Dataset path not found"):
        load_training_dataframe(data_path=str(missing), target_col="Class")


def test_load_training_dataframe_missing_target_column_raises(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(tmp_path, rows=[{"feature_0": 0.1, "not_class": 0}])
    with pytest.raises(ValueError, match="Target column"):
        load_training_dataframe(data_path=str(dataset_path), target_col="Class")


def test_load_training_dataframe_non_binary_target_raises(tmp_path: Path) -> None:
    dataset_path = _write_dataset_csv(
        tmp_path,
        rows=[
            {"feature_0": 0.1, "Class": 0},
            {"feature_0": 0.2, "Class": 2},
        ],
    )
    with pytest.raises(ValueError, match="must be binary"):
        load_training_dataframe(data_path=str(dataset_path), target_col="Class")

