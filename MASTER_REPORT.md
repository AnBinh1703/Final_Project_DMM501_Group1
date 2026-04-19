<!-- markdownlint-disable MD025 MD032 MD012 -->

# 1. Executive Summary

This document is the single source of truth for the Real-Time Banking Transaction Fraud Detection and Decision Support System.

The system is implemented as an end-to-end decision-support platform, not a standalone classifier.

Runtime flow:
Incoming transaction -> validation -> feature preparation -> risk_score inference -> risk_tier assignment -> decision_recommendation -> reason code generation -> alert and case handling -> timeline tracking -> monitoring metrics and dashboards.

Current verified state as of 2026-04-19:
- Unit and data tests passed: 14 passed.
- Integration tests passed: 17 passed.
- Docker Compose stack running with healthy API and PostgreSQL.
- API health confirmed with model loaded and 30 expected features.


# 2. Introduction

This project implements a practical fraud decision-support lifecycle for banking transactions, with model inference integrated into operational workflows.

The system includes:
- ML pipeline and model artifacts.
- Backend API with strict contracts.
- Frontend analyst workflow.
- Monitoring and alerting.
- Containerized deployment.
- Test and CI quality gates.

The objective is to support safe and explainable fraud triage decisions using risk-aware policies.


# 3. Problem Definition

Fraud detection in banking is an imbalanced classification and decision-allocation problem.

Key challenges:
- Fraud events are rare compared to normal traffic.
- False negatives increase direct loss.
- False positives increase customer friction and analyst workload.
- Operational capacity requires triaging only a limited fraction of transactions.

Therefore, the project treats model output as decision-support input, not autonomous judgment.


# 4. System Overview

System purpose:
Provide near-real-time transaction risk assessment and workflow support for analysts.

Primary entities:
- risk_score: model output ranking signal.
- risk_tier: LOW, REVIEW, HIGH.
- decision_recommendation: ALLOW, STEP_UP_AUTH, MANUAL_REVIEW, HOLD, BLOCK.
- alert: event raised for review/high-risk cases.
- case: investigation object with lifecycle states and timeline.

Operational flow:
- LOW: pass through with monitoring.
- REVIEW: route to human or step-up workflow.
- HIGH: stronger controls such as hold or block.


# 5. System Architecture

Architectural layers:
- Scoring layer: model loading and inference.
- Decision layer: threshold and policy mapping.
- Case operations layer: alert and case lifecycle handling.
- Monitoring layer: metrics, targets, and alert rules.
- Presentation layer: analyst-facing frontend.

Core architecture files:
- ARCHITECTURE.md
- src/api/main.py
- src/services/scoring_service.py
- src/services/decision_service.py
- src/services/reason_code_service.py
- src/services/case_service.py
- src/repositories/in_memory_case_repository.py
- src/monitoring/metrics.py


# 6. Repository Structure

Top-level structure:
- src: backend API, services, repositories, pipelines, monitoring, utilities.
- frontend: dashboard UI and API client logic.
- artifacts: models, reports, figures, benchmarks, deployment evidence.
- deployment: docker compose, Dockerfiles, Prometheus, Grafana, MLflow configs.
- tests: unit, data, model, integration, and local verification scripts.
- docs: technical reports, audits, quick guides, and specification documents.
- latex: submission-ready report variants.

Canonical implementation references:
- README.md
- ARCHITECTURE.md
- docs/SYSTEM_SPECIFICATION_DOCUMENT.md
- docs/RESPONSIBLE_AI.md
- docs/QUICK_START.md


# 7. Dataset and Data Analysis

Primary dataset:
- Kaggle Credit Card Fraud dataset at data/archive/creditcard.csv.

Observed characteristics:
- 284,807 rows.
- 30 model features plus target column.
- Fraud prevalence approximately 0.17 percent.

Implications:
- Accuracy alone is misleading.
- PR-AUC and threshold-conditioned precision/recall are required.
- Capacity-aware policy thresholds are necessary for realistic operations.

Data and EDA artifacts:
- artifacts/reports/dataset_schema.json
- artifacts/reports/class_distribution.json
- artifacts/reports/eda_summary.json
- artifacts/figures/class_distribution.png
- artifacts/figures/amount_distribution.png
- artifacts/figures/time_distribution.png
- artifacts/figures/fraud_vs_nonfraud_amount.png
- artifacts/figures/fraud_vs_nonfraud_time.png


# 8. Machine Learning Pipeline

Main workflow implementation:
- src/pipelines/run_model_workflow.py

Pipeline stages:
- Ingestion and schema checks.
- Train, validation, and test split.
- Baseline and improved model training.
- Validation-based model selection.
- Threshold tuning and policy metadata generation.
- Artifact export for deployment.
- Metrics, plots, and benchmark report generation.

Secondary workflow:
- src/pipelines/train_pipeline.py

Model versioning and run tracking:
- Implemented for both workflows using src/models/versioning.py.
- Each training run creates a unique model version and run ID.
- Per-run metadata and run history logs are persisted.


# 9. Model Evaluation

Evaluation scope includes:
- ROC-AUC.
- PR-AUC (Average Precision emphasis for imbalance).
- Precision, recall, and F1 at selected thresholds.
- Confusion matrix and threshold sweep diagnostics.

Artifacts:
- artifacts/figures/baseline_roc_curve.png
- artifacts/figures/baseline_pr_curve.png
- artifacts/figures/improved_roc_curve.png
- artifacts/figures/improved_pr_curve.png
- artifacts/figures/final_roc_curve.png
- artifacts/figures/final_pr_curve.png
- artifacts/figures/final_confusion_matrix.png
- artifacts/figures/model_comparison.png
- artifacts/figures/threshold_comparison.png
- artifacts/benchmarks/model_comparison_table.csv
- artifacts/benchmarks/threshold_comparison_table.csv

Current deployment metadata confirms:
- model_type: logistic_regression_pipeline
- expected_features: 30
- threshold_review and threshold_high are policy-driven.


# 10. Decision Logic and Fraud Workflow

Core decision outputs:
- risk_score.
- risk_tier.
- decision_recommendation.

Policy behavior:
- risk_tier LOW for low-ranked transactions.
- risk_tier REVIEW for review-capacity zone.
- risk_tier HIGH for top-risk zone.

Case workflow:
- Alert generated for REVIEW and HIGH outcomes.
- Case created and tracked through status transitions.
- Timeline records key events for auditability.

Important semantic rule:
- risk_score is uncalibrated ranking output and not claimed as calibrated fraud probability.


# 11. Backend System Design

Primary API module:
- src/api/main.py

Schema and contracts:
- src/api/schemas.py

Key endpoint groups:
- Scoring and system: /predict, /health, /metrics, /stream/pull.
- Alert handling: /alerts, /alerts/{alert_id}, /alerts/{alert_id}/status.
- Case handling: /cases, /cases/{case_id}, /cases/{case_id}/status, /cases/{case_id}/resolve, /cases/{case_id}/timeline.
- Data utilities: /features/schema, /features/random, /dataset/samples, /internal/dataset/samples.

Repository mode:
- Current default runtime reports case_repository_mode as in_memory_demo.
- SQL persistence path exists and is validated in integration tests.


# 12. Frontend System Design

Frontend implementation:
- frontend/index.html
- frontend/app.js
- frontend/ui.js
- frontend/api-client.js
- frontend/demo-data.js

Implemented behavior:
- Stream and single-transaction interactions.
- Queue and case-oriented views.
- Reason code and decision display.
- Timeline visualization and status actions.

Evidence screenshots:
- artifacts/figures/frontend_dashboard_live.png
- artifacts/figures/frontend_dashboard_streaming.png


# 13. Monitoring and Observability

Monitoring stack:
- Prometheus scrape and rule configuration.
- Grafana dashboard provisioning.
- API metrics endpoint instrumentation.

Primary files:
- deployment/prometheus/prometheus.yml
- deployment/prometheus/alerts.yml
- deployment/grafana/dashboards/fraud_api.json
- src/monitoring/metrics.py

Representative metrics:
- api_requests_total
- api_request_latency_seconds
- fraud_predictions_total
- risk_tier_total
- decision_recommendations_total
- fraud_alerts_total
- fraud_cases_total
- fraud_case_status_total
- review_queue_size
- confirmed_fraud_total
- false_positive_total

Monitoring evidence:
- artifacts/deploys/Grafana-dashboard.png
- artifacts/deploys/Prometheus-targets.png
- artifacts/deploys/Prometheus-rules.png


# 14. Deployment Architecture

Container orchestration:
- deployment/docker-compose.yml

Services:
- API
- Frontend
- PostgreSQL
- Prometheus
- Grafana
- MLflow

Current runtime verification:
- Compose stack started successfully.
- API endpoint returned healthy status with loaded model.
- Container statuses show active services and healthy checks where defined.

Operational evidence:
- artifacts/deploys/docker-compose.png
- artifacts/deploys/docker-terminal.png
- artifacts/deploys/swagger-docs.png


# 15. Testing and Validation

Test suites:
- tests/unit
- tests/data
- tests/model
- tests/integration
- tests/test_frontend_api.py
- tests/verify_system.py

Latest verified results in this environment:
- Unit plus data tests: 14 passed.
- Integration tests: 17 passed.

CI and quality gates:
- .github/workflows/ci.yml
- .github/workflows/docker.yml
- Coverage gate configured with minimum threshold.


# 16. Responsible AI

Responsible AI scope includes:
- Transparency of score semantics.
- Human-in-the-loop handling through alert and case workflow.
- Explainability artifacts and reason code support.
- Privacy and ethical risk discussion.

Current stance:
- score_semantics explicitly documented as uncalibrated.
- Reason codes are decision-support aids and not causal proof.
- Full fairness validation is constrained by dataset attribute limitations.

Primary document:
- docs/RESPONSIBLE_AI.md


# 17. Implementation Status

Implemented:
- End-to-end scoring and decision API.
- risk_tier and decision_recommendation logic.
- Alert and case lifecycle endpoints.
- Timeline endpoint and frontend integration.
- Monitoring instrumentation and deployment configs.
- Automated testing across core layers.
- Model version and run tracking logs for each training run.

Partially implemented:
- Full dashboard coverage for every newly added operational metric.
- Runtime verification depth for every environment variant.

Demo-level:
- In-memory case persistence default mode.
- Heuristic reason-code logic for portions of explanation layer.

Future work:
- Durable persistence as default mode.
- Stronger auth and RBAC hardening.
- Drift monitoring and retraining orchestration.


# 18. Limitations

Current limitations:
- Default case persistence mode is non-durable unless SQL mode is explicitly used.
- risk_score is a ranking signal and not calibrated probability.
- Some operational behaviors are tuned for demo and educational scope.
- Cross-environment consistency still depends on local dependency and artifact compatibility.

Known practical constraints:
- Model artifact compatibility can vary across library versions.
- Local setup differences may require artifact regeneration.


# 19. Future Work

Priority roadmap:
- Make SQL-backed persistence the default operational mode.
- Add robust auth, RBAC, and audit policy enforcement.
- Add drift detection and model health governance loops.
- Build closed-loop retraining from confirmed case outcomes.
- Expand frontend and monitoring to full analyst operations depth.
- Add stronger production runbooks and SLO-oriented alerting.


# 20. Conclusion

The project currently delivers a complete fraud decision-support system across ML, API, frontend, monitoring, deployment, and testing domains.

It is implementation-aligned, evidence-backed, and suitable for academic submission and live demonstration.

The remaining work is primarily production hardening, persistence defaulting, and governance automation rather than core feature completion.


## Documentation Cleanup Summary

Removed duplicates by consolidation:
- Repeated runtime workflow explanations across README, PROJECT_OVERVIEW, and multiple docs reports.
- Repeated endpoint lists in architecture, overview, and execution reports.
- Repeated deployment and quick-start command blocks.
- Repeated model-metric narratives spread across audit and final reports.

Resolved conflicts:
- Standardized terminology to risk_score, risk_tier, decision_recommendation, alert, case.
- Resolved runtime status by using latest verified evidence from current session.
- Clarified persistence as in-memory demo default with SQL capability present.
- Standardized score semantics as uncalibrated ranking signal.

Merged sections:
- Introduction and project framing.
- Architecture and module mapping.
- Dataset and ML workflow details.
- Evaluation and decision policy narrative.
- Backend, frontend, monitoring, and deployment details.
- Testing, Responsible AI, status classification, limitations, and roadmap.
