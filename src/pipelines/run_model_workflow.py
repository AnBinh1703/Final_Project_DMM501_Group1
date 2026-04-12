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
    pr_auc = auc(recall, precision)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(recall, precision, label=f"PR AUC={pr_auc:.4f}")
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title(title)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def run_workflow(data_path: str, artifacts_root: str, random_seed: int = 42) -> dict:
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

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["Time"], bins=100)
    ax.set_title("Time Distribution")
    ax.set_xlabel("Time")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    fig.savefig(figures_dir / "time_distribution.png", dpi=160)
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

    feature_cols = [c for c in df.columns if c != "Class"]
    X = df[feature_cols].values
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

    mlflow.set_tracking_uri(f"file:{(Path.cwd() / 'mlruns').resolve()}")
    mlflow.set_experiment("fraud-detection-benchmark")

    # Baseline: Logistic Regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    baseline_model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_seed)
    baseline_model.fit(X_train_scaled, y_train)

    baseline_val_scores = baseline_model.predict_proba(X_val_scaled)[:, 1]
    baseline_test_scores = baseline_model.predict_proba(X_test_scaled)[:, 1]

    baseline_threshold_df = _threshold_sweep(y_val, baseline_val_scores, model_name="logistic_regression")
    baseline_threshold = _best_threshold_from_f1(baseline_threshold_df)

    baseline_default = _evaluate(y_test, baseline_test_scores, threshold=0.5)
    baseline_tuned = _evaluate(y_test, baseline_test_scores, threshold=baseline_threshold)

    baseline_metrics_df = pd.DataFrame([
        {"model": "logistic_regression", "setting": "default_0.5", **baseline_default},
        {"model": "logistic_regression", "setting": "tuned", **baseline_tuned},
    ])
    baseline_metrics_df.to_csv(benchmarks_dir / "baseline_metrics_table.csv", index=False)
    baseline_threshold_df.to_csv(benchmarks_dir / "baseline_threshold_tuning.csv", index=False)

    baseline_cm = confusion_matrix(y_test, (baseline_test_scores >= baseline_threshold).astype(int))
    _plot_confusion_matrix(
        baseline_cm,
        title=f"Baseline Logistic Regression CM (thr={baseline_threshold:.2f})",
        out_path=figures_dir / "baseline_confusion_matrix.png",
    )
    _plot_roc(y_test, baseline_test_scores, "Baseline Logistic Regression ROC", figures_dir / "baseline_roc_curve.png")
    _plot_pr(y_test, baseline_test_scores, "Baseline Logistic Regression PR", figures_dir / "baseline_pr_curve.png")

    baseline_report = classification_report(
        y_test,
        (baseline_test_scores >= baseline_threshold).astype(int),
        output_dict=True,
        zero_division=0,
    )
    _save_json(reports_dir / "baseline_classification_report.json", baseline_report)

    baseline_model_path = models_dir / "baseline_logistic_regression.joblib"
    baseline_scaler_path = models_dir / "baseline_standard_scaler.joblib"
    joblib.dump(baseline_model, baseline_model_path)
    joblib.dump(scaler, baseline_scaler_path)

    with mlflow.start_run(run_name="baseline_logistic_regression"):
        mlflow.log_param("model", "LogisticRegression")
        mlflow.log_param("class_weight", "balanced")
        mlflow.log_param("random_seed", random_seed)
        mlflow.log_param("threshold_tuned", float(baseline_threshold))
        mlflow.log_metric("test_pr_auc", float(baseline_tuned["pr_auc"]))
        mlflow.log_metric("test_roc_auc", float(baseline_tuned["roc_auc"]))
        mlflow.log_metric("test_precision", float(baseline_tuned["precision"]))
        mlflow.log_metric("test_recall", float(baseline_tuned["recall"]))
        mlflow.log_metric("test_f1", float(baseline_tuned["f1"]))
        mlflow.log_artifact(str(benchmarks_dir / "baseline_metrics_table.csv"))
        mlflow.log_artifact(str(figures_dir / "baseline_confusion_matrix.png"))

    # Improved: LightGBM with simple tuning on validation PR-AUC
    neg = max(int((y_train == 0).sum()), 1)
    pos = max(int((y_train == 1).sum()), 1)
    natural_ratio = float(neg / pos)

    param_grid = {
        "n_estimators": [200, 350],
        "learning_rate": [0.03, 0.08],
        "num_leaves": [31, 63],
        "min_child_samples": [20, 80],
        "scale_pos_weight": [1.0, 10.0, 50.0, natural_ratio],
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
    improved_test_scores = best_model.predict_proba(X_test)[:, 1]

    improved_threshold_df = _threshold_sweep(y_val, improved_val_scores, model_name="lightgbm")
    improved_threshold = _best_threshold_from_f1(improved_threshold_df)

    improved_default = _evaluate(y_test, improved_test_scores, threshold=0.5)
    improved_tuned = _evaluate(y_test, improved_test_scores, threshold=improved_threshold)

    improved_metrics_df = pd.DataFrame([
        {"model": "lightgbm", "setting": "default_0.5", **improved_default},
        {"model": "lightgbm", "setting": "tuned", **improved_tuned},
    ])
    improved_metrics_df.to_csv(benchmarks_dir / "improved_metrics_table.csv", index=False)
    improved_threshold_df.to_csv(benchmarks_dir / "improved_threshold_tuning.csv", index=False)

    improved_cm = confusion_matrix(y_test, (improved_test_scores >= improved_threshold).astype(int))
    _plot_confusion_matrix(
        improved_cm,
        title=f"Improved LightGBM CM (thr={improved_threshold:.2f})",
        out_path=figures_dir / "improved_confusion_matrix.png",
    )
    _plot_roc(y_test, improved_test_scores, "Improved LightGBM ROC", figures_dir / "improved_roc_curve.png")
    _plot_pr(y_test, improved_test_scores, "Improved LightGBM PR", figures_dir / "improved_pr_curve.png")

    improved_report = classification_report(
        y_test,
        (improved_test_scores >= improved_threshold).astype(int),
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
    plt.close(fig)

    shap_sample = pd.DataFrame(X_test, columns=feature_cols).sample(n=min(1500, len(X_test)), random_state=random_seed)
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

    with mlflow.start_run(run_name="improved_lightgbm"):
        mlflow.log_param("model", "LightGBM")
        mlflow.log_params({k: v for k, v in best_params.items()})
        mlflow.log_param("natural_scale_pos_weight", natural_ratio)
        mlflow.log_param("random_seed", random_seed)
        mlflow.log_param("threshold_tuned", float(improved_threshold))
        mlflow.log_metric("test_pr_auc", float(improved_tuned["pr_auc"]))
        mlflow.log_metric("test_roc_auc", float(improved_tuned["roc_auc"]))
        mlflow.log_metric("test_precision", float(improved_tuned["precision"]))
        mlflow.log_metric("test_recall", float(improved_tuned["recall"]))
        mlflow.log_metric("test_f1", float(improved_tuned["f1"]))
        mlflow.log_artifact(str(benchmarks_dir / "improved_metrics_table.csv"))
        mlflow.log_artifact(str(figures_dir / "improved_confusion_matrix.png"))
        mlflow.log_artifact(str(figures_dir / "shap_summary.png"))

    threshold_comparison = pd.concat([baseline_threshold_df, improved_threshold_df], ignore_index=True)
    threshold_comparison.to_csv(benchmarks_dir / "threshold_comparison_table.csv", index=False)

    comparison_df = pd.DataFrame(
        [
            {
                "model": "logistic_regression",
                "threshold": baseline_threshold,
                "precision": baseline_tuned["precision"],
                "recall": baseline_tuned["recall"],
                "f1": baseline_tuned["f1"],
                "roc_auc": baseline_tuned["roc_auc"],
                "pr_auc": baseline_tuned["pr_auc"],
            },
            {
                "model": "lightgbm",
                "threshold": improved_threshold,
                "precision": improved_tuned["precision"],
                "recall": improved_tuned["recall"],
                "f1": improved_tuned["f1"],
                "roc_auc": improved_tuned["roc_auc"],
                "pr_auc": improved_tuned["pr_auc"],
            },
        ]
    )
    comparison_df.to_csv(benchmarks_dir / "model_comparison_table.csv", index=False)

    selected_model = "lightgbm" if improved_tuned["pr_auc"] >= baseline_tuned["pr_auc"] else "logistic_regression"
    selection_summary = {
        "selected_model": selected_model,
        "selection_timestamp_utc": datetime.now(UTC).isoformat(),
        "selection_basis": "Primary=PR-AUC and Recall at tuned threshold; secondary=F1 and precision trade-off",
        "baseline_tuned_metrics": baseline_tuned,
        "improved_tuned_metrics": improved_tuned,
    }
    _save_json(reports_dir / "model_selection_summary.json", selection_summary)

    validation_checks = {
        "model_artifact_loadable": False,
        "probabilities_in_range": False,
        "no_nan_predictions": False,
        "feature_count_matches": False,
    }

    selected_path = improved_model_path if selected_model == "lightgbm" else baseline_model_path
    loaded_model = joblib.load(selected_path)
    validation_checks["model_artifact_loadable"] = True

    sample_X = X_test[:20]
    if selected_model == "logistic_regression":
        loaded_scaler = joblib.load(baseline_scaler_path)
        sample_X = loaded_scaler.transform(sample_X)

    probs = loaded_model.predict_proba(sample_X)[:, 1]
    validation_checks["probabilities_in_range"] = bool(np.all((probs >= 0.0) & (probs <= 1.0)))
    validation_checks["no_nan_predictions"] = bool(np.isfinite(probs).all())
    validation_checks["feature_count_matches"] = bool(sample_X.shape[1] == len(feature_cols))
    _save_json(reports_dir / "model_validation_checks.json", validation_checks)

    comparison_csv_block = comparison_df.to_csv(index=False)
    benchmark_summary_md = (
        "# Model Benchmark Summary\n\n"
        f"- Dataset: `{dataset_path}`\n"
        f"- Baseline tuned threshold: {baseline_threshold:.2f}\n"
        f"- Improved tuned threshold: {improved_threshold:.2f}\n"
        f"- Selected model: **{selected_model}**\n\n"
        "## Tuned Metrics (CSV)\n\n"
        "```csv\n"
        f"{comparison_csv_block}"
        "```\n"
    )
    (reports_dir / "benchmark_summary.md").write_text(benchmark_summary_md, encoding="utf-8")

    return {
        "dataset_path": str(dataset_path),
        "rows": int(df.shape[0]),
        "features": int(len(feature_cols)),
        "baseline_threshold": float(baseline_threshold),
        "improved_threshold": float(improved_threshold),
        "selected_model": selected_model,
        "artifacts_root": str(root),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run full fraud model benchmark workflow")
    parser.add_argument("--data-path", type=str, default="data/raw/creditcard.csv")
    parser.add_argument("--artifacts-root", type=str, default="artifacts")
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_workflow(data_path=args.data_path, artifacts_root=args.artifacts_root, random_seed=args.seed)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
