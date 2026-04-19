# Master-Level Report — End-to-End Fraud Detection System (Risk Scoring → Decision Intelligence)

## 2026-04-18 Alignment Notice

This file remains as historical report content.

Current source-of-truth for implemented architecture, API contracts, lifecycle workflow,
and implemented-vs-proposed matrix is:
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`

Current system framing is:
Real-Time Banking Transaction Fraud Detection and Decision Support System.

Important update:
- Alert/case/timeline APIs are now implemented in backend.
- Frontend case operations are now API-backed.
- Persistence remains in-memory (demo-level simulated) and is explicitly labeled.

**Repository:** `Final_Project_DMM501_Group1`  
**Evidence directory:** `artifacts/` (models, figures, tables, reports)  
**Serving stack:** FastAPI + Prometheus metrics + Docker Compose monitoring (Prometheus/Grafana)  
**Core stance:** Fraud detection is not “a classifier”; it is **decision-making under asymmetric costs and limited capacity**.

---

## 1. Introduction

Fraud detection systems exist to reduce financial losses and operational burden by identifying suspicious transactions early enough to trigger an intervention. However, the operational problem is not simply “predict fraud”; it is to **allocate scarce interventions** (manual review, step-up authentication, blocking) to the subset of traffic where the expected benefit outweighs the harm from false positives.

This project implements an end-to-end ML system that converts transaction features into an **uncalibrated risk score** and then maps that score to **tiered actions** via an explicit decision policy. The system is instrumented for observability, packaged for reproducibility, and tested for correctness of contracts and failure modes.

---

## 2. Problem Definition & Business Context

### 2.1 Business problem

Card payment fraud produces direct loss (chargebacks, reimbursed losses) and indirect costs (manual review, customer support, churn due to friction). A scoring service is valuable only if it supports operational decisions:

1. **Allow** low-risk transactions without friction.
2. **Review / step-up** medium-risk transactions when human or automated capacity exists.
3. **Block / hold** very high-risk transactions when the risk justifies stronger intervention.

### 2.2 Success criteria (model + system + business)

This repo makes success multi-dimensional:

- **Model ranking quality:** measured by Average Precision (PR-AUC) and ROC-AUC on a held-out test set (`artifacts/figures/final_pr_curve.png`, `artifacts/figures/final_roc_curve.png`).
- **Operational operating points:** measured by precision/recall under the **review** and **high** tiers defined by the decision policy (`artifacts/models/model_info.json`).
- **System reliability:** health checks, typed API schemas, and Prometheus metrics (`src/api/main.py`, `src/monitoring/metrics.py`).

This framing is important: many models can look “good” offline, but only a policy-grounded operating point yields defendable business behavior.

---

## 3. Dataset & Data Characteristics

### 3.1 Dataset

The system uses the Kaggle Credit Card Fraud dataset (`data/archive/creditcard.csv`), which contains 30 input features (`Time`, `V1..V28`, `Amount`) and a binary target `Class`. A schema validation artifact is generated at `artifacts/reports/dataset_schema.json`.

### 3.2 Class imbalance and evaluation implications

Fraud is extremely rare (≈0.17%). In such regimes:

- Accuracy is not meaningful because predicting “non-fraud” for every transaction yields very high accuracy.
- Precision and recall must be interpreted jointly at operational thresholds, because the business impact depends on how many cases are flagged.
- Average Precision (AP) is an appropriate scalar ranking metric because it emphasizes performance on the positive class.

### 3.3 Representational limitation

Features `V1..V28` are PCA-transformed, which reduces interpretability. The report therefore treats explainability outputs as **model-behavior evidence** rather than causal explanations, and avoids claims about “why fraud happens” at a semantic feature level.

---

## 4. ML Pipeline Design

The benchmark workflow is implemented in `src/pipelines/run_model_workflow.py` and generates an evidence pack under `artifacts/`:

1. **Ingestion + validation** (schema, missing values, duplicates).
2. **Train/validation/test split** (70/15/15 with stratification; exported to `artifacts/reports/split_info.json`).
3. **Baseline model:** Logistic Regression within a scaling pipeline.
4. **Candidate model:** LightGBM with a small hyperparameter grid.
5. **Selection rule:** validation-only selection with a primary criterion of validation AP (PR-AUC), with tie-break on recall at the review operating point (`artifacts/reports/model_selection_summary.json`).
6. **Artifact production:** deployable model binary + model metadata used by the serving API (`artifacts/models/final_model.joblib`, `artifacts/models/model_info.json`).

### 4.1 Trade-off: stratified split vs time-aware evaluation

This project uses stratified random splitting to produce stable evaluation and a clean demonstration pipeline. In production fraud systems, a time-aware split is usually required because concept drift and delayed labels are common. The report therefore treats offline metrics as **necessary but not sufficient** evidence of real-world effectiveness.

---

## 5. Model Evaluation & Selection

Two modeling approaches are implemented and compared:

- **Logistic Regression (baseline):** strong, interpretable baseline with stable behavior under imbalance using class weighting.
- **LightGBM (improved candidate):** non-linear model with higher expressiveness, tuned using a small parameter grid.

The benchmark generates:

- ROC and PR curves (`artifacts/figures/*roc_curve.png`, `artifacts/figures/*pr_curve.png`).
- Threshold sweeps (`artifacts/figures/*threshold_sweep.png` and `artifacts/benchmarks/*threshold_tuning.csv`).
- Model comparison tables (`artifacts/benchmarks/model_comparison_table.csv`).

The selected deployable model for the current evidence pack is **logistic regression** (see `artifacts/models/model_info.json` and `artifacts/reports/model_selection_summary.json`).

---

## 6. Risk Score Analysis (Calibration Discussion)

### 6.1 Risk score semantics (critical)

The API returns `risk_score ∈ [0,1]`, computed from `predict_proba`, but it must be treated as:

**Risk score = an uncalibrated ranking signal used for prioritization, not a calibrated probability of fraud.**

This is explicit in the model metadata (`artifacts/models/model_info.json` → `score_semantics: "risk_score_uncalibrated"`) and surfaced through `/health` and `/predict` (`src/api/main.py`).

### 6.2 Why it is not a probability

Even though the output is bounded in `[0,1]`, several factors prevent probability claims:

- class imbalance and reweighting change the effective learning objective,
- calibration is not validated or enforced (no calibration curve/Brier score gate),
- dataset shift is not modeled (random split, no time-aware stress test),
- decision policy uses ranking (top-K capacity), which does not require calibrated probabilities.

### 6.3 What would be required for probability claims (production gap)

To interpret outputs as probabilities, a production system would require post-hoc calibration (e.g., isotonic or Platt scaling), stability analysis over time, and monitoring of calibration error under drift. This project does not implement those, and therefore does not claim probabilistic semantics.

---

## 7. Decision Layer (Threshold Strategy)

### 7.1 Primary policy: capacity-driven top-K tiering

The deployed decision strategy is a **two-tier capacity policy** recorded in `artifacts/models/model_info.json`:

- **Review tier:** flag approximately the top 1% of transactions by risk score (`review_top_rate = 0.01`, `threshold_review ≈ 0.7391`).
- **High tier:** flag approximately the top 0.2% by risk score (`high_top_rate = 0.002`, `threshold_high ≈ 0.9999`).

This policy is defensible because it ties model outputs to operational capacity: the system can guarantee that the review queue size is proportional to traffic volume, even when the fraud base rate changes.

### 7.2 Offline comparator: F1-optimal threshold

For reference only (not the primary deployment policy), the workflow records an F1-optimal threshold derived from validation (`threshold_f1 = 0.99` in `artifacts/models/model_info.json`). This comparator is useful to demonstrate the difference between:

- a **metric-optimal** threshold on a fixed test regime, and
- a **capacity-optimal** threshold that meets operational constraints.

### 7.3 Test operating-point evidence (final model)

From `artifacts/models/model_info.json` (test split):

- **Review tier (top-K):** precision ≈ 0.1462, recall ≈ 0.8514 (large review volume; high recall).
- **High tier (top-K):** precision ≈ 0.8429, recall ≈ 0.7973 (smaller volume; higher precision).
- **Average Precision (AP / PR-AUC):** ≈ 0.7694; **ROC-AUC:** ≈ 0.9652.

These operating points show the intended “funnel”: a broad review queue for recall and a narrow high-risk tier for strong interventions.

---

## 8. System Architecture

The system follows a layered architecture:

1. **Training + benchmarking** produces model artifacts and evidence (`src/pipelines/run_model_workflow.py`, `artifacts/`).
2. **Serving API** loads artifacts and exposes `/predict`, `/health`, `/metrics` (`src/api/main.py`, `src/models/loader.py`).
3. **Frontend dashboard** calls the live API and displays tiered decisions (`frontend/`).
4. **Observability stack** scrapes metrics and renders dashboards/alerts (`deployment/prometheus/*`, `deployment/grafana/*`).

This separation is production-aligned: model iteration is offline, serving is online, and the dashboard is a consumer of the serving contract.

---

## 9. API & Serving Layer

The API is implemented in FastAPI with Pydantic schemas (`src/api/main.py`, `src/api/schemas.py`).

Key endpoints:

- `GET /health`: returns model/version/threshold metadata.
- `POST /predict`: accepts `features` (ordered vector) or `features_by_name`, returns `risk_score`, `risk_tier`, and `action`.
- `GET /metrics`: Prometheus metrics endpoint.
- `GET /stream/pull`: returns already-scored simulated stream events (see Section 11).

The API enforces an input contract to prevent silent errors: feature length mismatch yields HTTP 422.

---

## 10. Frontend & Decision Interface

The dashboard is a decision-support UI, not a “fraud confirmation UI”. It:

- polls backend health to display model/version/policy metadata,
- streams scored events from `/stream/pull`,
- visualizes tiered decisions (LOW/REVIEW/HIGH) and actions (allow/review/block),
- allows basic queue handling for review cases (frontend-only).

The UI includes explicit copy that `risk_score` is **not** a fraud probability (`frontend/index.html`, `frontend/ui.js`).

---

## 11. Streaming & Simulation

Streaming is implemented as a **simulation** suitable for demo and stress testing, not as a production ingestion pipeline.

- `/stream/pull` returns time-ordered synthetic or dataset-backed events generated by `src/streaming/simulator.py`.
- The simulator includes burst traffic and rare “attack windows” to emulate operational spikes.
- Ground truth labels are not returned from the stream endpoint, preventing a misleading “oracle” demo behavior.

Production-grade streaming would require an event bus, exactly-once/at-least-once semantics, deduplication, and delayed label ingestion. These are out of scope for this project and documented as a production gap.

---

## 12. Monitoring & Observability

The API exposes Prometheus metrics (`src/monitoring/metrics.py`), and Docker Compose provisions:

- Prometheus scrape configuration and alert rules (`deployment/prometheus/prometheus.yml`, `deployment/prometheus/alerts.yml`),
- Grafana dashboards (`deployment/grafana/dashboards/fraud_api.json`).

This supports real system signals (latency, error rates, prediction tiers), which is required to argue “production awareness.”

---

## 13. Testing & CI/CD

The repository includes unit and integration tests (`tests/`) and a CI pipeline with an 80% coverage gate (`.github/workflows/ci.yml`). The test suite validates:

- API contracts and error handling,
- dataset sampling behavior and “no labels leakage” in public endpoints,
- model-loading behavior and artifact presence.

Docker builds and Compose configuration are validated in CI (`.github/workflows/docker.yml`).

---

## 14. Responsible AI

The project includes a Responsible AI document (`RESPONSIBLE_AI.md`) with:

- fairness limits due to missing protected attributes in the dataset,
- proxy slice recommendations (amount/time buckets),
- explainability artifacts (SHAP for LightGBM and coefficient-based importance for logistic regression),
- privacy stance and recommended logging policy.

The report avoids claiming demographic fairness guarantees given the dataset constraints.

---

## 15. Limitations & Production Gap

This project is demo-grade and must be presented honestly:

- no authentication/rate limiting in the API,
- no drift detection or retraining automation,
- random stratified split rather than time-aware evaluation,
- simulation-based streaming rather than real ingestion,
- no calibrated probability claims.

These are acceptable for DDM501 if clearly stated, justified, and scoped as future work rather than hidden assumptions.

---

## 16. Conclusion

This project demonstrates an end-to-end fraud detection system that is more than “a model”: it is a **policy-driven decision service** with artifacts, observability, tests, and deployment configuration. The strongest technical contribution is the explicit separation of:

1. **risk scoring** (ranking signal), and  
2. **decision intelligence** (tiered actions constrained by operational capacity).

The remaining work to reach production readiness is primarily in calibration, time-aware validation, security, and drift/feedback-loop design, all of which are clearly identified.

