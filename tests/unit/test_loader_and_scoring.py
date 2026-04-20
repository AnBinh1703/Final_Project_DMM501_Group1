import json
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pytest

from src.models.loader import load_model_from_path, maybe_load_model_from_env
from src.services.scoring_service import score_transaction, validate_feature_vector


def _dump_dummy_model(path: Path) -> None:
    joblib.dump(SimpleNamespace(n_features_in_=7), path)


def test_load_model_from_path_normalizes_metadata_values(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    _dump_dummy_model(model_path)
    metadata = {
        "threshold_high": 1.5,
        "threshold_review": -0.1,
        "model_version": "meta-v1",
        "feature_columns": ["a", "b"],
        "model_type": "dummy",
        "dataset_path": "data/raw/creditcard.csv",
        "fraud_base_rate": 2.0,
        "selection_timestamp_utc": "2026-04-20T00:00:00Z",
        "score_semantics": "risk_score_uncalibrated",
        "threshold_policy": {"strategy": "fixed"},
        "score_percentiles": ["0.1", "bad"],
    }
    (tmp_path / "model_info.json").write_text(json.dumps(metadata), encoding="utf-8")

    loaded = load_model_from_path(model_path, threshold=None, model_version=None)
    assert loaded.threshold_high == 0.5
    assert loaded.threshold_review == 0.5
    assert loaded.model_version == "meta-v1"
    assert loaded.n_features == 7
    assert loaded.feature_columns == ["a", "b"]
    assert loaded.model_type == "dummy"
    assert loaded.dataset_path == "data/raw/creditcard.csv"
    assert loaded.fraud_base_rate is None
    assert loaded.selection_timestamp_utc == "2026-04-20T00:00:00Z"
    assert loaded.threshold_policy == {"strategy": "fixed"}
    assert loaded.score_percentiles is None


def test_load_model_from_path_handles_invalid_json_and_explicit_overrides(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    _dump_dummy_model(model_path)
    (tmp_path / "model_info.json").write_text("{bad json", encoding="utf-8")

    loaded = load_model_from_path(model_path, threshold=0.8, model_version="override-v")
    assert loaded.threshold_high == 0.8
    assert loaded.threshold_review == 0.5
    assert loaded.model_version == "override-v"


def test_load_model_from_path_reads_metadata_sidecar_file(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    _dump_dummy_model(model_path)
    sidecar_path = tmp_path / "model.joblib.metadata.json"
    sidecar_path.write_text(json.dumps({"model_version": "sidecar-v"}), encoding="utf-8")

    loaded = load_model_from_path(model_path, threshold=None, model_version=None)
    assert loaded.model_version == "sidecar-v"


def test_maybe_load_model_from_env_strict_model_path_behaviour(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_PATH", "   ")
    assert maybe_load_model_from_env() is None

    missing_path = tmp_path / "missing.joblib"
    monkeypatch.setenv("MODEL_PATH", str(missing_path))
    assert maybe_load_model_from_env() is None


def test_maybe_load_model_from_env_applies_threshold_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model_path = tmp_path / "model.joblib"
    _dump_dummy_model(model_path)

    monkeypatch.setenv("MODEL_PATH", str(model_path))
    monkeypatch.setenv("FRAUD_THRESHOLD", "0.9")
    monkeypatch.setenv("REVIEW_THRESHOLD", "0.4")
    monkeypatch.setenv("MODEL_VERSION", "env-v1")

    loaded = maybe_load_model_from_env()
    assert loaded is not None
    assert loaded.threshold_high == 0.9
    assert loaded.threshold_review == 0.4
    assert loaded.model_version == "env-v1"


def test_validate_feature_vector_rejects_invalid_values() -> None:
    validate_feature_vector([1.0, 2.0])

    with pytest.raises(ValueError):
        validate_feature_vector([1.0, float("nan")])

    with pytest.raises(ValueError):
        validate_feature_vector([1.0, "bad"])  # type: ignore[list-item]


def test_score_transaction_requires_predict_proba() -> None:
    with pytest.raises(ValueError):
        score_transaction(model=object(), features=[1.0, 2.0])


def test_score_transaction_returns_probability() -> None:
    class DummyModel:
        def predict_proba(self, x: np.ndarray) -> np.ndarray:
            assert x.shape == (1, 3)
            return np.array([[0.2, 0.8]])

    score = score_transaction(model=DummyModel(), features=[1.0, 2.0, 3.0])
    assert score == 0.8
