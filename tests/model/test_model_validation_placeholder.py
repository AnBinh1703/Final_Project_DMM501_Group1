from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.models.loader import load_model_from_path
from src.pipelines.train_pipeline import run_training


def test_training_produces_artifacts_and_valid_metrics(tmp_path: Path) -> None:
	artifacts_dir = tmp_path / "artifacts"
	result = run_training(
		data_path=None,
		artifacts_dir=str(artifacts_dir),
		target_col="Class",
		min_precision=0.1,
		n_samples_if_synthetic=1000,
	)

	assert Path(result["model_path"]).exists()
	assert Path(result["model_info_path"]).exists()
	assert Path(result["metrics_path"]).exists()

	report = json.loads(Path(result["metrics_path"]).read_text(encoding="utf-8"))
	final_test = report["models"]["final_model_test"]
	assert 0.0 <= final_test["pr_auc"] <= 1.0
	assert 0.0 <= final_test["roc_auc"] <= 1.0
	assert 0.0 <= final_test["precision"] <= 1.0
	assert 0.0 <= final_test["recall"] <= 1.0


def test_loaded_model_predicts_probability_range(tmp_path: Path) -> None:
	artifacts_dir = tmp_path / "artifacts"
	result = run_training(
		data_path=None,
		artifacts_dir=str(artifacts_dir),
		target_col="Class",
		min_precision=0.1,
		n_samples_if_synthetic=1200,
	)

	loaded = load_model_from_path(Path(result["model_path"]), threshold=None, model_version=None)
	assert loaded.n_features is not None

	sample = np.zeros((1, loaded.n_features), dtype=float)
	proba = float(loaded.model.predict_proba(sample)[0][1])
	assert 0.0 <= proba <= 1.0
