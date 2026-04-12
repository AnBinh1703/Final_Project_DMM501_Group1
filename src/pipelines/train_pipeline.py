from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.data.dataset import load_training_dataframe

try:
    from lightgbm import LGBMClassifier

    HAS_LIGHTGBM = True
except Exception:
    HAS_LIGHTGBM = False


def _evaluate(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict[str, Any]:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "threshold": float(threshold),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def _tune_threshold(y_true: np.ndarray, y_score: np.ndarray, min_precision: float = 0.1) -> tuple[float, dict[str, Any]]:
    best_threshold = 0.5
    best_metrics = _evaluate(y_true, y_score, threshold=best_threshold)

    for threshold in np.linspace(0.05, 0.95, 91):
        metrics = _evaluate(y_true, y_score, threshold=float(threshold))
        if metrics["precision"] < min_precision:
            continue
        if metrics["f1"] > best_metrics["f1"]:
            best_threshold = float(threshold)
            best_metrics = metrics

    return best_threshold, best_metrics


def _train_baseline_model(X_train: np.ndarray, y_train: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(max_iter=1200, class_weight="balanced")
    model.fit(X_train, y_train)
    return model


def _train_candidate_model(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=220,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )
    model.fit(X_train, y_train)
    return model


def _train_final_model(X_train: np.ndarray, y_train: np.ndarray, positive_weight: float):
    if HAS_LIGHTGBM:
        model = LGBMClassifier(
            n_estimators=260,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            scale_pos_weight=positive_weight,
            objective="binary",
        )
    else:
        # Fallback keeps training runnable even if LightGBM binary is unavailable.
        model = RandomForestClassifier(
            n_estimators=260,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
    model.fit(X_train, y_train)
    return model


def run_training(
    data_path: str | None,
    artifacts_dir: str,
    target_col: str,
    min_precision: float,
    n_samples_if_synthetic: int,
) -> dict[str, Any]:
    df, source = load_training_dataframe(
        data_path=data_path,
        target_col=target_col,
        n_samples_if_synthetic=n_samples_if_synthetic,
    )

    X = df.drop(columns=[target_col]).values
    y = df[target_col].astype(int).values

    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=y,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.5,
        random_state=42,
        stratify=y_temp,
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    baseline_model = _train_baseline_model(X_train_scaled, y_train)
    baseline_val_scores = baseline_model.predict_proba(X_val_scaled)[:, 1]
    baseline_metrics = _evaluate(y_val, baseline_val_scores, threshold=0.5)

    candidate_model = _train_candidate_model(X_train, y_train)
    candidate_val_scores = candidate_model.predict_proba(X_val)[:, 1]
    candidate_metrics = _evaluate(y_val, candidate_val_scores, threshold=0.5)

    negatives = max((y_train == 0).sum(), 1)
    positives = max((y_train == 1).sum(), 1)
    positive_weight = float(negatives / positives)

    final_model = _train_final_model(X_train, y_train, positive_weight=positive_weight)
    final_val_scores = final_model.predict_proba(X_val)[:, 1]
    tuned_threshold, tuned_metrics = _tune_threshold(y_val, final_val_scores, min_precision=min_precision)

    X_train_full = np.concatenate([X_train, X_val], axis=0)
    y_train_full = np.concatenate([y_train, y_val], axis=0)
    final_model.fit(X_train_full, y_train_full)

    final_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("classifier", final_model),
    ])
    final_pipeline.fit(X_train_full, y_train_full)

    final_test_scores = final_pipeline.predict_proba(X_test)[:, 1]
    final_test_metrics = _evaluate(y_test, final_test_scores, threshold=tuned_threshold)

    model_version = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    artifacts_path = Path(artifacts_dir)
    artifacts_path.mkdir(parents=True, exist_ok=True)

    model_path = artifacts_path / "model.joblib"
    metrics_path = artifacts_path / "metrics_report.json"
    model_info_path = artifacts_path / "model_info.json"

    joblib.dump(final_pipeline, model_path)

    report = {
        "data_source": source,
        "target_column": target_col,
        "dataset_rows": int(df.shape[0]),
        "dataset_features": int(X.shape[1]),
        "class_distribution": {
            "non_fraud": int((y == 0).sum()),
            "fraud": int((y == 1).sum()),
        },
        "models": {
            "baseline_logistic_regression_val": baseline_metrics,
            "candidate_random_forest_val": candidate_metrics,
            "final_model_val_tuned_threshold": tuned_metrics,
            "final_model_test": final_test_metrics,
        },
        "final_model_name": "lightgbm" if HAS_LIGHTGBM else "random_forest_fallback",
        "model_version": model_version,
    }

    model_info = {
        "model_version": model_version,
        "threshold": float(tuned_threshold),
        "n_features": int(X.shape[1]),
    }

    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    model_info_path.write_text(json.dumps(model_info, indent=2), encoding="utf-8")

    try:
        import mlflow

        mlflow.set_experiment("fraud-detection")
        with mlflow.start_run(run_name=f"train-{model_version}"):
            mlflow.log_param("data_source", source)
            mlflow.log_param("target_col", target_col)
            mlflow.log_param("final_model_name", report["final_model_name"])
            mlflow.log_param("n_features", int(X.shape[1]))
            mlflow.log_param("threshold", float(tuned_threshold))
            final_metrics = report["models"]["final_model_test"]
            mlflow.log_metric("test_pr_auc", float(final_metrics["pr_auc"]))
            mlflow.log_metric("test_roc_auc", float(final_metrics["roc_auc"]))
            mlflow.log_metric("test_precision", float(final_metrics["precision"]))
            mlflow.log_metric("test_recall", float(final_metrics["recall"]))
            mlflow.log_metric("test_f1", float(final_metrics["f1"]))
            mlflow.log_artifact(str(model_path))
            mlflow.log_artifact(str(metrics_path))
            mlflow.log_artifact(str(model_info_path))
    except Exception:
        # Keep pipeline runnable even if MLflow local logging fails in a given environment.
        pass

    return {
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "model_info_path": str(model_info_path),
        "report": report,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train fraud detection model and save artifacts")
    parser.add_argument(
        "--data-path",
        type=str,
        default="data/raw/creditcard.csv",
        help="CSV dataset path (defaults to Kaggle Credit Card Fraud local path)",
    )
    parser.add_argument("--artifacts-dir", type=str, default="artifacts", help="Output artifacts directory")
    parser.add_argument("--target-col", type=str, default="Class", help="Target column name")
    parser.add_argument("--min-precision", type=float, default=0.1, help="Minimum precision constraint for threshold tuning")
    parser.add_argument(
        "--synthetic-samples",
        type=int,
        default=12000,
        help="Synthetic row count used only when --data-path is not provided",
    )
    return parser


def run() -> None:
    args = build_parser().parse_args()
    result = run_training(
        data_path=args.data_path,
        artifacts_dir=args.artifacts_dir,
        target_col=args.target_col,
        min_precision=args.min_precision,
        n_samples_if_synthetic=args.synthetic_samples,
    )

    final_test = result["report"]["models"]["final_model_test"]
    print("Training completed")
    print(f"Model saved: {result['model_path']}")
    print(f"Model info: {result['model_info_path']}")
    print(f"Metrics report: {result['metrics_path']}")
    print(
        "Final test metrics | "
        f"PR-AUC={final_test['pr_auc']:.4f}, "
        f"ROC-AUC={final_test['roc_auc']:.4f}, "
        f"Precision={final_test['precision']:.4f}, "
        f"Recall={final_test['recall']:.4f}, "
        f"F1={final_test['f1']:.4f}"
    )


if __name__ == "__main__":
    run()
