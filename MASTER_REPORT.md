<!-- markdownlint-disable MD025 MD032 MD012 -->

# 1. Executive Summary

This document is the single master record for the Real-Time Banking Transaction Fraud Detection and Decision Support System.

The implemented system is an end-to-end fraud operations platform rather than a standalone classification notebook. It combines model inference, threshold-based decision logic, analyst-facing alert and case workflows, audit and monitoring instrumentation, a browser dashboard, and containerized deployment assets.

The current implementation is aligned to the repository state on 2026-04-19:
- The deployed artifact is a logistic regression pipeline loaded from `artifacts/models/final_model.joblib`.
- The scoring contract expects 30 features: `Time`, `V1`-`V28`, and `Amount`.
- `risk_score` is explicitly treated as an uncalibrated ranking signal, not a calibrated fraud probability.
- `threshold_review` and `threshold_high` are capacity-driven thresholds stored in model metadata and used to derive `risk_tier` and `decision_recommendation`.
- Alerts and cases are created automatically for `REVIEW` and `HIGH` outcomes, with lifecycle transitions, timelines, and audit events.
- Prometheus metrics, Grafana dashboards, MLflow runtime logging, and Docker Compose assets are implemented.

Current validation status in this environment:
- Core unit and integration coverage is verified: 18 tests passed in a focused run across `tests/unit` and `tests/integration`, with one SQL persistence test blocked by the local Windows temporary-directory permission issue used by `pytest`.
- A broader full-suite run produced 19 passing tests, with the remaining errors caused by the same temp-directory permission problem rather than failing assertions.
- Docker Compose configuration and deployment artifacts are present in the repository, but the full stack was not re-executed during this consolidation pass.


# 2. Introduction

This project addresses fraud detection as an operational decision-support problem. The objective is not only to score transactions, but also to help analysts interpret risk, prioritize review workload, capture outcomes, and observe system behavior through runtime metrics and deployment tooling.

The repository includes:
- a reproducible ML workflow for data analysis, model training, threshold selection, and artifact export
- a FastAPI backend with explicit schemas and workflow endpoints
- a browser-based analyst dashboard implemented in vanilla HTML, CSS, and JavaScript
- monitoring integrations for Prometheus, Grafana, and MLflow
- Docker-based deployment assets
- automated tests and supporting verification scripts

The project is suitable for academic demonstration and technical review. Production use would require further hardening, especially around security controls, durable operations defaults, and governance automation.


# 3. Problem Definition

Banking fraud detection is a highly imbalanced classification problem with operational consequences:
- fraud events are rare
- false negatives create direct financial loss
- false positives create customer friction and analyst workload
- review capacity is limited, so not all suspicious activity can be investigated manually

For that reason, the system separates three concepts:
- `risk_score`: the model output used as a ranking signal
- `risk_tier`: the operational tier derived from policy thresholds
- `decision_recommendation`: the recommended business action derived from score, thresholds, amount, and channel context

This framing prevents the system from overstating model certainty and keeps human review in the loop where operationally necessary.


# 4. System Overview

The system accepts a banking transaction feature vector, validates the request, performs inference using the deployed model, maps the output into operational tiers, generates interpretable reason codes, and creates workflow records for analyst handling when necessary.

Core entities are standardized as follows:
- `risk_score`: model output in the range `[0, 1]`, explicitly labeled `risk_score_uncalibrated`
- `risk_tier`: `LOW`, `REVIEW`, or `HIGH`
- `decision_recommendation`: `ALLOW`, `STEP_UP_AUTH`, `MANUAL_REVIEW`, `HOLD`, or `BLOCK`
- `alert`: the operational signal created for a flagged transaction
- `case`: the investigation object linked to an alert and tracked through lifecycle states

At runtime, the main flow is:

Incoming transaction -> request validation -> feature resolution -> model scoring -> threshold-based policy mapping -> reason code generation -> alert/case creation for `REVIEW` or `HIGH` -> case timeline recording -> metrics and audit logging -> analyst dashboard consumption


# 5. System Architecture

The architecture is organized into five cooperating layers.

Scoring layer:
- model loading from artifact metadata in `src/models/loader.py`
- preprocessing and inference in `src/services/scoring_service.py`

Decision layer:
- policy mapping in `src/services/decision_service.py`
- heuristic explainability in `src/services/reason_code_service.py`

Workflow and persistence layer:
- alert and case orchestration in `src/services/case_service.py`
- repository abstraction in `src/repositories/`
- in-memory demo repository and SQL-backed PostgreSQL repository are both implemented

Presentation layer:
- FastAPI service in `src/api/main.py`
- analyst dashboard in `frontend/`

Operations and observability layer:
- Prometheus instrumentation in `src/monitoring/metrics.py`
- MLflow runtime tracking in `src/monitoring/mlflow_runtime_tracker.py`
- Grafana and Prometheus provisioning in `deployment/`

The backend starts by validating auth configuration, loading the model artifact, initializing the stream simulator if a model is available, and building the case repository from environment configuration. In `auto` mode the repository falls back to in-memory storage when no database URL is provided; in Docker Compose mode it is configured to use PostgreSQL.


# 6. Repository Structure

The repository is organized as follows:

```text
.
|-- src/
|   |-- api/
|   |-- data/
|   |-- features/
|   |-- models/
|   |-- monitoring/
|   |-- pipelines/
|   |-- repositories/
|   |-- security/
|   |-- services/
|   |-- streaming/
|   `-- utils/
|-- frontend/
|-- deployment/
|-- artifacts/
|-- data/
|-- tests/
|-- docs/
|-- latex/
|-- README.md
|-- ARCHITECTURE.md
`-- MASTER_REPORT.md
```

Key directories:
- `src/`: application code, training workflows, repositories, security, and monitoring
- `frontend/`: analyst dashboard and frontend API client
- `deployment/`: Docker Compose, Dockerfiles, Prometheus rules, Grafana dashboards, and MLflow container assets
- `artifacts/`: trained models, figures, benchmark tables, reports, MLflow data, and deployment evidence
- `tests/`: unit, data, model, integration, and smoke verification code
- `docs/`: prior reports, audits, quick-start material, and architecture/specification documents consolidated into this master record


# 7. Dataset and Data Analysis

The primary dataset is the Kaggle Credit Card Fraud Detection dataset stored at `data/archive/creditcard.csv`.

Artifact-backed dataset facts from `artifacts/reports/dataset_schema.json` and `artifacts/reports/eda_summary.json`:
- total rows: 284,807
- total columns: 31
- model features: 30
- target column: `Class`
- fraud cases: 492
- non-fraud cases: 284,315
- fraud prevalence: 0.001727485630620034
- duplicate rows detected during EDA: 1,081
- schema matches the expected credit-card format

The feature contract used by the deployed model is:
- `Time`
- `V1` through `V28`
- `Amount`

The data characteristics justify the system design choices:
- severe class imbalance makes plain accuracy misleading
- review operations require threshold-conditioned precision and recall, not only global ranking metrics
- threshold selection is tied to review capacity rather than a default 0.5 cutoff

Evidence artifacts include:
- `artifacts/reports/dataset_schema.json`
- `artifacts/reports/eda_summary.json`
- `artifacts/reports/class_distribution.json`
- `artifacts/reports/summary_statistics.csv`
- `artifacts/figures/class_distribution.png`
- `artifacts/figures/amount_distribution.png`
- `artifacts/figures/time_distribution.png`
- `artifacts/figures/fraud_vs_nonfraud_amount.png`
- `artifacts/figures/fraud_vs_nonfraud_time.png`


# 8. Machine Learning Pipeline

The primary training and model-selection workflow is implemented in `src/pipelines/run_model_workflow.py`.

The workflow performs:
- dataset loading and schema validation
- exploratory data analysis export
- train, validation, and test splitting
- baseline model training
- improved model training
- threshold sweeps and business-policy threshold selection
- figure and report generation
- artifact export for deployment
- model metadata export to `artifacts/models/model_info.json`
- version registration and MLflow logging

Recorded split information from `artifacts/reports/split_info.json`:
- train rows: 199,364
- validation rows: 42,721
- test rows: 42,722
- random seed: 42

Two model tracks are present in the workflow:
- baseline logistic regression pipeline with scaling
- improved LightGBM candidate with tuned parameters

Conflict resolved:
- some earlier documents emphasize LightGBM as the final model
- the actual deployed artifact metadata selects the logistic regression pipeline
- this master document therefore treats logistic regression as the production-aligned model and LightGBM as a benchmarked alternative, not the deployed default

Model metadata confirms:
- `selected_model`: `logistic_regression`
- `model_type`: `logistic_regression_pipeline`
- `dataset_path`: `data\\archive\\creditcard.csv`
- `score_semantics`: `risk_score_uncalibrated`
- threshold policy type: `top_k_rate`
- `review_top_rate`: `0.01`
- `high_top_rate`: `0.002`


# 9. Model Evaluation

Model evaluation emphasizes imbalanced-classification metrics and thresholded business behavior:
- ROC-AUC
- PR-AUC / Average Precision
- precision, recall, and F1 at selected thresholds
- confusion matrices
- threshold-sweep analysis
- feature-importance and SHAP outputs for benchmark inspection

Validation-only model selection summary from `artifacts/reports/model_selection_summary.json`:
- logistic regression validation PR-AUC: `0.6300872677700333`
- LightGBM validation PR-AUC: `0.6289299179337815`

Because the logistic regression pipeline achieved the slightly better validation PR-AUC, it was selected for deployment.

Test-set metrics for the deployed artifact from `artifacts/models/model_info.json`:

At `threshold_review = 0.7391262534904803`:
- precision: `0.14617169373549885`
- recall: `0.8513513513513513`
- F1: `0.2495049504950495`
- ROC-AUC: `0.9652288754708565`
- PR-AUC: `0.7694198862705721`

At `threshold_high = 0.9999047447184487`:
- precision: `0.8428571428571429`
- recall: `0.7972972972972973`
- F1: `0.8194444444444444`
- ROC-AUC: `0.9652288754708565`
- PR-AUC: `0.7694198862705721`

Interpretation:
- the `REVIEW` threshold is intentionally broader and recall-oriented to support analyst triage
- the `HIGH` threshold is intentionally narrow and high-precision for stronger intervention
- thresholds are chosen to match operational review capacity, not to maximize a single static metric

Evaluation artifacts include:
- `artifacts/figures/baseline_roc_curve.png`
- `artifacts/figures/baseline_pr_curve.png`
- `artifacts/figures/improved_roc_curve.png`
- `artifacts/figures/improved_pr_curve.png`
- `artifacts/figures/final_roc_curve.png`
- `artifacts/figures/final_pr_curve.png`
- `artifacts/figures/final_confusion_matrix.png`
- `artifacts/figures/model_comparison.png`
- `artifacts/figures/threshold_comparison.png`
- `artifacts/figures/shap_summary.png`
- `artifacts/benchmarks/model_comparison_table.csv`
- `artifacts/benchmarks/threshold_comparison_table.csv`


# 10. Decision Logic and Fraud Workflow

The decision engine is implemented in `src/services/decision_service.py`.

The policy is deterministic:
- if `risk_score >= threshold_high`, assign `risk_tier = HIGH`
- else if `risk_score >= threshold_review`, assign `risk_tier = REVIEW`
- else assign `risk_tier = LOW`

The action mapping is:
- `LOW` -> `decision_recommendation = ALLOW`
- `REVIEW` -> `decision_recommendation = STEP_UP_AUTH` for digital channels, otherwise `MANUAL_REVIEW`
- `HIGH` -> `decision_recommendation = BLOCK` when amount is at least 1500, otherwise `HOLD`

Backward-compatible action labels are also returned:
- `allow`
- `review`
- `block`

Reason-code generation is implemented in `src/services/reason_code_service.py`. It combines:
- policy-derived signals such as `MODEL_HIGH_RISK_SCORE` and `MODEL_REVIEW_RISK_SCORE`
- feature and metadata heuristics such as high amount, unusual time, velocity, new beneficiary, device mismatch, geographic anomaly, account-takeover pattern, and channel anomaly

These reason codes are useful for operator interpretation but remain heuristic and non-causal.

The fraud workflow is:
1. A scored request yields `risk_score`, `risk_tier`, and `decision_recommendation`.
2. If the tier is `REVIEW` or `HIGH`, the backend creates an `alert` and a linked `case`.
3. The case is initialized in status `NEW`.
4. Timeline events are appended for transaction receipt, scoring, flagging, alert creation, and case assignment.
5. Analysts can update case status, add notes, resolve outcomes, and inspect timelines.
6. Metrics and audit records are updated throughout the workflow.

Supported case statuses are:
- `NEW`
- `QUEUED`
- `IN_REVIEW`
- `ESCALATED`
- `CONFIRMED_FRAUD`
- `FALSE_POSITIVE`
- `BLOCKED`
- `RELEASED`
- `RESOLVED`


# 11. Backend System Design

The backend is implemented as a FastAPI application in `src/api/main.py` with typed request and response models in `src/api/schemas.py`.

Implemented endpoint groups:

Scoring and system:
- `GET /health`
- `GET /features/schema`
- `GET /features/random`
- `GET /metrics`
- `POST /predict`
- `GET /stream/pull`

Alert and case workflow:
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`
- `GET /audit/events`

Dataset utilities:
- `GET /dataset/samples`
- `GET /internal/dataset/samples`

The backend supports two feature input styles for `/predict`:
- `features`: ordered numeric vector
- `features_by_name`: numeric map aligned to model metadata

Validation behavior includes:
- rejection when both `features` and `features_by_name` are provided
- rejection of non-finite numeric values
- rejection of feature vectors that do not match the model's expected feature count
- validation of timestamp and amount fields

Security and operational middleware:
- optional token-based authentication with role mapping (`viewer`, `analyst`, `admin`)
- role-based endpoint access control
- optional rate limiting by token or client IP
- audit event capture integrated with case services

Persistence behavior:
- implemented demo-grade in-memory repository for local or fallback use
- implemented SQL repository with migrations and PostgreSQL support
- Docker Compose config uses PostgreSQL-backed case persistence

This means persistent case storage is implemented, but not the default in all local environments.


# 12. Frontend System Design

The frontend is implemented in plain HTML, CSS, and JavaScript rather than a heavy framework stack.

Primary files:
- `frontend/index.html`
- `frontend/app.js`
- `frontend/ui.js`
- `frontend/api-client.js`
- `frontend/demo-data.js`

Implemented frontend capabilities:
- backend connection and health polling
- streaming dashboard using `GET /stream/pull`
- support for real-time scored event visualization
- queue and case review view
- display of `risk_score`, `risk_tier`, `decision_recommendation`, and reason codes
- case timeline display
- case status transitions and resolution actions
- payload copy and re-score actions
- pagination and filtering for feed and case views

The frontend assumes:
- API base URL defaults to `http://localhost:8000`
- an analyst token can be supplied in the UI
- the dashboard expects a 30-feature backend contract

Implemented frontend mode distinctions:
- live API-backed scoring
- random or dataset-driven stream consumption
- analyst review workflow against the backend case APIs

This is an implemented analyst demo interface, not only a mock UI.


# 13. Monitoring and Observability

Monitoring is implemented across application metrics, alerting rules, dashboards, and runtime MLflow logging.

Application metrics in `src/monitoring/metrics.py` include:
- `api_requests_total`
- `api_request_latency_seconds`
- `fraud_predictions_total`
- `fraud_actions_total`
- `risk_tier_total`
- `decision_recommendations_total`
- `fraud_alerts_total`
- `fraud_cases_total`
- `fraud_case_status_total`
- `confirmed_fraud_total`
- `false_positive_total`
- `review_queue_size`
- `risk_scores_sum`
- `risk_scores_count`

Operational observability assets:
- Prometheus config: `deployment/prometheus/prometheus.yml`
- Prometheus alert rules: `deployment/prometheus/alerts.yml`
- Grafana dashboards: `deployment/grafana/dashboards/fraud_api.json` and `deployment/grafana/dashboards/mlflow_runtime.json`
- MLflow runtime exporter: `deployment/mlflow/exporter.py`

Monitoring scope:
- HTTP request counts and latency
- review queue growth
- alert and case creation
- case status transitions
- confirmed fraud and false positive outcomes
- runtime traffic logging into MLflow when enabled

Implementation status:
- instrumentation is implemented
- dashboard provisioning is implemented
- alert rules are implemented
- local evidence images exist under `artifacts/deploys`
- full end-to-end monitoring stack was not re-run during this consolidation session


# 14. Deployment Architecture

Deployment assets are centered around `deployment/docker-compose.yml`.

Defined services:
- `postgres`
- `api`
- `frontend`
- `mlflow`
- `prometheus`
- `grafana`

Container characteristics:
- the API container mounts `../artifacts` and uses the trained model artifact
- the API container enables PostgreSQL-backed case persistence, token auth, rate limiting, and MLflow runtime logging
- the frontend container serves the static dashboard on container port `8080`
- Prometheus scrapes the API metrics endpoint and loads local alert rules
- Grafana is provisioned with Prometheus as a datasource and dashboard JSON files

Default published ports in Compose:
- PostgreSQL: `5432`
- API: `8000`
- frontend: host `8082` to container `8080`
- MLflow: `5000`
- Prometheus: `9090`
- Grafana: `3000`

Deployment evidence available in the repository:
- `artifacts/deploys/docker-compose.png`
- `artifacts/deploys/docker-terminal.png`
- `artifacts/deploys/swagger-docs.png`
- `artifacts/deploys/Prometheus-targets.png`
- `artifacts/deploys/Prometheus-rules.png`
- `artifacts/deploys/Grafana-dashboard.png`

Implementation classification:
- local container stack definition: implemented
- service health checks: implemented for API, frontend, and PostgreSQL
- repository evidence of prior stack bring-up: available
- re-verification of live compose execution in this consolidation session: not performed


# 15. Testing and Validation

The repository contains automated tests across multiple layers:
- `tests/unit/`
- `tests/data/`
- `tests/model/`
- `tests/integration/`
- `tests/test_frontend_api.py`
- `tests/verify_system.py`

Current observed validation results in this environment:
- focused run of `tests/unit` and `tests/integration`: 18 passed, 1 blocked by a local `pytest` temporary-directory permission issue affecting the SQL persistence test setup
- broader full-suite run: 19 passed, 14 blocked by the same environment-level temp-directory permission issue

What this means:
- core API behavior, prediction flow, alert and case lifecycle flow, auth and audit flow, stream pull behavior, and utility logic are verified
- the blocked failures are environment-related setup errors, not evidence of broken assertions in the application code
- the SQL persistence path is implemented in code and targeted by tests, but full local test completion was blocked by temporary-directory access on this machine

Repository-level quality assets:
- `pytest.ini`
- `conftest.py`
- `.github/workflows/ci.yml`
- `.github/workflows/docker.yml`

Validation scope status:
- backend contract validation: implemented and partially verified
- workflow integration tests: implemented and verified
- SQL persistence integration test: implemented but not verified in this environment due temp-path permissions
- full end-to-end browser walkthrough: repository scripts and screenshots exist, but not re-executed during this consolidation session


# 16. Responsible AI

The system is explicitly positioned as fraud decision support, not autonomous irreversible fraud adjudication.

Responsible AI controls already implemented:
- explicit `score_semantics` returned in API responses
- separation of scoring from policy and workflow
- human-review path for `REVIEW` outcomes
- case lifecycle and timeline records for accountability
- heuristic reason codes to improve interpretability
- token protection for the labeled internal dataset sampling endpoint

Responsible AI constraints that remain important:
- `risk_score` is uncalibrated and must not be treated as a true probability
- reason codes are operational hints, not causal explanations
- the dataset does not contain explicit protected attributes, so direct demographic fairness claims cannot be made
- false positives and false negatives remain material business risks

Security and privacy status must be described accurately:
- basic authentication, RBAC, rate limiting, and audit-event collection are implemented and configurable
- enterprise-grade identity integration, secret management, encrypted transport enforcement, and tamper-resistant audit storage are not fully implemented in this repository

Recommended governance for production:
- approve thresholds through policy ownership
- review false positive and confirmed fraud outcomes regularly
- monitor slice-level outcome patterns by amount, time, and channel
- enforce stronger access controls and secure audit retention


# 17. Implementation Status

Fully implemented:
- artifact-backed model loading and inference
- `risk_score`, `risk_tier`, and `decision_recommendation` generation
- reason-code generation and summaries
- alert creation for flagged transactions
- case lifecycle APIs and timeline retrieval
- in-memory and SQL repository implementations
- token auth, RBAC, rate limiting, and audit-event capture
- streaming scored-event endpoint without exposing labels
- vanilla-JS analyst dashboard integrated with backend APIs
- Prometheus metrics and alert rules
- Grafana dashboard provisioning
- Docker Compose stack definition
- MLflow-based runtime traffic logging hooks

Partially implemented:
- complete verification of every deployment variant in the current environment
- exhaustive frontend coverage for all operational edge cases
- full production-grade security hardening and secrets management
- fairness monitoring beyond proxy slices such as amount, time, and channel

Demo-level:
- in-memory repository mode when running without a database URL
- heuristic reason-code generation
- local static-file frontend serving
- local deployment-oriented tokens and admin credentials in Compose examples

Future work:
- make durable SQL persistence the default across local and deployed modes
- add stronger identity and secret-management integration
- add model calibration or clearer percentile-centric presentation for operators
- add drift detection and automated governance triggers
- add closed-loop learning from `CONFIRMED_FRAUD` and `FALSE_POSITIVE` outcomes


# 18. Limitations

Current limitations are as follows:
- the deployed `risk_score` is a ranking signal and not a calibrated fraud probability
- threshold policy is capacity-oriented and may need recalibration if operational review volume changes
- fairness claims are limited by the absence of protected-attribute data in the source dataset
- reason codes are heuristic and should not be interpreted as causal explanations
- local default runtime may use non-durable in-memory case persistence unless SQL configuration is supplied
- Docker deployment assets are present, but full live-stack validation was not rerun during this documentation consolidation
- some tests remain blocked in this environment due Windows temporary-directory permissions rather than code assertions


# 19. Future Work

Priority next steps are:
- make PostgreSQL-backed persistence the default operational mode outside explicit demo scenarios
- add calibrated score options or percentile-first presentation for analyst decisions
- integrate stronger authentication, secret handling, and HTTPS-oriented deployment controls
- extend monitoring with drift, data-quality, and SLA-oriented alerts
- capture analyst case outcomes for feedback loops and retraining datasets
- expand dashboard analytics for queue aging, analyst productivity, and outcome tracking
- add reproducible deployment verification in CI for the full container stack


# 20. Conclusion

The repository contains a real fraud decision-support system with a trained deployed model, a structured backend API, analyst workflow endpoints, a browser dashboard, monitoring integrations, and deployment assets.

The correct implementation-aligned interpretation of the current project is:
- the deployed model is the logistic regression pipeline, not LightGBM
- persistent SQL-backed case storage is implemented, but not the fallback default in every environment
- authentication, RBAC, rate limiting, and audit capture exist in code and Compose configuration
- the system is suitable for demonstration and technical submission, but still requires production hardening and broader runtime verification for operational deployment

This document supersedes the repository's prior fragmented Markdown reports and should be treated as the project's single documentation source of truth.


## Documentation Cleanup Summary

Removed duplicates:
- repeated project overviews spread across `README.md`, `docs/PROJECT_OVERVIEW.md`, `ARCHITECTURE.md`, and prior final-report variants
- duplicated endpoint inventories across overview, specification, delivery, and audit documents
- repeated quick-start and deployment command sections
- repeated explanations of risk scoring, thresholding, monitoring, and dashboard behavior

Resolved conflicts:
- standardized terminology to `risk_score`, `risk_tier`, `decision_recommendation`, `alert`, and `case`
- resolved the model-selection conflict by aligning the document to `artifacts/models/model_info.json`, which selects logistic regression as the deployed artifact
- corrected persistence status from "in-memory only" or "SQL not implemented" to "both implemented, with environment-dependent default"
- corrected security status from "not implemented" to "implemented in configurable form, but not fully production-hardened"
- replaced unverified claims about current Docker runtime health with implementation-backed and artifact-backed wording
- replaced inaccurate blanket test-pass claims with the current environment-specific result, including the temp-directory permission limitation

Merged sections:
- introduction and problem framing
- architecture and module mapping
- dataset, EDA, training, and evaluation
- decision policy and fraud workflow
- backend, frontend, monitoring, and deployment
- testing, responsible AI, implementation status, limitations, and future work
