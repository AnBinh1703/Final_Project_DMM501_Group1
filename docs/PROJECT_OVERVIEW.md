<!-- markdownlint-disable MD032 MD031 -->

# Project Overview (One-File Preview)

## Real-Time Banking Transaction Fraud Detection and Decision Support System

Repository: `Final_Project_DMM501_Group1`  
Program: `DDM501 Final Project`  
Updated: `2026-04-19`

## 1) What This Project Does

This system is an end-to-end fraud decision-support platform, not only a classifier endpoint.

Runtime handling flow:

Incoming Transaction -> Input Validation -> Feature Preparation -> ML Risk Scoring -> Decision Policy (LOW/REVIEW/HIGH) -> Recommendation + Reason Codes -> Alert/Case Creation (for REVIEW/HIGH) -> Case Lifecycle Updates -> Timeline Events -> Metrics -> Frontend Visualization

## 2) System Components

Core modules:
- API: `src/api/main.py`
- Schemas: `src/api/schemas.py`
- Scoring service: `src/services/scoring_service.py`
- Decision service: `src/services/decision_service.py`
- Reason code service: `src/services/reason_code_service.py`
- Case service: `src/services/case_service.py`
- Repository: `src/repositories/in_memory_case_repository.py`
- Monitoring metrics: `src/monitoring/metrics.py`
- Frontend: `frontend/index.html`, `frontend/app.js`, `frontend/ui.js`, `frontend/api-client.js`
- Training workflow: `src/pipelines/run_model_workflow.py`
- Deployment: `deployment/docker-compose.yml`

## 3) Model and Decision Framing

Current deployed metadata from `/health` and `artifacts/models/model_info.json`:
- `model_type`: `logistic_regression_pipeline`
- `model_version`: `final_model`
- `expected_features`: `30`
- `threshold_review`: `0.7391262534904803`
- `threshold_high`: `0.9999047447184487`
- `score_semantics`: `risk_score_uncalibrated`

Important interpretation:
- `risk_score` is a ranking signal and is not treated as a calibrated probability.

## 4) API Surface (Implemented)

Scoring and system:
- `POST /predict`
- `GET /health`
- `GET /metrics`
- `GET /stream/pull`

Case and alert operations:
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`

Data utility:
- `GET /features/schema`
- `GET /features/random`
- `GET /dataset/samples`
- `GET /internal/dataset/samples` (token-protected)

## 5) Frontend Behavior

Frontend supports:
- live queue and fraud feed
- case status transitions
- reason-code display
- timeline view per case
- streaming simulation modes

Frontend screenshots and artifacts:
- `artifacts/figures/frontend_dashboard_live.png`
- `artifacts/figures/frontend_dashboard_streaming.png`

## 6) Monitoring and Deployment

Monitoring stack:
- Prometheus: `deployment/prometheus/prometheus.yml`
- Alert rules: `deployment/prometheus/alerts.yml`
- Grafana dashboards: `deployment/grafana/dashboards/fraud_api.json`

Compose services:
- `api` (8000)
- `frontend` (8082)
- `postgres` (5432)
- `prometheus` (9090)
- `grafana` (3000)
- `mlflow` (5000)

## 7) Current Verification (Evidence in This Session)

Verified now:
- Unit + data tests passed: `14 passed`
- Integration tests passed: `17 passed`
- Docker Compose runtime healthy for all six services
- API health returned `status=ok` and `model_loaded=true`

Notes from runtime:
- Case repository mode currently reports `in_memory_demo`
- This is demo-level persistence and non-durable by design

## 8) Honest Status Classification

Fully implemented:
- scoring, decision policy, alerts/cases/timeline APIs, frontend integration, tests, compose deployment

Partially implemented:
- complete Grafana panel depth for all new operational metrics

Demo-level simulated:
- in-memory case persistence

Future enhancements:
- durable SQL persistence as default
- auth/RBAC/rate limiting hardening in all environments
- closed-loop retraining from confirmed outcomes
- drift detection and governance automation

## 9) Quick Run and Verify

Run local stack:
```bash
docker compose -f deployment/docker-compose.yml up --build -d
```

Check health:
```bash
curl -s http://127.0.0.1:8000/health
```

Run tests in selected venv:
```bash
python -m pytest -q tests/unit tests/data
python -m pytest -q tests/integration
```

Stop stack:
```bash
docker compose -f deployment/docker-compose.yml down --remove-orphans
```

## 10) Key Documents

- `README.md`
- `ARCHITECTURE.md`
- `docs/QUICK_START.md`
- `docs/RESPONSIBLE_AI.md`
- `docs/FINAL_REPORT_EVIDENCE_BASED.md`
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`

This file is intended to be the single high-level preview for reviewers, teammates, and presentation preparation.
