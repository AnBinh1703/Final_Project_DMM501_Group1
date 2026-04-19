# Final E2E Report — Real-Time Fraud Detection ML System (Evidence-Based)

> Alignment Notice (2026-04-18):
> This file is preserved as a historical execution artifact and may contain outdated references
> (for example: older model selection assumptions, endpoint lists, UI behavior, or runtime status).
> Current source-of-truth implementation status is maintained in docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md, README.md, ARCHITECTURE.md, and SYSTEM_SPECIFICATION_DOCUMENT.md.
>


**Repository:** `Final_Project_DMM501_Group1`  
**Report date:** 2026-04-14  
**Scope:** DATA → ML PIPELINE → MODEL → API → FRONTEND → MONITORING → DEPLOYMENT → DEMO  
**Strict evidence rule:** All numbers and claims are grounded in repository files and generated artifacts under `artifacts/`. If something was not executed/observed live in this environment, it is marked **Unverified**.

---

## 0) Evidence Pack (What was extracted)

### 0.1 Dataset evidence (Kaggle credit card fraud)
- Dataset file in repo: `data/archive/creditcard.csv`
- Schema validation output: `artifacts/reports/dataset_schema.json`
- EDA summary: `artifacts/reports/eda_summary.json`
- Class imbalance: `artifacts/reports/class_distribution.json`
- EDA figures: `artifacts/figures/class_distribution.png`, `artifacts/figures/amount_distribution.png`, `artifacts/figures/time_distribution.png`, etc.

### 0.2 Model artifact evidence (deployable model + metadata)
- Deployable model artifact: `artifacts/models/final_model.joblib`
- Deploy metadata (feature order, threshold, dataset path, selection timestamp, tuned metrics): `artifacts/models/model_info.json`
- Model selection summary (baseline vs improved tuned metrics): `artifacts/reports/model_selection_summary.json`
- Model validation checks (artifact loadable, probabilities sane): `artifacts/reports/model_validation_checks.json`

### 0.3 Model evaluation & explainability figures
- Baseline curves: `artifacts/figures/baseline_roc_curve.png`, `artifacts/figures/baseline_pr_curve.png`
- Improved curves: `artifacts/figures/improved_roc_curve.png`, `artifacts/figures/improved_pr_curve.png`
- Threshold sweeps: `artifacts/figures/baseline_threshold_sweep.png`, `artifacts/figures/improved_threshold_sweep.png`, `artifacts/figures/threshold_comparison.png`
- Model comparison chart: `artifacts/figures/model_comparison.png`
- SHAP: `artifacts/figures/shap_summary.png`, table `artifacts/benchmarks/shap_importance_table.csv`

### 0.4 API evidence (implementation + contract)
- FastAPI app: `src/api/main.py`
- Pydantic schemas: `src/api/schemas.py`
- Model loading: `src/models/loader.py`
- Dataset sampling endpoint logic: `src/data/samples.py`
- Prometheus metrics implementation: `src/monitoring/metrics.py`
- Verification script (captures intended runtime checks): `verify_system.py` (**Unverified** here because backend was not launched in this environment)

### 0.5 Frontend evidence (real UI implementation)
- UI entry: `frontend/index.html`
- Streaming + logic: `frontend/app.js`
- API client + response validation: `frontend/api-client.js`
- Transaction generators: `frontend/demo-data.js`
- Real demo sample pool: `frontend/real-samples.json` (parsed: `n_samples=240`, `fraud_samples=60`, `n_features=30`)
- UI screenshot captured (layout evidence): `artifacts/figures/frontend_dashboard.png` (**Note:** backend not running in screenshot)

### 0.6 Monitoring & deployment evidence
- Docker Compose full stack: `deployment/docker-compose.yml`
- API Dockerfile: `deployment/api/Dockerfile`
- Frontend Dockerfile: `deployment/frontend/Dockerfile`
- Prometheus scrape config: `deployment/prometheus/prometheus.yml`
- Prometheus alert rules: `deployment/prometheus/alerts.yml`
- Grafana provisioning + dashboard JSON: `deployment/grafana/provisioning/*`, `deployment/grafana/dashboards/fraud_api.json`

### 0.7 Testing & CI/CD evidence
- Tests: `tests/unit/*`, `tests/integration/*`, `tests/model/*`, `tests/data/*`
- CI workflow (coverage gate): `.github/workflows/ci.yml`
- Docker build + compose validation workflow: `.github/workflows/docker.yml`

---

## 1) Problem Definition

### 1.1 Problem statement
Build an end-to-end ML system that assigns a fraud risk score to credit-card transactions and serves predictions via an API, with a demo dashboard for near-real-time monitoring and an observability stack (metrics, dashboards, alerting).

### 1.2 Business context
Credit-card fraud creates direct losses and operational costs. A scoring service enables:
- **Risk ops:** triage and prioritize suspicious transactions (human-in-the-loop)
- **Engineering:** consistent inference API with monitoring and deployment
- **Audit/compliance:** reproducible metrics + explainability artifacts (within dataset limits)

### 1.3 System success criteria (as implemented)
The project makes the operating threshold an explicit policy stored in metadata and returned by the API:
- Model selection uses **PR-AUC** as a primary criterion (implemented rule in `src/pipelines/run_model_workflow.py`).
- Serving must expose operational metrics (`/metrics`) and support health checks (`/health`).
- The demo UI must call the real backend `/predict` (not mock predictions).

---

## 2) Dataset Analysis (Kaggle Credit Card Fraud)

### 2.1 Dataset schema (evidence)
From `artifacts/reports/dataset_schema.json`:
- Shape: **284,807 rows × 31 columns**
- Columns match expected Kaggle schema: `Time, V1..V28, Amount, Class` (`matches_expected_schema=true`)

### 2.2 Imbalance (why accuracy is misleading)
From `artifacts/reports/class_distribution.json` and `artifacts/reports/eda_summary.json`:
- Non-fraud (Class=0): **284,315** (≈ **99.8273%**)
- Fraud (Class=1): **492** (≈ **0.1727%**)
- Fraud ratio: **0.001727485630620034** (≈ 0.17%)

**Implication:** Accuracy can be ~99.8–99.9% even for weak fraud detection, because predicting “non-fraud” almost always is “right”.  
Therefore, this repo emphasizes:
- **PR-AUC** (precision-recall area under curve) for imbalanced problems
- **Precision/Recall at an operating threshold** (because production behavior depends on threshold)

### 2.3 Data quality notes (evidence)
From `artifacts/reports/eda_summary.json`:
- Duplicate rows: **1081**
- Missing values: exported to `artifacts/reports/missing_values.csv` (file exists; counts are computed by the workflow)

### 2.4 Dataset figures (embedded)
Class distribution:

![Class Distribution (Fraud vs Non-fraud)](artifacts/figures/class_distribution.png)

Amount distribution:

![Amount Distribution](artifacts/figures/amount_distribution.png)

Time distribution:

![Time Distribution](artifacts/figures/time_distribution.png)

---

## 3) ML Pipeline (Data → Artifacts)

### 3.1 Pipeline entrypoint (real implementation)
Primary end-to-end benchmark workflow: `src/pipelines/run_model_workflow.py`.

This script produces:
- Schema validation outputs: `artifacts/reports/dataset_schema.json`
- EDA outputs: `artifacts/reports/eda_summary.json`, `artifacts/figures/*.png`
- Baseline model artifacts and evaluation
- Improved model training + hyperparameter sweep
- Threshold sweeps + comparison
- SHAP explainability for LightGBM
- Model selection summary + deployable model export

### 3.2 Train/val/test split (evidence)
From `artifacts/reports/split_info.json`:
- Train: **199,364**
- Validation: **42,721**
- Test: **42,722**
- Features: **30**
- Seed: **42**

### 3.3 MLflow tracking (implementation status)
`src/pipelines/run_model_workflow.py` configures MLflow to log metrics/artifacts using a SQLite backend:
- Backend file used by the workflow: `artifacts/mlflow.db` (exists)

Docker Compose also defines an MLflow service (`deployment/docker-compose.yml`), but:
- **Unverified** in this environment (Compose was not launched for this report).

---

## 4) Model Training (Baseline vs Improved) — Evidence Tables

### 4.1 Models implemented
From `src/pipelines/run_model_workflow.py` and produced artifacts in `artifacts/models/`:

**Baseline**
- Model: Logistic Regression inside a scikit-learn `Pipeline([StandardScaler, LogisticRegression])`
- Class imbalance handling: `class_weight="balanced"`
- Artifact: `artifacts/models/baseline_logistic_regression_pipeline.joblib`

**Improved**
- Model: `lightgbm.LGBMClassifier`
- Hyperparameter search: `sklearn.model_selection.ParameterGrid` over:
  - `n_estimators` ∈ {250, 450}
  - `learning_rate` ∈ {0.03, 0.08}
  - `num_leaves` ∈ {31, 63}
  - `scale_pos_weight` ∈ {10.0, natural_ratio}
- Sweep results saved: `artifacts/benchmarks/improved_hyperparameter_tuning.csv`
- Artifact: `artifacts/models/improved_lightgbm.joblib`

### 4.2 Tuned test metrics (ground truth from artifacts)
From `artifacts/reports/model_selection_summary.json` (and mirrored in `artifacts/models/model_info.json`):

| Model | Tuned Threshold | PR-AUC | ROC-AUC | Precision | Recall | F1 | TN | FP | FN | TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression (baseline) | **0.99** | **0.7928733741** | **0.9679722632** | **0.6741573034** | **0.8108108108** | **0.7361963190** | 42619 | 29 | 14 | 60 |
| LightGBM (improved) | **0.84** | **0.7160881658** | **0.8828017663** | **0.8852459016** | **0.7297297297** | **0.8000000000** | 42641 | 7 | 20 | 54 |

### 4.3 Model selection outcome (deployable choice)
From `artifacts/reports/model_selection_summary.json`:
- `selected_model`: **logistic_regression**
- Selection criterion (implemented): selects LightGBM only if improved tuned PR-AUC ≥ baseline tuned PR-AUC.

From `artifacts/models/model_info.json` (deploy metadata used by API loader):
- `model_type`: **logistic_regression_pipeline**
- `threshold`: **0.99**
- `n_features`: **30**
- `feature_columns`: `Time, V1..V28, Amount`
- `dataset_path`: `data/archive/creditcard.csv`

### 4.4 Evaluation figures (embedded)
Baseline:

![Baseline ROC Curve](artifacts/figures/baseline_roc_curve.png)

![Baseline PR Curve](artifacts/figures/baseline_pr_curve.png)

Improved:

![Improved ROC Curve](artifacts/figures/improved_roc_curve.png)

![Improved PR Curve](artifacts/figures/improved_pr_curve.png)

Comparison:

![Model Comparison (Tuned Metrics)](artifacts/figures/model_comparison.png)

---

## 5) Threshold Tuning (Operating Point = Policy)

### 5.1 How threshold tuning is implemented (evidence)
In `src/pipelines/run_model_workflow.py`:
- Validation scores are swept across thresholds from 0.01 to 0.99.
- “Best threshold” is selected by **maximizing F1** on validation (`_best_threshold_from_f1`).
- The chosen threshold is then used to compute tuned test metrics.

### 5.2 Threshold evidence artifacts
- Baseline sweep table: `artifacts/benchmarks/baseline_threshold_tuning.csv`
- Improved sweep table: `artifacts/benchmarks/improved_threshold_tuning.csv`
- Overlay comparison table: `artifacts/benchmarks/threshold_comparison_table.csv`
- Sweep plots:
  - `artifacts/figures/baseline_threshold_sweep.png`
  - `artifacts/figures/improved_threshold_sweep.png`
  - `artifacts/figures/threshold_comparison.png`

### 5.3 Threshold figures (embedded)

![Baseline Threshold Sweep](artifacts/figures/baseline_threshold_sweep.png)

![Improved Threshold Sweep](artifacts/figures/improved_threshold_sweep.png)

![Threshold Comparison (F1 overlay)](artifacts/figures/threshold_comparison.png)

### 5.4 Interpretation (grounded in the tuned metrics table)
- Baseline tuned threshold **0.99** yields higher PR-AUC than the improved model in this artifact set.
- Improved model at threshold **0.84** achieves higher **precision** (0.8852) but lower **recall** (0.7297) than baseline tuned recall (0.8108).

**Why this matters operationally:** threshold sets the review/alert volume. This system makes threshold explicit and traceable:
- stored in `artifacts/models/model_info.json`
- returned in API responses from `/predict`
- used by frontend to label Fraud vs Suspicious vs Normal

---

## 6) Model Explainability (SHAP) — Evidence

### 6.1 What explainability is implemented
`src/pipelines/run_model_workflow.py` computes SHAP values for the LightGBM model:
- uses `shap.TreeExplainer(best_model)`
- plots SHAP summary

### 6.2 Explainability artifacts
- SHAP summary plot: `artifacts/figures/shap_summary.png`
- SHAP importance table: `artifacts/benchmarks/shap_importance_table.csv`

![SHAP Summary Plot (LightGBM)](artifacts/figures/shap_summary.png)

### 6.3 Important constraint (not assumed)
SHAP is generated for the **LightGBM** model even though the **deployable selected model** in this artifact set is Logistic Regression. This is still valuable as:
- evidence of explainability capability for a strong candidate model
- an analysis artifact for the modeling phase

Deploy-time explainability for Logistic Regression (e.g., coefficients) is **not** separately exported as a dedicated artifact in this repo (no claim made).

---

## 7) System Architecture (E2E Flow)

### 7.1 High-level architecture (implemented components)
Evidence in `ARCHITECTURE.md`, plus code and deployment config:
- **Training/benchmarking** writes artifacts to `artifacts/`
- **API** loads `artifacts/models/final_model.joblib` and serves predictions
- **Frontend** streams transactions and calls `/predict`
- **Prometheus** scrapes `/metrics`
- **Grafana** visualizes metrics and alerting state
- **Docker Compose** wires services together

### 7.2 Architecture diagram (Mermaid, matches repo)
```mermaid
flowchart LR
  U[User / Reviewer] --> FE[Frontend Dashboard]
  FE -->|HTTP POST /predict| API[FastAPI Serving]
  API -->|joblib load| ART[(artifacts/ volume)]

  subgraph Observability
    API -->|GET /metrics| PROM[Prometheus]
    PROM --> GRAF[Grafana Dashboard]
    PROM --> RULES[Alert Rules]
  end

  subgraph Training
    DS[(creditcard.csv)] --> PIPE[run_model_workflow.py]
    PIPE --> ART
    PIPE --> MLF[MLflow (sqlite)]
  end
```

### 7.3 Data path and contract boundaries (actual)
**Feature contract** end-to-end for the Kaggle model:
- 30 floats in this order: `[Time, V1..V28, Amount]`
- Stored in `artifacts/models/model_info.json` under `feature_columns`
- Frontend validates feature length in `frontend/api-client.js` (requires exactly 30)
- API validates feature length using `loaded.n_features` in `src/api/main.py`

---

## 8) API Design (FastAPI) — Contract + Behavior

### 8.1 API entrypoint and model loading
- App: `src/api/main.py`
- Startup behavior: loads model once at startup via `maybe_load_model_from_env()` from `src/models/loader.py`

**Model load precedence (evidence: `src/models/loader.py`):**
1. If `MODEL_PATH` is set: load that exact path
2. Else try defaults:
   - `artifacts/models/final_model.joblib`
   - `artifacts/model.joblib`

### 8.2 Endpoints (implemented)
From `src/api/main.py`:

| Endpoint | Method | Purpose | Evidence |
|---|---:|---|---|
| `/health` | GET | readiness + model metadata | `src/api/main.py` |
| `/predict` | POST | score fraud probability + label via threshold | `src/api/main.py`, `src/api/schemas.py` |
| `/metrics` | GET | Prometheus exposition | `src/api/main.py`, `src/monitoring/metrics.py` |
| `/dataset/samples` | GET | dataset-backed sample rows (mixed/fraud/legit) | `src/api/main.py`, `src/data/samples.py` |
| `/features/schema` | GET | feature names/shape | `src/api/main.py` |
| `/features/random` | GET | random feature vector generator | `src/api/main.py`, `src/features/random_features.py` |

### 8.3 Request/response schemas (evidence)
From `src/api/schemas.py`:

**PredictRequest**
- `features: list[float] | None`
- `features_by_name: dict[str, float] | None`

**PredictResponse**
- `request_id: str`
- `risk_score: float` (0..1, uncalibrated)
- `fraud_label: int` (0/1)
- `threshold: float` (0..1)
- `model_version: str`
- `model_type: str | None`
- `n_features: int | None`
- `feature_names: list[str] | None`
- `selection_timestamp_utc: str | None`

### 8.4 Input validation and failure modes (actual)
From `src/api/main.py`:
- Returns **503** if model not loaded (`MODEL_PATH` missing/invalid)
- Returns **422** if:
  - neither `features` nor `features_by_name` provided
  - both provided
  - feature length mismatch vs model metadata
  - non-finite values (NaN/inf)
- Returns **500** if loaded model lacks `predict_proba`

### 8.5 Real API examples (capture status)
**Unverified runtime output in this environment** (Python dependencies for FastAPI/Uvicorn were not installed during report generation).  
However, the repo provides a verification harness to capture real outputs:
- Run verification script: `verify_system.py` (**this script uses `/health`, `/dataset/samples`, `/predict`, `/metrics`**)

**To capture real evidence JSON for submission (recommended):**
1. Install deps (per `QUICK_START.md`)
2. Run API with the deployable artifact:
   ```bash
   MODEL_PATH=artifacts/models/final_model.joblib \
   MODEL_VERSION=creditcard-production-v1 \
   FRAUD_THRESHOLD=0.99 \
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```
3. Capture outputs:
   ```bash
   curl -s http://localhost:8000/health | tee evidence_health.json
   curl -s "http://localhost:8000/dataset/samples?n=3&strategy=mixed&seed=42" | tee evidence_samples.json
   curl -s http://localhost:8000/features/random?mode=creditcard | python -c 'import sys,json;print(json.dumps({"features":json.load(sys.stdin)["features"]}))' > payload.json
   curl -s http://localhost:8000/predict -H 'Content-Type: application/json' -d @payload.json | tee evidence_predict.json
   curl -s http://localhost:8000/metrics | head -n 40 | tee evidence_metrics.txt
   ```

---

## 9) Frontend System (UI/UX) — Evidence

### 9.1 What the frontend is (real implementation)
The frontend is a static HTML/JS dashboard under `frontend/` that calls the backend API and renders a live stream:
- `frontend/index.html` (layout)
- `frontend/app.js` (stream loop + state + risk classification)
- `frontend/api-client.js` (strict response shape validation, timeouts)
- `frontend/ui.js` (DOM rendering + chart)
- `frontend/demo-data.js` (real sample loader + random generator)

### 9.2 Dashboard layout (evidence from `frontend/index.html`)
Main panels:
- **Header:** connection pill; model version; threshold; expected feature count
- **Control Panel:** API base URL; mode (Real vs Random); speed; Start/Stop/Reset
- **Live Summary KPIs:** total processed; fraud; suspicious; fraud rate; avg probability; last latency
- **Alert Panel:** recent suspicious/fraud items
- **Chart:** fraud probability over time with threshold overlay (canvas)
- **Live Transaction Feed:** append-only table (timestamp, request id, amount, probability, risk, label, threshold, latency, status, source)

### 9.3 Streaming modes (evidence)
From `frontend/app.js` + `frontend/demo-data.js`:

**Mode A — Real Sample Stream**
- Loads `frontend/real-samples.json` via `fetch('./real-samples.json')`
- Falls back to a small inline list if fetch fails
- Uses feature vectors in the same order as backend: `[Time, V1..V28, Amount]`

**Evidence (parsed from `frontend/real-samples.json`):**
- `n_features = 30`
- `n_samples = 240`
- `fraud_samples = 60` (samples with `class_label=1`)

**Mode B — Random Generated Stream**
- Generates plausible distributions (time cursor + Gaussian-like PCA components + log-normal-like amount)
- Intended for demo traffic variety (not for training)

### 9.4 Risk classification + alerting (actual logic)
From `frontend/app.js`:
- `LOW` if `risk_score < threshold_review`
- `REVIEW` if `threshold_review <= risk_score < threshold_high`
- `HIGH` if `risk_score >= threshold_high`
- Else `Suspicious`

Alerts are created for `Suspicious` and `Fraud` and shown in the Alert Panel.

### 9.5 Frontend UI screenshot (embedded)
Captured from the real `frontend/index.html` served locally (backend not running at capture time):

![Frontend Dashboard Screenshot (layout evidence)](artifacts/figures/frontend_dashboard.png)

**TODO (optional, for stronger submission evidence):** capture a second screenshot while the backend is running and the stream is active (shows live feed rows, alerts, and chart movement).

---

## 10) Monitoring & Alerts (Prometheus + Grafana)

### 10.1 Metrics emitted by the API (evidence)
From `src/monitoring/metrics.py` and used in `src/api/main.py`:

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `api_requests_total` | Counter | `endpoint, method, http_status` | request volume by endpoint/status |
| `api_request_latency_seconds` | Histogram | `endpoint, method` | latency distribution; enables p95 |
| `fraud_predictions_total` | Counter | `label` | number of predictions by label (0/1) |
| `fraud_scores_sum` / `fraud_scores_count` | Counter | — | score aggregation (avg score) |

### 10.2 Prometheus scrape configuration (evidence)
From `deployment/prometheus/prometheus.yml`:
- Scrape interval: 5s
- Target: `api:8000` at `/metrics`

### 10.3 Alert rules (evidence)
From `deployment/prometheus/alerts.yml`:
- `FraudApiHigh5xxErrorRate` (warning): 5xx rate > 5% for 10m
- `FraudApiHighP95Latency` (warning): p95 latency > 0.5s for 10m
- `FraudApiPredictionRateTooLow` (info): prediction rate < 0.01 req/s for 15m
- `FraudApiPredictionRateTooHigh` (warning): prediction rate > 50 req/s for 10m

### 10.4 Grafana dashboard (evidence)
From `deployment/grafana/dashboards/fraud_api.json`:
- Dashboard title: “Fraud Detection API Monitoring”
- Panels include:
  - API Requests Per Second
  - Request Latency (95th percentile)
  - Average Fraud Score
  - Fraud Predictions by Label

**Runtime verification:** **Unverified** for this report (Grafana/Prometheus were not launched here).

**TODO (how to capture Grafana screenshots):**
1. Generate artifacts (if needed):  
   `python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts --seed 42`
2. Start stack:  
   `docker compose -f deployment/docker-compose.yml up --build`
3. Open Grafana: `http://localhost:3000` (admin/admin by default)
4. Open the dashboard and screenshot the panels while running the frontend stream.

---

## 11) Deployment (Docker + Compose)

### 11.1 Compose services (evidence)
From `deployment/docker-compose.yml`:

| Service | Port | Purpose | Evidence |
|---|---:|---|---|
| `api` | 8000 | FastAPI serving | `deployment/api/Dockerfile`, `src/api/main.py` |
| `frontend` | 8080 | static dashboard | `deployment/frontend/Dockerfile`, `frontend/` |
| `mlflow` | 5000 | tracking UI/server | `deployment/mlflow/Dockerfile` |
| `prometheus` | 9090 | metrics scraping + alert eval | `deployment/prometheus/*` |
| `grafana` | 3000 | dashboards | `deployment/grafana/*` |

### 11.2 Model deployment contract (important)
Compose config sets:
- `MODEL_PATH: /app/artifacts/models/final_model.joblib`
- `FRAUD_THRESHOLD: "0.99"` (explicit override)
- `MODEL_VERSION: creditcard-production-v1`
- Volume mount: `../artifacts:/app/artifacts`

This makes the deployable model and threshold policy explicit at runtime.

### 11.3 Build artifacts required
The API container expects a model artifact present in the mounted `artifacts/` volume. The repo’s runbook is `QUICK_START.md`.

**Runtime verification:** **Unverified** in this report (Compose not executed here).

---

## 12) Testing & CI/CD

### 12.1 Test coverage in repo (evidence)
Tests exist in:
- Unit: `tests/unit/*` (e.g., preprocessing + request id generation)
- Integration: `tests/integration/*` (API endpoints via ASGI client)
- Data checks: `tests/data/*` (dataset loader behavior)
- Model checks: `tests/model/*` (synthetic training produces artifacts; probability sanity)

### 12.2 CI workflow (coverage gate)
From `.github/workflows/ci.yml`:
- Python 3.11 on Ubuntu
- Installs `requirements.txt` + `pytest-cov`
- Runs: `pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80`

### 12.3 Docker workflow
From `.github/workflows/docker.yml`:
- Builds API image and frontend image
- Validates docker-compose file with `docker compose ... config`

**Runtime verification:** **Unverified** in this report (GitHub Actions runs not queried here).

---

## 13) Responsible AI (RAI) — Evidence-Based

Primary RAI document: `RESPONSIBLE_AI.md`.

### 13.1 Explainability
- Implemented SHAP for LightGBM; artifacts exist (Section 6).
- Limitation documented: SHAP is not causal; interpretation must be careful.

### 13.2 Fairness limitations (strictly stated)
Dataset contains anonymized PCA components and **no protected attributes**. Therefore:
- demographic parity / equalized odds across protected groups cannot be computed
- only proxy slice checks (e.g., amount/time buckets) are possible

### 13.3 Privacy posture (as implemented + documented)
From `RESPONSIBLE_AI.md` and API schema:
- API accepts numeric feature vectors only (no PII fields).
- Recommended: do not log raw features in production; keep aggregated metrics.

### 13.4 Ethical risks + mitigations
- False positives: cause friction → mitigate with explicit threshold + “Suspicious” tier (human review)
- False negatives: missed fraud → mitigate by emphasizing recall and threshold trade-offs

---

## 14) Limitations (No assumptions)

### 14.1 Verified vs Unverified in this report
**Verified by artifacts and repository inspection**
- Kaggle dataset is present and processed (`data/archive/creditcard.csv` and `artifacts/reports/*`)
- End-to-end benchmark artifacts exist (metrics, curves, SHAP, model export)
- Deployable model metadata exists (`artifacts/models/model_info.json`)
- Frontend implementation exists and real sample pool is present (`frontend/real-samples.json`)

**Unverified (not executed/observed live while generating this report)**
- Running FastAPI server and capturing live endpoint responses (`/health`, `/predict`, `/metrics`)
- Running Docker Compose stack (Prometheus/Grafana/MLflow live dashboards)
- Running tests + checking CI results

### 14.1.1 System components status table (submission-ready)

| Component | Evidence (repo / artifacts) | Status in this report | How to verify (1–2 commands) |
|---|---|---|---|
| Dataset present | `data/archive/creditcard.csv`, `artifacts/reports/dataset_schema.json` | **Verified** | N/A (already in repo) |
| ML benchmark pipeline outputs | `src/pipelines/run_model_workflow.py`, `artifacts/reports/*`, `artifacts/figures/*` | **Verified** | Re-run workflow (see Appendix A) |
| Deployable model + metadata | `artifacts/models/final_model.joblib`, `artifacts/models/model_info.json` | **Verified** | After `pip install -r requirements.txt`: `python -c "import joblib; joblib.load('artifacts/models/final_model.joblib')"` |
| API implementation | `src/api/main.py`, `src/api/schemas.py`, `src/models/loader.py` | **Verified (code)** / **Unverified (runtime)** | Run `uvicorn ...` then `curl /health` |
| Frontend implementation | `frontend/index.html`, `frontend/app.js`, `frontend/api-client.js` | **Verified (code)** / **Partially Verified (static UI screenshot)** | Serve `frontend/` and open in browser |
| Prometheus/Grafana config | `deployment/prometheus/*`, `deployment/grafana/*` | **Verified (config)** / **Unverified (runtime)** | `docker compose up` then open Grafana |
| Docker images/Compose wiring | `deployment/*` | **Verified (config)** / **Unverified (runtime)** | `docker compose -f deployment/docker-compose.yml up --build` |
| Tests + coverage gate | `tests/*`, `.github/workflows/ci.yml` | **Verified (exists)** / **Unverified (executed)** | `pytest ... --cov-fail-under=80` |
| CI/Docker workflows | `.github/workflows/ci.yml`, `.github/workflows/docker.yml` | **Verified (exists)** / **Unverified (latest runs)** | Check Actions on GitHub |

### 14.2 Multiple artifact sets (must not be conflated)
This repo contains **two** artifact tracks:
1. **Kaggle benchmark track** under `artifacts/models/` with **30 features** (the one used for deployment and frontend streaming contract).
2. **Synthetic training track** under `artifacts/model.joblib`, `artifacts/model_info.json`, and `artifacts/metrics_report.json` with **20 features** (`data_source: synthetic:make_classification`).

The deployable, demo-aligned contract for the dashboard is the Kaggle track with **30 features**.

---

## 15) Conclusion (E2E Verdict)

### 15.1 End-to-end completeness (implementation)
This repository implements an end-to-end ML system at demo scope:
- Real dataset in repo
- Benchmark pipeline producing real artifacts, metrics, figures, and explainability
- Deployable model and explicit threshold policy recorded in metadata
- Serving API with clear contract + observability
- Frontend dashboard that streams transactions and calls the real `/predict`
- Monitoring/alerting configuration with Prometheus + Grafana
- Deployment configuration via Docker Compose
- Tests and CI workflows defined

### 15.2 Demo readiness (what to do next)
To produce fully “demo-ready” evidence (live screenshots and real response logs), run the stack per `QUICK_START.md` and capture:
- `curl` outputs for `/health`, `/predict`, `/metrics`
- frontend stream screenshot (alerts + feed + chart)
- Grafana dashboard screenshot while streaming

---

## Appendix A — Recommended “Evidence Capture” Checklist (for submission)

- [ ] Run `python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts --seed 42`
- [ ] Save `artifacts/models/model_info.json` and `artifacts/reports/model_selection_summary.json` in the submission package
- [ ] Screenshot: `artifacts/figures/model_comparison.png`, `baseline_pr_curve.png`, `improved_pr_curve.png`, `shap_summary.png`
- [ ] Launch API and save JSON outputs for `/health` and `/predict`
- [ ] Screenshot frontend while stream is running (alerts + chart)
- [ ] (Optional) Run Docker Compose and screenshot Grafana dashboard panels
