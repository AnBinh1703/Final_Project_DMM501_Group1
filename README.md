# Real-Time Banking Fraud Detection and Decision Support System

Repository: Final_Project_DMM501_Group1

This project is an end-to-end ML-powered fraud decision-support platform for banking transactions.

It is not only a binary classifier demo.

The runtime workflow implemented in the API is:
Incoming Transaction -> Validation -> Feature Preparation -> Risk Scoring -> Decision Policy -> Reason Codes -> Alert/Case Creation -> Case Lifecycle Tracking -> Timeline Events -> Metrics

## Current Implementation Status

Implemented now:
- ML risk scoring API with strict feature validation
- Decision policy engine with LOW/REVIEW/HIGH tiers
- Decision recommendations (`ALLOW`, `STEP_UP_AUTH`, `MANUAL_REVIEW`, `HOLD`, `BLOCK`)
- Reason-code generation (demo-level heuristic + policy-based)
- Alert and case lifecycle APIs
- Investigation timeline per case
- Frontend queue/detail/timeline integration
- Prometheus metrics and alerts for operational workflow
- Docker Compose configuration for API, frontend, Prometheus, Grafana, MLflow
- Test suite with integration coverage for case workflow

Partially implemented:
- Frontend runtime manually verified in this session: not executed (code aligned, tests passing)
- Grafana dashboard panels for all newly added case metrics: partial

Demo-level simulated:
- Persistence layer for alerts/cases is in-memory (non-durable)

Future enhancement:
- Durable DB persistence
- Auth/RBAC and rate limiting
- Closed-loop retraining from case outcomes
- Drift detection and model governance automation

## Verified in This Session

- Full test suite passed: `30 passed`
- New integration workflow test passed for:
  - `/predict` -> flagged case
  - `/alerts` and `/alerts/{id}`
  - `/alerts/{id}/status`
  - `/cases/{id}/resolve`
  - `/cases/{id}/timeline`
- Docker Compose config validated with `docker compose config`

## Core API Endpoints

### Scoring and System Endpoints
- `POST /predict`
- `GET /health`
- `GET /metrics`
- `GET /stream/pull`

### Alert and Case Endpoints
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`

### Data Utility Endpoints
- `GET /features/schema`
- `GET /features/random`
- `GET /dataset/samples`
- `GET /internal/dataset/samples` (token-protected)

## Score Semantics

`risk_score` is explicitly treated as:
`risk_score_uncalibrated`

This is a ranking signal, not a calibrated fraud probability.

## Local Quick Start

### 1) Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Train/refresh artifacts (optional if artifacts already exist)
```bash
python -m src.pipelines.run_model_workflow \
  --data-path data/archive/creditcard.csv \
  --artifacts-root artifacts
```

### 3) Run API
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 4) Run frontend
```bash
cd frontend
python3 -m http.server 8082 --bind 127.0.0.1
```

### 5) Run tests
```bash
python -m pytest -q
```

## Docker Compose

```bash
docker compose -f deployment/docker-compose.yml up --build
```

Service ports:
- API: 8000
- Frontend: 8082
- Prometheus: 9090
- Grafana: 3000
- MLflow: 5000

## Documentation Map

Primary upgrade and audit report:
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`

Architecture and specification:
- `ARCHITECTURE.md`
- `SYSTEM_SPECIFICATION_DOCUMENT.md`
- `PROJECT_OVERVIEW.md`
- `RESPONSIBLE_AI.md`
- `DEPLOYMENT_REPORT.md`

## Important Notes for Evaluators

- Claims in docs are aligned to implementation and tests in this branch.
- If a capability is not runtime-verified in this environment, it is labeled explicitly.
- Case persistence is currently in-memory by design for demo and testability.
