# Pre-Submission Critical Review (DDM501) — Fraud Detection System

> Alignment Notice (2026-04-18):
> This file is preserved as a historical execution artifact and may contain outdated references
> (for example: older model selection assumptions, endpoint lists, UI behavior, or runtime status).
> Current source-of-truth implementation status is maintained in docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md, README.md, ARCHITECTURE.md, and SYSTEM_SPECIFICATION_DOCUMENT.md.
>


This review is written as a strict academic reviewer + product owner. It is **evidence-based**: observations are grounded in the repository implementation (`src/`, `frontend/`, `deployment/`, `tests/`) and generated artifacts under `artifacts/`.

---

## SECTION A — Strengths

The project addresses a real, high-impact business problem. Fraud scoring is operationally meaningful because the system is designed around **triage under capacity constraints**, not just offline classification. The repository explicitly frames the downstream consumer as a Risk Operations workflow and exposes an actionable decision output (`risk_tier`, `action`) rather than only a model score (see `src/api/schemas.py` and `src/api/main.py`).

The system is genuinely end-to-end: training workflow → artifacts → serving API → frontend demo → monitoring stack → CI/testing. Evidence exists for each layer: deployable model artifacts (`artifacts/models/final_model.joblib`, `artifacts/models/model_info.json`), curves/explainability (`artifacts/figures/final_roc_curve.png`, `artifacts/figures/final_pr_curve.png`, `artifacts/figures/shap_summary.png`), API contract (`src/api/main.py`), dashboard UI (`frontend/index.html`, `frontend/app.js`, `frontend/ui.js`), and monitoring configuration (`deployment/prometheus/*`, `deployment/grafana/*`, plus screenshots under `artifacts/deploys/`).

The decision layer is **explicit and versioned**. Thresholds and policy metadata are stored alongside the model (`artifacts/models/model_info.json`) and surfaced by `/health` and `/predict`, preventing hidden policy drift at runtime (`src/models/loader.py`, `src/api/main.py`).

The repo demonstrates strong engineering hygiene for a student project: integration tests exist for the API and streaming endpoints (`tests/integration/*`), CI enforces a coverage gate (80%) via GitHub Actions (`.github/workflows/ci.yml`), and Docker Compose configuration is present for a full observability stack (`deployment/docker-compose.yml`).

---

## SECTION B — Weaknesses

**Calibration and semantics are underspecified for decision-grade use.** The system correctly warns that the model output is an “uncalibrated risk score”, but it still uses `predict_proba` and reports values in `[0,1]`. Without calibration curves, Brier score, and stability checks, stakeholders can easily misinterpret it as a probability of fraud. This is a documentation + UX risk even if the code is correct.

**Validation strategy is not production-realistic.** The Kaggle dataset has a `Time` column but the pipeline uses random stratified splits (`train_test_split(..., stratify=y)` in `src/pipelines/run_model_workflow.py`). For a fraud system, temporal splits (or at least time-aware stress tests) are a more defensible approximation of deployment drift and delayed labels.

**Threshold justification is only partially business-defensible.** The implemented tiering is capacity-driven (top-K), which is good. However, the report must explicitly connect capacity and costs to business outcomes: review queue size, analyst throughput, false positive cost (friction), false negative cost (loss), and how these drive review/high cutoffs. Right now, the policy is present but the economics are not fully quantified.

**Streaming is a simulation** and needs clearer labeling. `/stream/pull` generates time-ordered events and can sample from dataset-backed pools, but it is not an event-bus ingestion system and it does not model real label delays or account-level aggregation (`src/streaming/simulator.py`, `src/api/main.py`). That is fine for a demo, but must be clearly separated from production claims.

**Explainability is incomplete for the final model.** SHAP is generated as an artifact (`artifacts/figures/shap_summary.png`), but the selected deployable model is logistic regression in the current benchmark run (`artifacts/models/model_info.json`). If SHAP is produced for the LightGBM path only, the paper must either (1) justify SHAP as “candidate model analysis” or (2) provide an explanation artifact for the deployed model (e.g., coefficient-based importance already exists in `artifacts/figures/final_feature_importance.png` and should be emphasized).

---

## SECTION C — Critical Risks

1. **Metric inconsistency risk (PR-AUC naming):** If plots and tables disagree, reviewers will treat results as unreliable. The project previously computed PR curves with trapezoidal area but reported PR-AUC as Average Precision elsewhere. Any mismatch between `artifacts/figures/final_pr_curve.png` and JSON/CSV tables undermines trust.

2. **Policy drift risk between artifacts and deployment:** If Docker/README override thresholds, the deployed behavior may not match the declared decision policy in `model_info.json`. That makes business claims (“we review top 1%”) non-reproducible.

3. **UI misinterpretation risk:** Any “probability” labeling or “fraud detected” phrasing can be interpreted as ground truth classification. This can invalidate Responsible AI claims because it effectively over-claims certainty.

4. **Production gap risk:** Lack of (a) authentication/rate limiting, (b) data contract governance beyond feature-length checks, (c) drift detection, and (d) retraining/rollback procedure means the system is a demo, not production. The report must explicitly say so.

---

## SECTION D — Required Fixes before submission

1. **Make metric definitions internally consistent and explicit.** Use **Average Precision** as PR-AUC across plots/tables, and rename axes/legends accordingly. Ensure the paper uses one definition and states it precisely.

2. **Lock the decision policy as the primary system behavior.** In the paper and in deployment docs, treat the top-K tiering policy (`review_top_rate=1%`, `high_top_rate=0.2%` in `artifacts/models/model_info.json`) as the production-aligned policy. Present F1-optimal thresholding only as an offline comparator.

3. **Remove unintentional threshold overrides.** Ensure Docker Compose and Quickstart use artifact-driven thresholds by default; only override thresholds as an explicit “what-if” demo.

4. **Audit all UI copy.** Ensure the dashboard never claims calibrated probability or confirmed fraud. All outputs must be framed as tiered decisions based on an uncalibrated score.

5. **Strengthen the Production Gap section.** Distinguish simulation vs production in architecture and data flow (labels, feedback loop, drift, security). Mark unverified runtime claims where a reviewer cannot reproduce them from this repo alone.

6. **Update validation scripts to match the API contract.** Any “verification” tooling must reflect the current Pydantic schema to avoid submission-time failures.

