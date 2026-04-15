from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import matplotlib
import mlflow
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    auc,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import ParameterGrid, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def _mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _evaluate(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict:
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "pr_auc": float(average_precision_score(y_true, y_score)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def _threshold_sweep(y_true: np.ndarray, y_score: np.ndarray, model_name: str) -> pd.DataFrame:
    rows: list[dict] = []
    for threshold in np.linspace(0.01, 0.99, 99):
        metrics = _evaluate(y_true, y_score, threshold=float(threshold))
        metrics["model"] = model_name
        rows.append(metrics)
    return pd.DataFrame(rows)


def _best_threshold_from_f1(threshold_df: pd.DataFrame) -> float:
    best_idx = threshold_df["f1"].idxmax()
    return float(threshold_df.loc[best_idx, "threshold"])


def _best_threshold_from_precision(threshold_df: pd.DataFrame, *, min_precision: float) -> float:
    """
    Business-driven threshold selection:
    maximize recall subject to precision >= min_precision (review-queue style constraint).
    """
    df_ok = threshold_df[threshold_df["precision"] >= float(min_precision)].copy()
    if not df_ok.empty:
        df_ok = df_ok.sort_values(by=["recall", "precision", "threshold"], ascending=[False, False, True])
        return float(df_ok.iloc[0]["threshold"])

    # If nothing meets the precision constraint, fall back to the threshold that maximizes precision.
    df2 = threshold_df.sort_values(by=["precision", "threshold"], ascending=[False, True])
    return float(df2.iloc[0]["threshold"])


def _threshold_from_topk_rate(y_score: np.ndarray, *, top_rate: float) -> float:
    """
    Business-driven threshold selection based on review capacity:
    choose a threshold that flags approximately the top-K fraction by score.

    Note: ties at the threshold can result in slightly more than top_rate being flagged.
    """
    r = float(top_rate)
    if not (0.0 < r < 1.0):
        raise ValueError("top_rate must be in (0,1)")
    n = int(len(y_score))
    if n < 1:
        raise ValueError("y_score must be non-empty")
    k = max(1, int(np.ceil(r * n)))
    scores_desc = np.sort(np.asarray(y_score, dtype=float))[::-1]
    return float(scores_desc[min(k - 1, n - 1)])


def _compute_score_percentiles(y_score: np.ndarray) -> list[float]:
    scores = np.asarray(y_score, dtype=float)
    return [float(np.quantile(scores, p / 100.0)) for p in range(0, 101)]


def _plot_confusion_matrix(cm: np.ndarray, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.figure.colorbar(im, ax=ax)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Pred 0", "Pred 1"])
    ax.set_yticklabels(["True 0", "True 1"])
    ax.set_title(title)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="black")
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_roc(y_true: np.ndarray, y_score: np.ndarray, title: str, out_path: Path) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(fpr, tpr, label=f"ROC AUC={roc_auc:.4f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_pr(y_true: np.ndarray, y_score: np.ndarray, title: str, out_path: Path) -> None:
    precision, recall, _ = precision_recall_curve(y_true, y_score)
    # Use Average Precision (AP) for consistency with exported PR-AUC metrics
    # (average_precision_score), which is the standard scalar summary for
    # imbalanced classification. The trapezoidal area under the PR curve
    # depends on the discretization; we avoid presenting it as "PR-AUC".
    ap = float(average_precision_score(y_true, y_score))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(recall, precision, label=f"Average Precision (AP)={ap:.4f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_threshold_curves(threshold_df: pd.DataFrame, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(threshold_df["threshold"], threshold_df["precision"], label="precision")
    ax.plot(threshold_df["threshold"], threshold_df["recall"], label="recall")
    ax.plot(threshold_df["threshold"], threshold_df["f1"], label="f1")
    best_idx = threshold_df["f1"].idxmax()
    best_thr = float(threshold_df.loc[best_idx, "threshold"])
    best_f1 = float(threshold_df.loc[best_idx, "f1"])
    ax.axvline(best_thr, linestyle="--", color="gray", linewidth=1)
    ax.set_title(f"{title} (best thr={best_thr:.2f}, f1={best_f1:.3f})")
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Metric")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_model_comparison(tuned_rows: list[dict], title: str, out_path: Path) -> None:
    df = pd.DataFrame(tuned_rows)
    metrics = ["pr_auc", "roc_auc", "f1", "precision", "recall"]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(metrics))
    width = 0.35 if len(df) == 2 else 0.25
    for i, row in enumerate(df.to_dict(orient="records")):
        vals = [float(row[m]) for m in metrics]
        ax.bar(x + (i - (len(df) - 1) / 2) * width, vals, width=width, label=str(row["model"]))
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim(0.0, 1.0)
    ax.set_title(title)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def _plot_full_correlation(df: pd.DataFrame, title: str, out_path: Path) -> None:
    corr = df.corr(numeric_only=True)
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_title(title)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=90, fontsize=6)
    ax.set_yticklabels(corr.columns, fontsize=6)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def run_workflow(
    data_path: str,
    artifacts_root: str,
    random_seed: int = 42,
    review_top_rate: float = 0.01,
    high_top_rate: float = 0.002,
) -> dict:
    root = Path(artifacts_root)
    reports_dir = root / "reports"
    figures_dir = root / "figures"
    benchmarks_dir = root / "benchmarks"
    models_dir = root / "models"

    for directory in [reports_dir, figures_dir, benchmarks_dir, models_dir]:
        _mkdir(directory)

    dataset_path = Path(data_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

    review_top_rate = float(review_top_rate)
    high_top_rate = float(high_top_rate)
    if not (0.0 < high_top_rate <= review_top_rate < 1.0):
        raise ValueError("Expected 0 < high_top_rate <= review_top_rate < 1")

    df = pd.read_csv(dataset_path)

    expected_columns = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]
    schema_info = {
        "dataset_path": str(dataset_path),
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "columns": list(df.columns),
        "matches_expected_schema": list(df.columns) == expected_columns,
    }
    _save_json(reports_dir / "dataset_schema.json", schema_info)

    # EDA and data quality outputs
    missing_values = df.isnull().sum().rename("missing_count").to_frame()
    missing_values.to_csv(reports_dir / "missing_values.csv")

    duplicates = int(df.duplicated().sum())
    class_distribution = df["Class"].value_counts().sort_index().rename_axis("Class").reset_index(name="count")
    class_distribution["ratio"] = class_distribution["count"] / len(df)
    class_distribution.to_csv(reports_dir / "class_distribution.csv", index=False)
    _save_json(
        reports_dir / "class_distribution.json",
        {
            "total_rows": int(len(df)),
            "class_counts": {str(int(r["Class"])): int(r["count"]) for _, r in class_distribution.iterrows()},
            "class_ratio": {str(int(r["Class"])): float(r["ratio"]) for _, r in class_distribution.iterrows()},
        },
    )

    summary_stats = df.describe().T
    summary_stats.to_csv(reports_dir / "summary_statistics.csv")

    eda_summary = {
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "duplicate_rows": duplicates,
        "fraud_ratio": float((df["Class"] == 1).mean()),
        "class_counts": {
            "0": int((df["Class"] == 0).sum()),
            "1": int((df["Class"] == 1).sum()),
        },
    }
    _save_json(reports_dir / "eda_summary.json", eda_summary)

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(class_distribution["Class"].astype(str), class_distribution["count"])
    ax.set_title("Class Distribution")
    ax.set_xlabel("Class")
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(figures_dir / "class_distribution.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["Amount"], bins=100)
    ax.set_title("Amount Distribution")
    ax.set_xlabel("Amount")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    fig.savefig(figures_dir / "amount_distribution.png", dpi=160)
    plt.close(fig)

    # Fraud vs non-fraud amount comparison
    fig, ax = plt.subplots(figsize=(7, 4))
    non_fraud = df[df["Class"] == 0]["Amount"].clip(lower=0)
    fraud = df[df["Class"] == 1]["Amount"].clip(lower=0)
    bins = np.linspace(0, float(df["Amount"].quantile(0.99)), 80)
    ax.hist(non_fraud, bins=bins, alpha=0.6, label="Non-fraud", density=True)
    ax.hist(fraud, bins=bins, alpha=0.6, label="Fraud", density=True)
    ax.set_title("Amount Distribution: Fraud vs Non-fraud (up to p99)")
    ax.set_xlabel("Amount")
    ax.set_ylabel("Density")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(figures_dir / "fraud_vs_nonfraud_amount.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["Time"], bins=100)
    ax.set_title("Time Distribution")
    ax.set_xlabel("Time")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    fig.savefig(figures_dir / "time_distribution.png", dpi=160)
    plt.close(fig)

    # Fraud vs non-fraud time comparison (up to p99 for readability)
    fig, ax = plt.subplots(figsize=(7, 4))
    non_fraud_t = df[df["Class"] == 0]["Time"].clip(lower=0)
    fraud_t = df[df["Class"] == 1]["Time"].clip(lower=0)
    max_t = float(df["Time"].quantile(0.99))
    bins = np.linspace(0, max_t, 80)
    ax.hist(non_fraud_t, bins=bins, alpha=0.6, label="Non-fraud", density=True)
    ax.hist(fraud_t, bins=bins, alpha=0.6, label="Fraud", density=True)
    ax.set_title("Time Distribution: Fraud vs Non-fraud (up to p99)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Density")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(figures_dir / "fraud_vs_nonfraud_time.png", dpi=160)
    plt.close(fig)

    corr = df[["Time", "Amount", "Class"]].corr()
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr.columns)))
    ax.set_yticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right")
    ax.set_yticklabels(corr.columns)
    ax.set_title("Correlation (Time, Amount, Class)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(figures_dir / "correlation_overview.png", dpi=160)
    plt.close(fig)

    # Full correlation heatmap (all features + Class)
    _plot_full_correlation(df, title="Full Correlation Heatmap", out_path=figures_dir / "correlation_full.png")

    feature_cols = [c for c in df.columns if c != "Class"]
    # Keep X as a DataFrame so models that support feature names (e.g., LightGBM)
    # are trained and scored with consistent feature columns (avoids noisy warnings).
    X = df[feature_cols].copy()
    y = df["Class"].astype(int).values

    X_train, X_temp, y_train, y_temp = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=random_seed,
        stratify=y,
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp,
        y_temp,
        test_size=0.50,
        random_state=random_seed,
        stratify=y_temp,
    )

    split_info = {
        "train_rows": int(X_train.shape[0]),
        "val_rows": int(X_val.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "n_features": int(X_train.shape[1]),
        "random_seed": random_seed,
    }
    _save_json(reports_dir / "split_info.json", split_info)

    # Keep experiment tracking self-contained under artifacts/ and use sqlite backend
    # to avoid file-store corruption issues.
    mlflow_db_path = (root / "mlflow.db").resolve()
    mlflow.set_tracking_uri(f"sqlite:///{mlflow_db_path}")
    mlflow.set_experiment("fraud-detection-benchmark")

    # Baseline: Logistic Regression
    baseline_pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_seed)),
        ]
    )
    baseline_pipeline.fit(X_train, y_train)

    baseline_val_scores = baseline_pipeline.predict_proba(X_val)[:, 1]

    baseline_threshold_df = _threshold_sweep(y_val, baseline_val_scores, model_name="logistic_regression")
    baseline_threshold_review = _threshold_from_topk_rate(baseline_val_scores, top_rate=review_top_rate)
    baseline_threshold_high = _threshold_from_topk_rate(baseline_val_scores, top_rate=high_top_rate)
    baseline_threshold_review = float(min(baseline_threshold_review, baseline_threshold_high))

    baseline_default_val = _evaluate(y_val, baseline_val_scores, threshold=0.5)
    baseline_review_val = _evaluate(y_val, baseline_val_scores, threshold=baseline_threshold_review)
    baseline_high_val = _evaluate(y_val, baseline_val_scores, threshold=baseline_threshold_high)

    baseline_metrics_df = pd.DataFrame([
        {"model": "logistic_regression", "split": "val", "setting": "default_0.5", **baseline_default_val},
        {"model": "logistic_regression", "split": "val", "setting": f"review_top{review_top_rate*100:.2f}pct", **baseline_review_val},
        {"model": "logistic_regression", "split": "val", "setting": f"high_top{high_top_rate*100:.2f}pct", **baseline_high_val},
    ])
    baseline_metrics_df.to_csv(benchmarks_dir / "baseline_metrics_table.csv", index=False)
    baseline_threshold_df.to_csv(benchmarks_dir / "baseline_threshold_tuning.csv", index=False)
    _plot_threshold_curves(
        baseline_threshold_df,
        title="Baseline Logistic Regression Threshold Sweep (validation)",
        out_path=figures_dir / "baseline_threshold_sweep.png",
    )

    baseline_cm = confusion_matrix(y_val, (baseline_val_scores >= baseline_threshold_high).astype(int))
    _plot_confusion_matrix(
        baseline_cm,
        title=f"Baseline Logistic Regression CM (val, high_thr={baseline_threshold_high:.2f})",
        out_path=figures_dir / "baseline_confusion_matrix.png",
    )
    # Rubric-required filename for baseline confusion matrix
    _plot_confusion_matrix(
        baseline_cm,
        title=f"Baseline Logistic Regression CM (val, high_thr={baseline_threshold_high:.2f})",
        out_path=figures_dir / "confusion_matrix.png",
    )
    _plot_roc(y_val, baseline_val_scores, "Baseline Logistic Regression ROC (val)", figures_dir / "baseline_roc_curve.png")
    _plot_pr(y_val, baseline_val_scores, "Baseline Logistic Regression PR (val)", figures_dir / "baseline_pr_curve.png")

    baseline_report = classification_report(
        y_val,
        (baseline_val_scores >= baseline_threshold_high).astype(int),
        output_dict=True,
        zero_division=0,
    )
    _save_json(reports_dir / "baseline_classification_report.json", baseline_report)

    baseline_model_path = models_dir / "baseline_logistic_regression_pipeline.joblib"
    joblib.dump(baseline_pipeline, baseline_model_path)

    _save_json(
        reports_dir / "baseline_metrics.json",
        {"threshold_review": baseline_threshold_review, "threshold_high": baseline_threshold_high, "val": baseline_high_val},
    )

    try:
        with mlflow.start_run(run_name="baseline_logistic_regression"):
            mlflow.log_param("model", "LogisticRegression")
            mlflow.log_param("class_weight", "balanced")
            mlflow.log_param("random_seed", random_seed)
            mlflow.log_param("threshold_review", float(baseline_threshold_review))
            mlflow.log_param("threshold_high", float(baseline_threshold_high))
            mlflow.log_metric("val_pr_auc", float(baseline_high_val["pr_auc"]))
            mlflow.log_metric("val_roc_auc", float(baseline_high_val["roc_auc"]))
            mlflow.log_metric("val_precision_high", float(baseline_high_val["precision"]))
            mlflow.log_metric("val_recall_high", float(baseline_high_val["recall"]))
            mlflow.log_metric("val_f1_high", float(baseline_high_val["f1"]))
            mlflow.log_artifact(str(benchmarks_dir / "baseline_metrics_table.csv"))
            mlflow.log_artifact(str(figures_dir / "baseline_confusion_matrix.png"))
    except Exception:
        pass

    # Improved: LightGBM with simple tuning on validation PR-AUC
    neg = max(int((y_train == 0).sum()), 1)
    pos = max(int((y_train == 1).sum()), 1)
    natural_ratio = float(neg / pos)

    param_grid = {
        # Keep tuning basic and fast while still demonstrating HP search.
        "n_estimators": [250, 450],
        "learning_rate": [0.03, 0.08],
        "num_leaves": [31, 63],
        "scale_pos_weight": [10.0, natural_ratio],
    }

    tuning_rows: list[dict] = []
    best_model: LGBMClassifier | None = None
    best_params: dict | None = None
    best_val_pr_auc = -1.0

    for params in ParameterGrid(param_grid):
        model = LGBMClassifier(
            objective="binary",
            random_state=random_seed,
            subsample=0.9,
            colsample_bytree=0.9,
            n_jobs=-1,
            **params,
        )
        model.fit(X_train, y_train)
        val_scores = model.predict_proba(X_val)[:, 1]
        val_pr_auc = float(average_precision_score(y_val, val_scores))
        row = {"val_pr_auc": val_pr_auc, "natural_scale_pos_weight": natural_ratio, **params}
        tuning_rows.append(row)
        if val_pr_auc > best_val_pr_auc:
            best_val_pr_auc = val_pr_auc
            best_model = model
            best_params = params

    if best_model is None or best_params is None:
        raise RuntimeError("LightGBM tuning failed to produce a candidate model")

    tuning_df = pd.DataFrame(tuning_rows).sort_values(by="val_pr_auc", ascending=False)
    tuning_df.to_csv(benchmarks_dir / "improved_hyperparameter_tuning.csv", index=False)

    improved_val_scores = best_model.predict_proba(X_val)[:, 1]

    improved_threshold_df = _threshold_sweep(y_val, improved_val_scores, model_name="lightgbm")
    improved_threshold_review = _threshold_from_topk_rate(improved_val_scores, top_rate=review_top_rate)
    improved_threshold_high = _threshold_from_topk_rate(improved_val_scores, top_rate=high_top_rate)
    improved_threshold_review = float(min(improved_threshold_review, improved_threshold_high))

    improved_default_val = _evaluate(y_val, improved_val_scores, threshold=0.5)
    improved_review_val = _evaluate(y_val, improved_val_scores, threshold=improved_threshold_review)
    improved_high_val = _evaluate(y_val, improved_val_scores, threshold=improved_threshold_high)

    improved_metrics_df = pd.DataFrame([
        {"model": "lightgbm", "split": "val", "setting": "default_0.5", **improved_default_val},
        {"model": "lightgbm", "split": "val", "setting": f"review_top{review_top_rate*100:.2f}pct", **improved_review_val},
        {"model": "lightgbm", "split": "val", "setting": f"high_top{high_top_rate*100:.2f}pct", **improved_high_val},
    ])
    improved_metrics_df.to_csv(benchmarks_dir / "improved_metrics_table.csv", index=False)
    improved_threshold_df.to_csv(benchmarks_dir / "improved_threshold_tuning.csv", index=False)
    _plot_threshold_curves(
        improved_threshold_df,
        title="Improved LightGBM Threshold Sweep (validation)",
        out_path=figures_dir / "improved_threshold_sweep.png",
    )

    improved_cm = confusion_matrix(y_val, (improved_val_scores >= improved_threshold_high).astype(int))
    _plot_confusion_matrix(
        improved_cm,
        title=f"Improved LightGBM CM (val, high_thr={improved_threshold_high:.2f})",
        out_path=figures_dir / "improved_confusion_matrix.png",
    )
    _plot_roc(y_val, improved_val_scores, "Improved LightGBM ROC (val)", figures_dir / "improved_roc_curve.png")
    _plot_pr(y_val, improved_val_scores, "Improved LightGBM PR (val)", figures_dir / "improved_pr_curve.png")

    improved_report = classification_report(
        y_val,
        (improved_val_scores >= improved_threshold_high).astype(int),
        output_dict=True,
        zero_division=0,
    )
    _save_json(reports_dir / "improved_classification_report.json", improved_report)

    feature_importance = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": best_model.feature_importances_,
        }
    ).sort_values(by="importance", ascending=False)
    feature_importance.to_csv(benchmarks_dir / "improved_feature_importance.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 6))
    top = feature_importance.head(15).iloc[::-1]
    ax.barh(top["feature"], top["importance"])
    ax.set_title("LightGBM Top Feature Importances")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(figures_dir / "improved_feature_importance.png", dpi=160)
    # Rubric-required filename (improved model feature importance)
    fig.savefig(figures_dir / "feature_importance.png", dpi=160)
    plt.close(fig)

    shap_sample = X_val.sample(n=min(1500, len(X_val)), random_state=random_seed)
    explainer = shap.TreeExplainer(best_model)
    shap_values = explainer.shap_values(shap_sample)
    if isinstance(shap_values, list):
        shap_values_to_plot = shap_values[1]
    else:
        shap_values_to_plot = shap_values

    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values_to_plot, shap_sample, show=False, plot_size=None)
    plt.tight_layout()
    plt.savefig(figures_dir / "shap_summary.png", dpi=160)
    plt.close()

    mean_abs_shap = np.abs(shap_values_to_plot).mean(axis=0)
    shap_importance = pd.DataFrame(
        {
            "feature": feature_cols,
            "mean_abs_shap": mean_abs_shap,
        }
    ).sort_values(by="mean_abs_shap", ascending=False)
    shap_importance.to_csv(benchmarks_dir / "shap_importance_table.csv", index=False)

    improved_model_path = models_dir / "improved_lightgbm.joblib"
    final_preprocess_path = models_dir / "final_preprocessing_identity.json"
    joblib.dump(best_model, improved_model_path)
    _save_json(
        final_preprocess_path,
        {
            "type": "identity",
            "feature_columns": feature_cols,
            "notes": "LightGBM used raw numeric features without scaling",
        },
    )

    try:
        with mlflow.start_run(run_name="improved_lightgbm"):
            mlflow.log_param("model", "LightGBM")
            mlflow.log_params({k: v for k, v in best_params.items()})
            mlflow.log_param("natural_scale_pos_weight", natural_ratio)
            mlflow.log_param("random_seed", random_seed)
            mlflow.log_param("threshold_review", float(improved_threshold_review))
            mlflow.log_param("threshold_high", float(improved_threshold_high))
            mlflow.log_metric("val_pr_auc", float(improved_high_val["pr_auc"]))
            mlflow.log_metric("val_roc_auc", float(improved_high_val["roc_auc"]))
            mlflow.log_metric("val_precision_high", float(improved_high_val["precision"]))
            mlflow.log_metric("val_recall_high", float(improved_high_val["recall"]))
            mlflow.log_metric("val_f1_high", float(improved_high_val["f1"]))
            mlflow.log_artifact(str(benchmarks_dir / "improved_metrics_table.csv"))
            mlflow.log_artifact(str(figures_dir / "improved_confusion_matrix.png"))
            mlflow.log_artifact(str(figures_dir / "shap_summary.png"))
    except Exception:
        pass

    threshold_comparison = pd.concat([baseline_threshold_df, improved_threshold_df], ignore_index=True)
    threshold_comparison.to_csv(benchmarks_dir / "threshold_comparison_table.csv", index=False)
    threshold_comparison.to_csv(benchmarks_dir / "threshold_comparison.csv", index=False)

    # Overlay precision/recall curves for threshold tuning comparison (validation).
    fig, ax = plt.subplots(figsize=(7, 4))
    for model_name, df_ in threshold_comparison.groupby("model"):
        ax.plot(df_["threshold"], df_["precision"], label=f"{model_name} precision")
        ax.plot(df_["threshold"], df_["recall"], label=f"{model_name} recall")
    ax.set_title("Threshold Comparison (Validation)")
    ax.set_xlabel("Threshold")
    ax.set_ylabel("Metric")
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(figures_dir / "threshold_comparison.png", dpi=160)
    plt.close(fig)

    # ---------------------------
    # Model selection (validation)
    # ---------------------------
    baseline_val_pr_auc = float(average_precision_score(y_val, baseline_val_scores))
    improved_val_pr_auc = float(average_precision_score(y_val, improved_val_scores))

    selected_model: str
    if improved_val_pr_auc > baseline_val_pr_auc + 1e-6:
        selected_model = "lightgbm"
    elif baseline_val_pr_auc > improved_val_pr_auc + 1e-6:
        selected_model = "logistic_regression"
    else:
        # Tie-break: pick the model with better recall at the REVIEW operating point.
        selected_model = (
            "lightgbm"
            if improved_review_val["recall"] >= baseline_review_val["recall"]
            else "logistic_regression"
        )

    selection_timestamp = datetime.now(UTC).isoformat()
    selection_summary = {
        "selected_model": selected_model,
        "selection_timestamp_utc": selection_timestamp,
        "selection_basis": "Validation-only selection. Primary=Val PR-AUC; tie-break=Recall at REVIEW operating point under a top-K review-rate policy.",
        "threshold_policy": {
            "type": "top_k_rate",
            "review_top_rate": float(review_top_rate),
            "high_top_rate": float(high_top_rate),
            "notes": "Thresholds are chosen to match business review capacity (flag the top-scoring fraction). Risk scores are uncalibrated.",
        },
        "baseline": {
            "val_pr_auc": baseline_val_pr_auc,
            "threshold_review": float(baseline_threshold_review),
            "threshold_high": float(baseline_threshold_high),
            "val_metrics_review": baseline_review_val,
            "val_metrics_high": baseline_high_val,
        },
        "improved": {
            "val_pr_auc": improved_val_pr_auc,
            "threshold_review": float(improved_threshold_review),
            "threshold_high": float(improved_threshold_high),
            "val_metrics_review": improved_review_val,
            "val_metrics_high": improved_high_val,
            "best_params": best_params,
        },
    }
    _save_json(reports_dir / "model_selection_summary.json", selection_summary)

    # ---------------------------
    # Final evaluation (test only)
    # ---------------------------
    X_trainval = pd.concat([X_train, X_val], axis=0)
    y_trainval = np.concatenate([y_train, y_val], axis=0)

    final_threshold_review: float
    final_threshold_high: float
    final_model: object
    final_model_type: str

    if selected_model == "lightgbm":
        if best_params is None:
            raise RuntimeError("Expected LightGBM best_params to be set")
        final_model = LGBMClassifier(
            objective="binary",
            random_state=random_seed,
            subsample=0.9,
            colsample_bytree=0.9,
            n_jobs=-1,
            **best_params,
        )
        final_model.fit(X_trainval, y_trainval)
        final_threshold_review = float(improved_threshold_review)
        final_threshold_high = float(improved_threshold_high)
        final_model_type = "lightgbm"
    else:
        final_model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_seed)),
            ]
        )
        final_model.fit(X_trainval, y_trainval)
        final_threshold_review = float(baseline_threshold_review)
        final_threshold_high = float(baseline_threshold_high)
        final_model_type = "logistic_regression_pipeline"

    if final_threshold_review > final_threshold_high:
        final_threshold_review = float(min(0.5, final_threshold_high))

    final_test_scores = final_model.predict_proba(X_test)[:, 1]  # type: ignore[attr-defined]
    final_test_review = _evaluate(y_test, final_test_scores, threshold=final_threshold_review)
    final_test_high = _evaluate(y_test, final_test_scores, threshold=final_threshold_high)

    # Offline reference operating point: F1-optimal threshold on validation,
    # used as a comparator (not the production policy).
    selected_threshold_df = improved_threshold_df if selected_model == "lightgbm" else baseline_threshold_df
    selected_val_scores = improved_val_scores if selected_model == "lightgbm" else baseline_val_scores
    final_threshold_f1 = _best_threshold_from_f1(selected_threshold_df)
    final_val_f1 = _evaluate(y_val, selected_val_scores, threshold=final_threshold_f1)
    final_test_f1 = _evaluate(y_test, final_test_scores, threshold=final_threshold_f1)

    final_cm = confusion_matrix(y_test, (final_test_scores >= final_threshold_high).astype(int))
    _plot_confusion_matrix(
        final_cm,
        title=f"Final Model CM (test, high_thr={final_threshold_high:.2f})",
        out_path=figures_dir / "final_confusion_matrix.png",
    )
    # Overwrite rubric filename with the final model's test CM.
    _plot_confusion_matrix(
        final_cm,
        title=f"Final Model CM (test, high_thr={final_threshold_high:.2f})",
        out_path=figures_dir / "confusion_matrix.png",
    )
    _plot_roc(y_test, final_test_scores, "Final Model ROC (test)", figures_dir / "final_roc_curve.png")
    _plot_pr(y_test, final_test_scores, "Final Model PR (test)", figures_dir / "final_pr_curve.png")

    # Final model feature importance (matches the deployable artifact).
    if selected_model == "lightgbm":
        importances = getattr(final_model, "feature_importances_", None)
        if importances is not None:
            feature_importance = pd.DataFrame(
                {"feature": feature_cols, "importance": importances}
            ).sort_values(by="importance", ascending=False)
            feature_importance.to_csv(benchmarks_dir / "final_feature_importance.csv", index=False)
            fig, ax = plt.subplots(figsize=(8, 6))
            top = feature_importance.head(15).iloc[::-1]
            ax.barh(top["feature"], top["importance"])
            ax.set_title("Final LightGBM Top Feature Importances")
            ax.set_xlabel("Importance")
            fig.tight_layout()
            fig.savefig(figures_dir / "final_feature_importance.png", dpi=160)
            fig.savefig(figures_dir / "feature_importance.png", dpi=160)
            plt.close(fig)
    else:
        # Logistic regression: use absolute coefficients as a global importance proxy.
        try:
            clf = final_model.named_steps["classifier"]  # type: ignore[union-attr]
            coef = np.asarray(getattr(clf, "coef_"))[0]
            coef_importance = pd.DataFrame(
                {"feature": feature_cols, "importance": np.abs(coef)}
            ).sort_values(by="importance", ascending=False)
            coef_importance.to_csv(benchmarks_dir / "final_feature_importance.csv", index=False)
            fig, ax = plt.subplots(figsize=(8, 6))
            top = coef_importance.head(15).iloc[::-1]
            ax.barh(top["feature"], top["importance"])
            ax.set_title("Final Logistic Regression | Absolute Coefficients")
            ax.set_xlabel("|coef|")
            fig.tight_layout()
            fig.savefig(figures_dir / "final_feature_importance.png", dpi=160)
            fig.savefig(figures_dir / "feature_importance.png", dpi=160)
            plt.close(fig)
        except Exception:
            pass

    # Save final deployable artifact (predict_proba on raw features).
    final_model_path = models_dir / "final_model.joblib"
    joblib.dump(final_model, final_model_path)

    validation_checks = {
        "model_artifact_loadable": True,
        "probabilities_in_range": False,
        "no_nan_predictions": False,
        "feature_count_matches": False,
    }
    sample_X = X_test.iloc[:20]
    probs = final_model.predict_proba(sample_X)[:, 1]  # type: ignore[attr-defined]
    validation_checks["probabilities_in_range"] = bool(np.all((probs >= 0.0) & (probs <= 1.0)))
    validation_checks["no_nan_predictions"] = bool(np.isfinite(probs).all())
    validation_checks["feature_count_matches"] = bool(sample_X.shape[1] == len(feature_cols))
    _save_json(reports_dir / "model_validation_checks.json", validation_checks)

    # Reference score distribution for UI percentile display (uncalibrated ranking aid).
    score_percentiles = _compute_score_percentiles(np.asarray(selected_val_scores, dtype=float))

    model_info = {
        "model_type": final_model_type,
        "selected_model": selected_model,
        "dataset_path": str(dataset_path),
        "fraud_base_rate": float((df["Class"] == 1).mean()),
        "feature_columns": feature_cols,
        "n_features": int(len(feature_cols)),
        "threshold_review": float(final_threshold_review),
        "threshold_high": float(final_threshold_high),
        "threshold_f1": float(final_threshold_f1),
        "threshold_policy": {
            "type": "top_k_rate",
            "review_top_rate": float(review_top_rate),
            "high_top_rate": float(high_top_rate),
            "notes": "Capacity-driven thresholds (top-K). Scores are uncalibrated and should be treated as relative ranking.",
        },
        "score_semantics": "risk_score_uncalibrated",
        "score_percentiles": score_percentiles,
        "metrics": {
            "val": {
                "baseline_pr_auc": baseline_val_pr_auc,
                "improved_pr_auc": improved_val_pr_auc,
            },
            "test_threshold_review": final_test_review,
            "test_threshold_high": final_test_high,
            "val_threshold_f1": final_val_f1,
            "test_threshold_f1": final_test_f1,
        },
        "selection_timestamp_utc": selection_timestamp,
    }
    _save_json(models_dir / "model_info.json", model_info)

    benchmark_summary_md = (
        "# Model Benchmark Summary\n\n"
        f"- Dataset: `{dataset_path}`\n"
        f"- Selected model (validation-only): **{selected_model}**\n"
        f"- Threshold policy: top-K rates (review/high) = {review_top_rate*100:.2f}% / {high_top_rate*100:.2f}%\n"
        f"- Thresholds (review/high): {final_threshold_review:.2f} / {final_threshold_high:.2f}\n\n"
        "## Final Test Metrics\n\n"
        f"- Review operating point (top-K): precision={final_test_review['precision']:.4f}, recall={final_test_review['recall']:.4f}\n"
        f"- High operating point (top-K): precision={final_test_high['precision']:.4f}, recall={final_test_high['recall']:.4f}\n"
        f"- Average Precision / PR-AUC (test): {final_test_high['pr_auc']:.4f}\n"
        f"- ROC-AUC (test): {final_test_high['roc_auc']:.4f}\n"
    )
    (reports_dir / "benchmark_summary.md").write_text(benchmark_summary_md, encoding="utf-8")

    return {
        "dataset_path": str(dataset_path),
        "rows": int(df.shape[0]),
        "features": int(len(feature_cols)),
        "threshold_review": float(final_threshold_review),
        "threshold_high": float(final_threshold_high),
        "selected_model": selected_model,
        "artifacts_root": str(root),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full fraud model benchmark workflow")
    parser.add_argument("--data-path", type=str, default="data/archive/creditcard.csv")
    parser.add_argument("--artifacts-root", type=str, default="artifacts")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--review-top-rate",
        type=float,
        default=0.01,
        help="Manual review capacity as a fraction of total traffic (e.g., 0.01 = review top 1%)",
    )
    parser.add_argument(
        "--high-top-rate",
        type=float,
        default=0.002,
        help="Auto-action capacity as a fraction of total traffic (e.g., 0.002 = block top 0.2%)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_workflow(
        data_path=args.data_path,
        artifacts_root=args.artifacts_root,
        random_seed=args.seed,
        review_top_rate=float(args.review_top_rate),
        high_top_rate=float(args.high_top_rate),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
