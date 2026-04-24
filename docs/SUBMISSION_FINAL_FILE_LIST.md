# Submission Final File List

This file summarizes the final submission-relevant files, the current changed scope in the repository, and recommended commit messages.

## 1. Required Submission Files

Core required files present in this repository:

- `README.md`
- `ARCHITECTURE.md`
- `CONTRIBUTING.md`
- `requirements.txt`
- `deployment/api/Dockerfile`
- `deployment/frontend/Dockerfile`
- `deployment/mlflow/Dockerfile`
- `deployment/docker-compose.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/docker.yml`

Final report files:

- `latex/COMPLETE_FRAUD_DETECTION_REPORT.tex`
- `latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf`

## 2. Current Changed Files in the Working Tree

### Documentation and report scope

- `.gitignore`
- `README.md`
- `ARCHITECTURE.md`
- `CONTRIBUTING.md`
- `latex/COMPLETE_FRAUD_DETECTION_REPORT.tex`
- `latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf`

### Synced model/artifact evidence scope

- `artifacts/benchmarks/improved_hyperparameter_tuning.csv`
- `artifacts/benchmarks/improved_metrics_table.csv`
- `artifacts/benchmarks/shap_importance_table.csv`
- `artifacts/figures/shap_summary.png`
- `artifacts/mlflow.db`
- `artifacts/models/improved_lightgbm.joblib`
- `artifacts/models/model_info.json`
- `artifacts/models/versions/index.json`
- `artifacts/reports/latest_model_run.json`
- `artifacts/reports/model_run_history.jsonl`
- `artifacts/reports/model_selection_summary.json`
- `artifacts/models/versions/v0002_20260424T083412Z/`

## 3. Recommended Commit Strategy

### Preferred: split into 2 commits

Commit 1: docs and final report

Recommended commit message:

`docs(report): finalize full fraud detection report and submission docs`

Files:

- `.gitignore`
- `README.md`
- `ARCHITECTURE.md`
- `CONTRIBUTING.md`
- `latex/COMPLETE_FRAUD_DETECTION_REPORT.tex`
- `latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf`
- `docs/SUBMISSION_FINAL_FILE_LIST.md`

Commit 2: model evidence and generated artifacts

Recommended commit message:

`artifacts(model): sync v0002 benchmark outputs and report evidence`

Files:

- all modified files under `artifacts/`

### Acceptable: single final submission commit

If the team prefers a single commit, use:

`docs(report): finalize submission package, report, and synced artifacts`

## 4. Why This Split Is Better

- The first commit is easy for the instructor to read because it isolates report and documentation work.
- The second commit makes it explicit that benchmark outputs and model metadata were regenerated and synchronized.
- If you need to discuss contribution during Q&A, this split makes it easier to explain which changes are narrative/documentation work and which are pipeline-generated evidence.

## 5. Final Pre-Commit Check

Before pushing, confirm:

- the final report still matches model artifact version `v0002_20260424T083412Z`
- the PDF builds successfully
- the docs and report all reference the same system behavior
- the team can explain why `risk_score` is uncalibrated and why thresholds are top-K capacity-driven
- official member names are mapped clearly to git/GitHub identities if aliases differ
