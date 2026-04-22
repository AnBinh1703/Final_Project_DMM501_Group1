# Full Project Review — Real-Time Banking Fraud Detection and Decision Support System

Evidence basis:
- Runtime code is treated as the source of truth.
- Generated artifacts are the next strongest evidence.
- Repository docs are used only when they match code and artifacts.
- If docs conflict with code, this report calls that out explicitly.

---

## Step 1 — Repository Structure

Files reviewed:
- `README.md`
- `ARCHITECTURE.md`
- `deployment/docker-compose.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/docker.yml`
- `src/`, `artifacts/`, `frontend/`, `deployment/`, `tests/`, `docs/`

What it does:
- The repository combines ML training, runtime scoring, case management, analyst UI, observability, and deployment in one codebase.
- `src/` holds the runtime backend and ML logic.
- `artifacts/` holds generated model files, benchmark outputs, plots, reports, and MLflow state.
- `frontend/` is a static browser UI that talks to the FastAPI backend.
- `deployment/` wires the app together with Docker, Prometheus, Grafana, and MLflow.

Key findings:

| Folder | Role | Layer | Notes |
|---|---|---|---|
| `src/` | Application and ML runtime code | Backend / ML | Contains API, preprocessing, model loading, repositories, streaming, monitoring, and security. |
| `artifacts/` | Generated outputs | ML / MLOps | Contains model snapshots, reports, plots, and MLflow DB/state; these are derived, not source. |
| `frontend/` | Analyst dashboard | Presentation | Static HTML/CSS/JS app; not a React/Vue app. |
| `deployment/` | Runtime packaging | Infra / MLOps | Dockerfiles, Compose, Prometheus, Grafana, and MLflow exporter. |
| `tests/` | Verification suite | QA | Unit, data, integration, API, SQL persistence, and frontend smoke coverage. |
| `docs/` | Reports and specs | Documentation | Includes PDFs and markdown reports; one referenced report file is missing. |
| `.github/workflows/` | CI automation | CI/CD | Separate workflows for test validation and Docker validation. |

Important parameters / values:
- The active compose stack exposes `api`, `frontend`, `postgres`, `mlflow`, `prometheus`, and `grafana`.
- CI runs unit tests, integration tests, and coverage gates at `80%`.
- The repo contains generated state in-tree: `__pycache__`, `.pytest_cache`, `latex/*.aux/.log/.toc`, and MLflow files.

Issues / risks:
- `README.md` and `ARCHITECTURE.md` reference `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`, but that file does not exist in `docs/`.
- `frontend/` has `package-lock.json` but no visible `package.json`; the UI is served as a static site.
- Generated artifacts are committed alongside source, which makes the tree noisier than a source-only repository.

Mini summary:
- The repo is structurally complete and production-shaped, but it mixes source, generated artifacts, and documentation.
- The clearest structural conflict is the missing referenced markdown report.

---

## Step 2 — Dataset and Features

Files reviewed:
- `src/data/dataset.py`
- `src/data/samples.py`
- `src/features/random_features.py`
- `artifacts/reports/dataset_schema.json`
- `artifacts/reports/eda_summary.json`
- `artifacts/reports/split_info.json`

What it does:
- The core dataset is the Kaggle-style credit card fraud dataset at `data/archive/creditcard.csv`.
- The dataset schema is 31 columns: `Time`, `V1`–`V28`, `Amount`, `Class`.
- `Class` is the binary target label.
- Feature sampling utilities can load real data, generate synthetic fraud-like rows, or produce mixed/production-style samples.

Key findings:

| Item | Value | Interpretation |
|---|---:|---|
| Dataset path | `data/archive/creditcard.csv` | The production benchmark dataset used by the main workflow. |
| Shape | `284807 x 31` | 30 features plus the `Class` target. |
| Fraud count | `492` | Extremely small positive class. |
| Non-fraud count | `284315` | Majority class dominates almost everything. |
| Fraud ratio | `0.001727485630620034` | About `0.17%` fraud base rate. |
| Duplicate rows | `1081` | Data quality issue to keep in mind. |
| Train/val/test split | `199364 / 42721 / 42722` | Stratified split with `random_seed=42`. |

Important parameters / values:
- `Time` is elapsed seconds since the first transaction in the dataset, not a Unix timestamp.
- `Amount` is transaction value and is strongly skewed.
- `V1`–`V28` are anonymized PCA-like components and are not directly interpretable.
- The dataset is hard because class imbalance is extreme and the features are largely non-semantic.

Why this dataset is difficult:
- A trivial `0.5` threshold would be poorly aligned with the base rate and the operational workload.
- Precision can collapse quickly if you chase recall without capacity constraints.
- ROC-AUC can look strong even when the positive class is rare; PR-AUC is more informative here.
- The feature space is anonymized, so explanation quality must be heuristic or model-based rather than business-semantic.

Issues / risks:
- The feature names are mostly anonymized, so feature-level explanation is limited.
- Because the fraud rate is tiny, metric variance is high; benchmark results should be read together, not in isolation.

Mini summary:
- The data is the standard hard case for fraud modeling: highly imbalanced, partially anonymized, and operationally threshold-sensitive.

---

## Step 3 — Preprocessing

Files reviewed:
- `src/features/preprocess.py`
- `src/services/scoring_service.py`
- `src/pipelines/train_pipeline.py`
- `src/pipelines/run_model_workflow.py`

What it does:
- The runtime preprocessing utility is intentionally minimal.
- At scoring time, the backend only converts the feature vector into a numeric NumPy row.
- Scaling happens in the logistic regression training pipelines, not in the utility preprocessing function.
- No one-hot encoding is used because the current feature set is fully numeric.

Key evidence:

```python
def preprocess_feature_vector(features: list[float]) -> np.ndarray:
    return np.asarray(features, dtype=float).reshape(1, -1)
```

```python
baseline_pipeline = Pipeline(
    [
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_seed)),
    ]
)
```

Important parameters / values:
- `StandardScaler` is used for logistic regression in both training paths.
- `LightGBM` in the benchmark workflow uses raw numeric features; its sidecar metadata explicitly records `identity` preprocessing.
- The backend scoring path expects a 30-feature ordered vector.

Why scaling matters here:
- Logistic regression is sensitive to feature scale and regularization.
- `Time` and `Amount` live on different scales from the anonymized components.
- Scaling stabilizes optimization and makes coefficients more comparable.

Issues / risks:
- The runtime preprocessing helper is a placeholder, not a real feature engineering pipeline.
- Because preprocessing is split between utility code and training code, the project has a mild “two preprocessing stories” problem.

Mini summary:
- Runtime preprocessing is identity-like; model training carries the real scaling behavior.
- This is acceptable for the current numeric feature set, but the split should be documented carefully.

---

## Step 4 — Model Pipeline

Files reviewed:
- `src/pipelines/train_pipeline.py`
- `src/pipelines/run_model_workflow.py`
- `src/models/loader.py`
- `src/models/versioning.py`
- `artifacts/models/model_info.json`
- `artifacts/reports/model_selection_summary.json`
- `deployment/docker-compose.yml`

What it does:
- There are two training entrypoints.
- `train_pipeline.py` is a simpler alternate path with baseline logistic regression, candidate random forest, and a LightGBM-or-RandomForest final model path.
- `run_model_workflow.py` is the main benchmark workflow for the current artifact set.
- The deployed canonical model is the logistic regression pipeline at `artifacts/models/final_model.joblib`.

Key findings:

| Model | Role | Status | Notes |
|---|---|---|---|
| Logistic regression pipeline | Baseline benchmark | Trained | Uses `StandardScaler + LogisticRegression(class_weight="balanced")`. |
| LightGBM | Improved candidate | Trained but not selected | Tuned on validation PR-AUC; did not beat baseline in the current artifact set. |
| Final logistic regression pipeline | Selected model | Deployed | This is the canonical model in `artifacts/models/final_model.joblib`. |
| RandomForest fallback | Code-path fallback | Partial | Exists in `train_pipeline.py` when LightGBM is unavailable, but it is not the selected deployed artifact here. |

Key evidence:

```python
if improved_val_pr_auc > baseline_val_pr_auc + 1e-6:
    selected_model = "lightgbm"
elif baseline_val_pr_auc > improved_val_pr_auc + 1e-6:
    selected_model = "logistic_regression"
else:
    selected_model = (
        "lightgbm"
        if improved_review_val["recall"] >= baseline_review_val["recall"]
        else "logistic_regression"
    )
```

```python
MODEL_PATH: /app/artifacts/models/final_model.joblib
MODEL_VERSION: creditcard-production-v1
```

Important parameters / values:
- Canonical artifact metadata says:
  - `model_type = logistic_regression_pipeline`
  - `selected_model = logistic_regression`
  - `n_features = 30`
  - `threshold_review = 0.7391262534904675`
  - `threshold_high = 0.9999047447184487`
  - `score_semantics = risk_score_uncalibrated`
- `run_model_workflow.py` stores the model under `artifacts/models/final_model.joblib` and versioned copies under `artifacts/models/versions/`.
- `src/models/loader.py` loads `artifacts/models/final_model.joblib` by default when `MODEL_PATH` is not explicitly set.

Issues / risks:
- The repo has overlapping training flows, so “final model” can be ambiguous if you only read code names.
- The main workflow says the improved LightGBM candidate exists, but the selected production artifact is logistic regression because validation PR-AUC was slightly better.

Mini summary:
- The actual deployed model is the logistic regression pipeline, not LightGBM.
- This is confirmed by artifact metadata and by the Docker deployment configuration.

![Final PR Curve](../artifacts/figures/final_pr_curve.png)
![Final ROC Curve](../artifacts/figures/final_roc_curve.png)
![Final Feature Importance](../artifacts/figures/final_feature_importance.png)

---

## Step 5 — Model Metrics and Thresholds

Files reviewed:
- `artifacts/models/model_info.json`
- `artifacts/reports/model_selection_summary.json`
- `artifacts/reports/latest_model_run.json`
- `artifacts/benchmarks/model_comparison.csv`
- `artifacts/benchmarks/threshold_comparison.csv`

What it does:
- The project evaluates models with PR-AUC, ROC-AUC, precision, recall, and F1.
- Thresholds are not fixed at `0.5`; they are selected from top-K capacity policies.
- The selected model uses two operating thresholds:
  - `threshold_review` for manual review
  - `threshold_high` for high-risk containment

Important parameters / values:

| Metric | Value | Interpretation |
|---|---:|---|
| `fraud_base_rate` | `0.001727485630620034` | Very low prevalence; thresholding must be capacity-aware. |
| Baseline validation PR-AUC | `0.6300872677700333` | Baseline logistic regression validation ranking quality. |
| Improved validation PR-AUC | `0.6289299179337815` | LightGBM did not beat the baseline in validation PR-AUC. |
| `threshold_review` | `0.7391262534904675` | Review queue threshold for the selected model. |
| `threshold_high` | `0.9999047447184487` | High-risk containment threshold for the selected model. |
| `threshold_f1` | `0.99` | Offline reference threshold, not the production policy. |
| `score_semantics` | `risk_score_uncalibrated` | Ranking score, not a calibrated probability. |

Selected-model test metrics:

| Operating point | Precision | Recall | F1 | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|
| `threshold_review` | `0.14617169373549885` | `0.8513513513513513` | `0.2495049504950495` | `0.9652288754708565` | `0.7694198862705721` |
| `threshold_high` | `0.8428571428571429` | `0.7972972972972973` | `0.8194444444444444` | `0.9652288754708565` | `0.7694198862705721` |
| `threshold_f1` | `0.7023809523809523` | `0.7972972972972973` | `0.7468354430379747` | `0.9652288754708565` | `0.7694198862705721` |

Key explanation:
- `0.5` is not the right default because the model is used as a ranking system under extreme class imbalance, not as a generic probability classifier.
- Top-K thresholding is used to match operational review capacity.
- `threshold_review` flags roughly the top `1%` of scores.
- `threshold_high` flags roughly the top `0.2%` of scores.
- The score is explicitly uncalibrated, so it should be treated as a relative risk ranking.

Issues / risks:
- Precision at the review threshold is low by design; that threshold is tuned for recall and triage, not clean auto-blocking.
- The score is uncalibrated, so it should not be communicated as “probability of fraud” without calibration work.

Mini summary:
- Thresholds are capacity-driven and intentionally not tied to `0.5`.
- The selected model has strong ROC-AUC and reasonable PR-AUC, but the operational value comes from the chosen thresholds.

![Final Confusion Matrix](../artifacts/figures/final_confusion_matrix.png)

---

## Step 6 — Decision Policy Engine

Files reviewed:
- `src/services/decision_service.py`
- `src/api/main.py`
- `src/api/schemas.py`

What it does:
- Converts model score into a risk tier and operational recommendation.
- Uses score thresholds plus amount and channel context.
- Maintains a backward-compatible `action` field and a richer `decision_recommendation` field.

Key evidence:

```python
if score >= threshold_high:
    recommendation = "BLOCK" if amount is not None and amount >= 1500.0 else "HOLD"
    return DecisionResult(
        risk_tier="HIGH",
        action="block",
        decision_recommendation=recommendation,
        decision_label="BLOCK",
        decision_explanation="High-risk transaction flagged for immediate containment.",
        fraud_label=1,
    )
```

Decision table:

| Score band | Risk tier | `action` | `decision_recommendation` | Notes |
|---|---|---|---|---|
| `score < threshold_review` | `LOW` | `allow` | `ALLOW` | No extra intervention. |
| `threshold_review <= score < threshold_high` | `REVIEW` | `review` | `STEP_UP_AUTH` or `MANUAL_REVIEW` | Digital channels get step-up auth; other channels go to manual review. |
| `score >= threshold_high` | `HIGH` | `block` | `BLOCK` or `HOLD` | Amount `>= 1500` pushes to `BLOCK`, otherwise `HOLD`. |

Important parameters / values:
- Digital channels are normalized and compared against:
  - `mobile_app`
  - `internet_banking`
  - `web`
  - `api`
  - `card_not_present`
- Amount affects only the `HIGH` tier recommendation split (`BLOCK` vs `HOLD`).

Issues / risks:
- The policy engine is business-aware but still heuristic; it is not a learned decision policy.
- Channel behavior is coarse-grained and hard-coded.

Mini summary:
- The model score does not directly drive a single action; it drives a policy tree with tiering, containment, and manual review logic.

---

## Step 7 — Reason Code Engine

Files reviewed:
- `src/services/reason_code_service.py`
- `src/api/main.py`
- `src/api/schemas.py`

What it does:
- Generates demo-level reason codes from model score, amount, time, channel, and optional metadata.
- Produces readable summaries for the frontend and case records.
- Mixes policy-based and heuristic signals.

Key evidence:

```python
if risk_tier == "HIGH" and score >= threshold_high:
    reasons.append("MODEL_HIGH_RISK_SCORE")
elif risk_tier == "REVIEW" and score >= threshold_review:
    reasons.append("MODEL_REVIEW_RISK_SCORE")
else:
    reasons.append("MODEL_LOW_RISK_SCORE")

if resolved_amount is not None and resolved_amount >= 1000.0:
    reasons.append("HIGH_AMOUNT_ANOMALY")
```

Heuristic rules used:
- Model score threshold code:
  - `MODEL_HIGH_RISK_SCORE`
  - `MODEL_REVIEW_RISK_SCORE`
  - `MODEL_LOW_RISK_SCORE`
- Amount anomaly: `amount >= 1000`
- Unusual time window: before `05:00` or after `23:00`
- High velocity: `high_velocity_txns` or `velocity_1h >= 5`
- `new_beneficiary`
- `device_mismatch`
- `geo_anomaly`
- `ato_pattern`
- Channel anomaly if channel is not in the known channel set

Why these are heuristic:
- They are rule-based signals, not learned explanations.
- They do not prove causality.
- They are useful for analyst triage and UI messaging, but not for rigorous root-cause attribution.

Issues / risks:
- The labels can look explanatory even though they are not causal.
- Because the rules are heuristic, they should be presented as analyst hints, not audit-grade explanations.

Mini summary:
- The reason-code engine is intentionally interpretable but not causal.
- This is acceptable for a decision support UI, but it should not be oversold.

---

## Step 8 — Backend API

Files reviewed:
- `src/api/main.py`
- `src/api/schemas.py`
- `src/models/loader.py`
- `src/security/auth.py`
- `src/security/rate_limit.py`
- `src/security/audit.py`

What it does:
- FastAPI app loads the model on startup, builds the stream simulator, and initializes the case service.
- `/predict` scores a transaction, maps it to a decision, generates reason codes, and creates alert/case records when needed.
- `/stream/pull` returns already-scored streaming events.
- `/alerts` and `/cases` support analyst workflow.
- `/metrics` exposes Prometheus metrics.

Key evidence:

```python
@app.post("/predict", response_model=PredictResponse)
async def predict(...):
    loaded = getattr(app.state, "loaded_model", None)
    features = _resolve_features(req, loaded)
    score = score_transaction(model=loaded.model, features=features)
    decision = decide_risk_action(...)
    reason_codes = generate_reason_codes(...)
    if case_service is not None:
        alert_record, case_record = case_service.create_from_prediction(...)
```

Endpoint table:

| Endpoint | Method | Purpose | Key Output | Notes |
|---|---|---|---|---|
| `/` | `GET` | Redirect to docs | Redirect response | Convenience entrypoint. |
| `/health` | `GET` | Runtime status | Model, thresholds, queue size | Used by frontend and tests. |
| `/features/schema` | `GET` | Feature contract | Feature names and count | Falls back to `Time,V1..V28,Amount`. |
| `/features/random` | `GET` | Synthetic feature generation | Feature vector | Modes: `auto`, `creditcard`, `normal`. |
| `/metrics` | `GET` | Prometheus exposition | Metrics text | Scraped by Prometheus. |
| `/predict` | `POST` | Score one transaction | Risk score, tier, decision, reasons, case IDs | Requires read-role auth when enabled. |
| `/stream/pull` | `GET` | Pull scored stream events | Scored events list | Returns no labels. |
| `/alerts` | `GET` | List alerts | Alert list | Read roles only. |
| `/alerts/{id}` | `GET` | Get alert | Alert detail | Read roles only. |
| `/alerts/{id}/status` | `POST` | Update linked case status | Updated case | Analyst/admin role required. |
| `/cases` | `GET` | List cases | Case list | Filterable by status. |
| `/cases/{id}` | `GET` | Get case | Case detail | Includes timeline when available. |
| `/cases/{id}/status` | `POST` | Update case status | Updated case | Analyst/admin role required. |
| `/cases/{id}/resolve` | `POST` | Resolve case | Updated case | Analyst/admin role required. |
| `/cases/{id}/timeline` | `GET` | Read case history | Timeline events | Read roles only. |
| `/audit/events` | `GET` | Read audit trail | Audit events | Admin-only. |
| `/dataset/samples` | `GET` | Sample raw dataset rows | Samples without labels | Read roles only. |
| `/internal/dataset/samples` | `GET` | Internal sample rows with labels | Samples with labels | Hidden endpoint; protected by internal token. |

Important parameters / values:
- Auth is role-based with `viewer`, `analyst`, and `admin`.
- The rate limiter is path-exempt for docs, health, and metrics.
- The API validates both positional features and `features_by_name`.
- The backend expects `30` features for the credit-card contract.

Issues / risks:
- Auth is static token-based, not identity-provider based.
- The internal dataset endpoint exposes labels if the internal token is known, so it must remain internal-only.

Mini summary:
- The API is the system’s core orchestration layer: score, decide, create case, expose workflow, and export metrics.

![Swagger Docs](../artifacts/deploys/swagger-docs.png)

---

## Step 9 — Alert and Case Workflow

Files reviewed:
- `src/services/case_service.py`
- `src/repositories/case_lifecycle.py`
- `src/repositories/in_memory_case_repository.py`
- `src/repositories/sql_case_repository.py`
- `src/api/main.py`

What it does:
- Alerts and cases are created only for `REVIEW` and `HIGH` predictions.
- The case record stores the full feature vector, score, threshold context, reason codes, and analyst notes.
- Timeline events are appended when cases are created and when status changes occur.

Key findings:
- `CaseService.create_from_prediction()` returns no alert/case for `LOW` transactions.
- Initial case status is `NEW`.
- Alert and case share a `case_id`/`alert_id` 1:1 relationship.
- Timeline events capture both system-generated and analyst-generated workflow transitions.

Status table:

| Status | Meaning | Next Possible States |
|---|---|---|
| `NEW` | Newly created case | `QUEUED`, `IN_REVIEW`, `ESCALATED`, resolution states |
| `QUEUED` | Waiting in review backlog | `IN_REVIEW`, `ESCALATED`, resolution states |
| `IN_REVIEW` | Analyst actively investigating | `ESCALATED`, `CONFIRMED_FRAUD`, `FALSE_POSITIVE`, `BLOCKED`, `RELEASED`, `RESOLVED` |
| `ESCALATED` | Higher-priority handling | Same resolution states |
| `CONFIRMED_FRAUD` | Fraud confirmed | Final / closed |
| `FALSE_POSITIVE` | Legitimate transaction | Final / closed |
| `BLOCKED` | Contained by policy | Final / closed |
| `RELEASED` | Cleared by analyst | Final / closed |
| `RESOLVED` | Generic closure state | Final / closed |

Important parameters / values:
- Active review queue statuses are `NEW`, `QUEUED`, `IN_REVIEW`, and `ESCALATED`.
- The timeline starts with:
  - `TRANSACTION_RECEIVED`
  - `RISK_SCORED`
  - `FLAGGED`
  - `ALERT_CREATED`
  - `CASE_ASSIGNED`

Issues / risks:
- The workflow is flexible, but not a fully enforced state machine.
- Transition semantics are stored in repository code rather than a dedicated workflow engine.

Mini summary:
- Alert/case creation is tightly coupled to risk tiering, and analyst actions are recorded as timeline events.

---

## Step 10 — Repository / Persistence Layer

Files reviewed:
- `src/repositories/factory.py`
- `src/repositories/in_memory_case_repository.py`
- `src/repositories/sql_case_repository.py`
- `src/repositories/migrations.py`
- `src/repositories/migrations/001_case_lifecycle.sql`

What it does:
- Supports two persistence modes:
  - in-memory demo mode
  - SQL-backed persistent mode
- SQL mode auto-applies schema migrations.
- Repository selection is driven by environment variables.

Key evidence:

```python
mode = str(os.getenv("CASE_REPOSITORY_MODE", "auto")).strip().lower()
db_url = str(os.getenv("CASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()

if mode in {"in_memory", "memory", "demo"}:
    return InMemoryCaseRepository()
```

Migration schema highlights:
- `alerts`
- `cases`
- `case_timeline`
- `audit_events`
- `schema_migrations`

Important parameters / values:
- `CASE_REPOSITORY_MODE=auto` falls back to in-memory if SQL initialization fails.
- `CASE_REPOSITORY_MODE=postgres` or `postgresql` requires a PostgreSQL DSN.
- `CASE_DB_AUTO_MIGRATE=true` runs migrations automatically.
- `persistence_mode` becomes `postgresql` or `sql_sqlite` in SQL-backed mode.

Demo mode vs persistent mode:
- Demo mode keeps everything in process memory and resets on restart.
- Persistent mode stores alerts/cases/timeline/audit rows in a real database and survives restarts.

Issues / risks:
- In-memory mode is excellent for demos and tests, but not durable.
- SQL repository is still fairly direct and application-managed; it is not a full workflow platform.

Mini summary:
- The repo cleanly separates demo and persistent storage, and the default deployment uses SQL persistence.

---

## Step 11 — Frontend System

Files reviewed:
- `frontend/index.html`
- `frontend/app.js`
- `frontend/api-client.js`
- `frontend/ui.js`
- `frontend/demo-data.js`
- `frontend/styles.css`

What it does:
- The frontend is a static browser app, not a mock-only placeholder.
- It has a dashboard view and a review view.
- It polls health, streams scored transactions, renders alerts, and lets analysts update cases.
- It can operate in real-stream mode or random local generation mode.

Key findings:
- The dashboard includes:
  - connection header
  - control panel
  - live summary
  - fraud alert queue
  - risk chart
  - live transaction feed
  - review queue
  - case detail panel
  - timeline panel
- `ApiClient` validates response shapes from `/health`, `/predict`, `/stream/pull`, `/alerts`, and `/cases`.
- The app uses `localStorage` for API URL, API token, and actor name.
- The frontend enforces the `30`-feature contract before starting a stream.

Key evidence:

```javascript
if (state.mode === 'real') {
  const batch = await api.pullStream({ paceMs: state.intervalMs, maxEvents: 75 });
  for (const ev of batch.events || []) {
    recordStreamEvent({ batch, event: ev, pullLatencyMs: batch._latencyMs });
  }
} else {
  const tx = DemoData.generateRandomTransaction();
  const result = await api.predictTransaction(tx.features);
  recordApiPrediction({ result, tx, timestamp });
}
```

Important parameters / values:
- Real mode uses backend-scored stream pulls.
- Random mode generates local transaction payloads and calls `/predict`.
- `demo-data.js` contains inline real samples extracted from `data/archive/creditcard.csv`.
- The frontend is intentionally lightweight: plain HTML/CSS/JS, no SPA framework.

Issues / risks:
- No `package.json` is visible, so the frontend is not packaged as a standard npm app.
- Some demo behavior is local, which is fine for UX but should not be confused with production streaming.

Mini summary:
- The frontend is real and connected, but intentionally minimal and static.

![Frontend Dashboard](../artifacts/figures/frontend_dashboard_live.png)

---

## Step 12 — Streaming / Simulation

Files reviewed:
- `src/streaming/simulator.py`
- `src/api/main.py`
- `frontend/demo-data.js`
- `frontend/app.js`

What it does:
- The backend stream endpoint returns pull-based scored events rather than a Kafka/Kinesis-style live feed.
- The simulator creates time-ordered events with burst traffic and rare attack windows.
- The simulator can draw from the real dataset or from synthetic credit-card-like feature generation.

Key findings:
- Base defaults:
  - `base_transactions_per_second = 1.2`
  - `burst_transactions_per_second = 14.0`
  - `base_fraud_rate = 0.0017`
  - `attack_fraud_rate = 0.01`
- Attack windows are intentionally rare.
- Ground-truth labels are not returned by the stream component.

Important parameters / values:
- The simulator is stateful and keeps internal time, burst, and attack counters.
- `pace_ms` controls how much simulated wall-clock time is produced per pull.
- `max_events` caps each pull call.

Issues / risks:
- This is simulated streaming, not a real message broker pipeline.
- The stream has operational realism, but not production ingestion guarantees.

Mini summary:
- Streaming is a realistic simulation layer that powers the dashboard and tests, not a real distributed stream processor.

---

## Step 13 — Monitoring and Observability

Files reviewed:
- `src/monitoring/metrics.py`
- `src/monitoring/mlflow_runtime_tracker.py`
- `deployment/prometheus/prometheus.yml`
- `deployment/prometheus/alerts.yml`
- `deployment/grafana/provisioning/datasources/datasource.yml`
- `deployment/grafana/provisioning/dashboards/dashboards.yml`
- `deployment/grafana/dashboards/fraud_api.json`
- `deployment/grafana/dashboards/mlflow.json`

What it does:
- Prometheus scrapes API and MLflow exporter metrics.
- Grafana is pre-provisioned with a Prometheus datasource and dashboards.
- The API exposes Prometheus counters, gauges, and histograms.
- Runtime MLflow logging is optional and controlled by environment variables.

Key metrics table:

| Metric | Meaning | Operational Value |
|---|---|---|
| `api_requests_total` | Requests by endpoint/method/status | Traffic and error-rate monitoring |
| `api_request_latency_seconds` | Request latency histogram | p95/p99 latency alerting |
| `fraud_predictions_total` | Scored transactions by tier | Fraud workload distribution |
| `fraud_actions_total` | Suggested actions by action type | Policy mix visibility |
| `fraud_alerts_total` | Alerts created for REVIEW/HIGH | Analyst workload tracking |
| `fraud_cases_total` | Cases created by status | Case creation volume |
| `fraud_case_status_total` | Case state transitions | Workflow health |
| `confirmed_fraud_total` | Confirmed fraud count | Outcome tracking |
| `false_positive_total` | False positives count | Precision/cost tracking |
| `review_queue_size` | Active review backlog | Queue pressure / staffing signal |
| `risk_scores_sum` / `risk_scores_count` | Average risk score support | Trend analysis |

Important parameters / values:
- Prometheus scrapes every `5s`.
- Alerting rules cover:
  - high 5xx rate
  - high p95 latency
  - prediction rate too low
  - prediction rate too high
  - review backlog high
  - false positive spike
- MLflow runtime metrics include traffic totals, average risk score, tier totals, decision totals, and HTTP family totals.

Key evidence:

```python
REQUESTS_TOTAL = Counter("api_requests_total", "Total number of requests", ["endpoint", "method", "http_status"])
LATENCY_SECONDS = Histogram("api_request_latency_seconds", "Request latency in seconds", ["endpoint", "method"])
REVIEW_QUEUE_SIZE = Gauge("review_queue_size", "Current number of active cases awaiting analyst decision")
```

Issues / risks:
- The observability stack is strong for a demo, but it still depends on local containers and environment variables.
- No evidence of alert routing to an external incident system is present.

Mini summary:
- Monitoring is one of the strongest parts of the repo: Prometheus, Grafana, and MLflow are all wired into the stack.

![Grafana Dashboard](../artifacts/deploys/Grafana-dashboard.png)
![Prometheus Alert Rules](../artifacts/deploys/Prometheus-rules.png)

---

## Step 14 — Deployment

Files reviewed:
- `deployment/docker-compose.yml`
- `deployment/api/Dockerfile`
- `deployment/frontend/Dockerfile`
- `deployment/mlflow/Dockerfile`
- `deployment/mlflow/exporter.py`
- `deployment/prometheus/prometheus.yml`

What it does:
- Docker Compose runs the full stack locally.
- The API container mounts `../artifacts` so it can load the model artifact and write or read derived outputs.
- The frontend is served as static files.
- MLflow runs as a server plus a Prometheus exporter process.

Service table:

| Service | Port | Role | Notes |
|---|---:|---|---|
| `postgres` | `5432` | Persistent case storage | Healthchecked with `pg_isready`. |
| `api` | `8000` | FastAPI backend | Loads `artifacts/models/final_model.joblib`. |
| `frontend` | `8080` in container, `8082` on host by default | Static dashboard | Served by `python -m http.server`. |
| `mlflow` | `5000` / exporter `5001` | Experiment tracking + metrics export | Uses SQLite backend in `/mlflow/mlflow.db`. |
| `prometheus` | `9090` | Metrics scraping and alerting | Scrapes API and MLflow exporter. |
| `grafana` | `3000` | Dashboarding | Pre-provisioned datasource and dashboards. |

Important parameters / values:
- API environment points directly to:
  - `MODEL_PATH=/app/artifacts/models/final_model.joblib`
  - `CASE_REPOSITORY_MODE=postgres`
  - `CASE_DB_URL=postgresql+psycopg://fraud:fraud@postgres:5432/fraud_ops`
  - `API_AUTH_ENABLED=true`
  - `RATE_LIMIT_ENABLED=true`
  - `MLFLOW_RUNTIME_ENABLED=true`
- Compose uses healthchecks for `postgres`, `api`, and `frontend`.
- Volume mounts preserve `postgres_data`, `mlflow_data`, and `grafana_data`.

Issues / risks:
- This is solid local deployment, but it is still single-host container orchestration.
- No Kubernetes manifests or cloud deployment pipeline are present in the reviewed tree.

Mini summary:
- Deployment is complete enough for a demo and local production-like testbed, but it is not a cloud-hardened deployment.

![Compose Stack](../artifacts/deploys/docker-compose.png)
![API Docs Screenshot](../artifacts/deploys/swagger-docs.png)

---

## Step 15 — Testing and CI/CD

Files reviewed:
- `tests/unit/*`
- `tests/data/*`
- `tests/integration/*`
- `tests/test_frontend_api.py`
- `tests/verify_system.py`
- `.github/workflows/ci.yml`
- `.github/workflows/docker.yml`

What it does:
- Unit tests check preprocessing, IDs, loader/scoring helpers, and reason-code logic.
- Data tests check dataset resolution, sampling strategies, and target validation.
- Integration tests validate health, prediction, alert/case workflows, security, SQL persistence, stream pulls, and docs.
- A frontend smoke script verifies that the browser layer can talk to the backend.
- CI enforces both functional tests and a coverage gate.

Verification matrix:

| Area | What is verified | Notes |
|---|---|---|
| Unit | Feature validation, loader behavior, reason codes, IDs | Fast and isolated. |
| Data | Dataset path resolution and sample extraction | Checks empty/missing/error paths. |
| Integration | `/health`, `/predict`, `/alerts`, `/cases`, `/stream/pull`, auth, SQL persistence | Uses the actual app lifespan. |
| Frontend smoke | API round-trip from browser-style client | Simple but useful for integration. |
| CI | Unit tests, integration tests, coverage, Docker compose config | Keeps the repo shippable. |

Important parameters / values:
- CI uses Python `3.11`.
- Coverage gate is `80%`.
- Docker workflow validates both API and frontend image builds plus compose configuration.

Issues / risks:
- CI does not appear to run a real browser automation suite.
- External services like Grafana and Prometheus are configured, but their runtime behavior is not deeply end-to-end tested in CI.

Mini summary:
- Test coverage is broad for an application repo, with good API and persistence coverage.
- The biggest gap is the absence of full browser and infrastructure integration testing.

---

## Step 16 — Security and Responsible AI

Files reviewed:
- `src/security/auth.py`
- `src/security/rate_limit.py`
- `src/security/audit.py`
- `src/api/main.py`
- `src/services/reason_code_service.py`
- `src/models/loader.py`

What it does:
- Auth is enabled by environment variable and uses static token-to-role mappings.
- RBAC restricts read, analyst, and admin paths.
- Audit events are appended for auth failures, forbidden actions, case updates, resolution, and rate-limit hits.
- The risk score is explicitly marked as uncalibrated.

Implemented:
- Static token auth via `API_TOKENS`
- Role-based access control
- Audit trail on key operations
- Sliding-window rate limiting
- Human review workflow and case resolution

Not fully hardened:
- No SSO/OIDC or identity-provider integration
- No secret rotation or token management workflow
- No distributed rate limiting
- No fairness/bias evaluation artifacts
- No calibration layer for the risk score
- No formal causal explanation engine

Key evidence:

```python
if not auth_enabled():
    ctx = AuthContext(token=None, role="admin", actor=actor)
    request.state.auth_context = ctx
    return ctx
```

```python
if not self._enabled or self._is_exempt_path(request.url.path):
    return await call_next(request)
```

Responsible AI notes:
- The reason-code system is heuristic, not causal.
- The score is a ranking signal, not a calibrated probability.
- Analysts remain in the loop for REVIEW/HIGH cases.

Issues / risks:
- Static tokens are acceptable for demo and internal deployment, but not enough for a regulated production environment.
- Because the score is uncalibrated, probability-style language would be misleading.

Mini summary:
- The repo has decent security hygiene for a demo stack, but it is not production-hardened in identity, policy, or fairness terms.

---

## Step 17 — Full System Summary

Files reviewed:
- `src/api/main.py`
- `src/pipelines/run_model_workflow.py`
- `artifacts/models/model_info.json`
- `deployment/docker-compose.yml`
- `frontend/app.js`
- `src/repositories/*`
- `src/monitoring/*`

What the project is:
- A real-time fraud detection and decision support system for banking transactions.
- It scores transactions, assigns risk tiers, creates alerts/cases, and exposes analyst workflows through a browser dashboard.
- It includes observability, experiment tracking, persistence, security controls, and a simulation layer.

End-to-end runtime flow:
1. API starts and loads `artifacts/models/final_model.joblib`.
2. The stream simulator is initialized from the dataset metadata.
3. `/predict` or `/stream/pull` scores transactions.
4. The decision engine maps scores into `LOW`, `REVIEW`, or `HIGH`.
5. REVIEW/HIGH creates alert/case records with reason codes and timeline events.
6. The frontend polls the backend, shows the alert queue, and lets analysts update or resolve cases.
7. Prometheus and MLflow record runtime traffic and model-ops metrics.

Actual deployed model:
- `logistic_regression_pipeline`
- Selected because validation PR-AUC beat the LightGBM candidate in the current artifact set.
- Confirmed by `artifacts/models/model_info.json`, `artifacts/reports/latest_model_run.json`, and `deployment/docker-compose.yml`.

Key thresholds and parameters:
- `fraud_base_rate = 0.001727485630620034`
- `threshold_review = 0.7391262534904675`
- `threshold_high = 0.9999047447184487`
- `threshold_f1 = 0.99`
- `review_top_rate = 0.01`
- `high_top_rate = 0.002`
- `score_semantics = risk_score_uncalibrated`

Main strengths:
- Clear end-to-end orchestration from scoring to analyst action
- Strong artifact trail with benchmark outputs and versioning
- Good integration of alerting, case management, and observability
- Practical threshold policy for an imbalanced fraud problem
- Useful static frontend with live operational controls

Main limitations:
- Two overlapping training pipelines create some conceptual ambiguity
- Score is uncalibrated, so probabilistic interpretation is limited
- Security is token-based rather than identity-provider based
- Streaming is simulated rather than broker-backed
- Frontend is static and lightweight, not a modern app framework

Top 10 technical takeaways:
1. The deployed canonical model is logistic regression, not LightGBM.
2. Thresholds are capacity-driven, not default `0.5`.
3. The score is a ranking signal, not a calibrated fraud probability.
4. `V1`–`V28` are anonymized PCA-like features.
5. The alert/case workflow is implemented end to end.
6. SQL persistence and in-memory demo mode are both supported.
7. The frontend is real and operationally connected to the backend.
8. Prometheus/Grafana and MLflow are integrated, not just planned.
9. Security exists, but it is basic and demo-oriented.
10. The repository is closer to a strong decision-support demo than a fully production-hardened fraud platform.

Recommended next improvements:
- Calibrate the risk score or clearly expose it as ranking-only in all user-facing surfaces.
- Unify the training entrypoints or deprecate the less relevant one.
- Replace static tokens with an identity-provider-backed auth model.
- Add fairness and calibration reporting to the artifact set.
- Add browser-level end-to-end tests for the frontend.
- Add a real distributed stream source if the system must behave like production ingestion.
- Reduce source-tree noise by moving generated artifacts out of version control or making their lifecycle explicit.

System Capability Matrix:

| Capability | Status | Evidence |
|---|---|---|
| Model scoring | Implemented | `/predict`, `score_transaction`, `final_model.joblib` |
| Threshold tiering | Implemented | `decision_service.py`, `model_info.json` |
| Alert creation | Implemented | `CaseService.create_from_prediction()` |
| Case lifecycle | Implemented | `case_lifecycle.py`, repository methods |
| SQL persistence | Implemented | `sql_case_repository.py`, migrations, tests |
| In-memory demo mode | Implemented | `in_memory_case_repository.py`, factory |
| Frontend dashboard | Implemented | `frontend/index.html`, `frontend/app.js` |
| Streaming simulation | Implemented | `streaming/simulator.py`, `/stream/pull` |
| Monitoring / Grafana | Implemented | `metrics.py`, Prometheus, Grafana dashboards |
| MLflow runtime tracking | Implemented | `mlflow_runtime_tracker.py`, exporter |
| Static-token auth | Implemented | `auth.py`, deployment env vars |
| Distributed auth/SSO | Missing | No OIDC/SSO integration in code |

Risk / Gap Matrix:

| Area | Problem | Impact | Suggested Fix |
|---|---|---|---|
| Docs | Referenced report file is missing | Documentation mismatch | Create or remove the dead reference. |
| Model interpretation | Score is uncalibrated | Risk of misuse as probability | Add calibration or label the score more aggressively. |
| Training story | Two training pipelines overlap | Confusion about the “real” final model | Consolidate into one authoritative workflow. |
| Auth | Static tokens only | Weak production identity control | Use OIDC/SSO and secret rotation. |
| Rate limiting | In-process limiter | Not horizontally scalable | Move to gateway or shared store. |
| Streaming | Simulated pull stream | Not real ingestion | Add a broker-backed stream for prod-like behavior. |
| Frontend | Static-only app shell | Limited modularity | Add a proper frontend build if needed. |
| Fairness | No bias reporting | Regulatory and ethical blind spot | Add subgroup metrics and fairness checks. |

Business Interpretation Matrix:

| Technical Component | Business Meaning |
|---|---|
| `risk_score` | Relative risk ranking for a transaction. |
| `LOW` | Transaction can pass without extra friction. |
| `REVIEW` | Analyst or step-up verification is needed. |
| `HIGH` | Immediate containment / blocking candidate. |
| `threshold_review` | Review capacity boundary. |
| `threshold_high` | Severe-risk containment boundary. |
| Alert | An item that needs analyst attention. |
| Case | A tracked fraud investigation record. |
| Timeline | Audit trail of how the case moved. |
| Prometheus/Grafana | Live operational health and workload visibility. |
| MLflow | Model-ops and runtime monitoring trail. |

Mini summary:
- This is a well-instrumented fraud decision-support system with a real backend, real monitoring, real persistence, and a real analyst UI.
- The main production-style caveats are calibration, identity, and streaming realism.
