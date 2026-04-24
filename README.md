# Real-Time Banking Fraud Detection and Decision Support System

Repository: Final_Project_DMM501_Group1

Official team roster:

- Main author: AN Duong Binh
- Member: Tuyen Le Quang
- Member: NHI Nguyen Le Hong
- Instructor: Phd. NGU Huynh Cong Viet

This repository implements a complete fraud decision-support platform for banking transactions.

It combines machine learning, policy-based decisions, analyst workflow APIs, frontend operations, observability, and containerized MLOps deployment.

## Full Project Overview

Business objective:

- Detect suspicious transactions early.
- Prioritize limited analyst review capacity.
- Support consistent operational decisions with traceable evidence.

System objective:

- Convert transaction features into risk_score.
- Map score to risk_tier and decision_recommendation.
- Create and track alerts and cases.
- Expose monitoring metrics for engineering and operations.

Runtime flow:

Incoming Transaction -> Validation -> Feature Preparation -> Risk Scoring -> Decision Policy -> Reason Codes -> Alert and Case Creation -> Case Lifecycle Tracking -> Timeline Events -> Metrics and Dashboards

## Full Project Preview

### Core layers

- Data and feature layer: dataset ingestion, schema handling, feature validation.
- ML layer: baseline and improved model training, evaluation, threshold policy output.
- API layer: scoring, streaming, alert and case workflow endpoints.
- Frontend layer: analyst queue, case detail, decision support, timeline operations.
- Monitoring layer: Prometheus metrics, Grafana dashboards, alert rules.
- MLOps layer: MLflow tracking, Docker Compose orchestration, test and CI workflows.

### Repository preview

```text
src/
  api/            # FastAPI endpoints and schemas
  services/       # scoring, decision, reason code, case services
  repositories/   # in-memory and SQL persistence paths
  pipelines/      # model workflow and training pipelines
  monitoring/     # Prometheus metrics and MLflow runtime tracking
frontend/         # analyst dashboard UI and API client
deployment/       # docker compose, Dockerfiles, Prometheus, Grafana, MLflow
artifacts/        # models, figures, reports, benchmarks, deploy screenshots
tests/            # unit, data, model, integration, system checks
docs/             # architecture, specification, deployment, responsible AI
```

## Analyst Preview and Workflow

### Analyst dashboard (live)

![Analyst dashboard live](artifacts/figures/frontend_dashboard_live.png)

### Analyst dashboard (stream mode)

![Analyst dashboard stream mode](artifacts/figures/frontend_dashboard_streaming.png)

### Analyst operations sequence

1. Pull scored events or submit transaction for scoring.
2. Inspect risk_tier and decision_recommendation.
3. Review reason codes and transaction context.
4. Update case status through investigation lifecycle.
5. Resolve outcome as confirmed fraud or false positive.
6. Use timeline history for audit and reporting.

### Analyst-facing capability status

- Alert queue and case listing: implemented.
- Case detail with reason codes: implemented.
- Case status transition APIs: implemented.
- Case resolution and timeline endpoints: implemented.
- Frontend integration for queue and timeline: implemented.

## Architecture and API Preview

### API contract screenshot

![Swagger docs](artifacts/deploys/swagger-docs.png)

### Core endpoints

Scoring and system:

- POST /predict
- GET /health
- GET /metrics
- GET /stream/pull

Alert and case workflow:

- GET /alerts
- GET /alerts/{alert_id}
- POST /alerts/{alert_id}/status
- GET /cases
- GET /cases/{case_id}
- POST /cases/{case_id}/status
- POST /cases/{case_id}/resolve
- GET /cases/{case_id}/timeline

Utilities:

- GET /features/schema
- GET /features/random
- GET /dataset/samples
- GET /internal/dataset/samples

## Machine Learning and Decision Policy Preview

Key model design points:

- Handles highly imbalanced fraud data.
- Exports deployable model artifacts and metadata.
- Uses threshold policy for review and high-risk action tiers.
- Tracks experiments and runtime traffic metrics with MLflow.
- Current deployed artifact version in `artifacts/models/model_info.json`: `v0002_20260424T083412Z`

Score semantics:

- risk_score is treated as risk_score_uncalibrated.
- It is a ranking signal for decision support, not calibrated fraud probability.

Model evidence visuals:

![Final PR curve](artifacts/figures/final_pr_curve.png)

![Final ROC curve](artifacts/figures/final_roc_curve.png)

![Final confusion matrix](artifacts/figures/final_confusion_matrix.png)

## Monitoring and MLOps Preview

### Monitoring dashboards

![Grafana dashboard](artifacts/deploys/Grafana-dashboard.png)

![Prometheus targets](artifacts/deploys/Prometheus-targets.png)

### Deployment evidence

![Docker deployment terminal](artifacts/deploys/docker-terminal.png)

Monitoring and runtime tracking highlights:

- Prometheus metrics for requests, latency, tier distribution, case outcomes.
- Alert rules for reliability and traffic behavior.
- MLflow experiment for online traffic metrics:
  experiment name: fraud-runtime-traffic
  run name: api-online-traffic
  metrics: traffic_requests_total, traffic_stream_pull_calls_total, traffic_scored_events_total

## Implementation Status

Implemented:

- End-to-end scoring and decision APIs.
- Alert and case lifecycle with timeline.
- Frontend analyst workflow integration.
- Prometheus and Grafana stack.
- MLflow training and runtime traffic tracking.
- Docker Compose stack for local deployment.

Partially implemented:

- Full Grafana panel depth for all newly added operational metrics.

Demo-level behavior:

- In-memory repository mode for simplified local demo.
- SQL repository path is present and covered by integration tests.

## Quick Start

Fastest local path:

```bash
bash ./rune2e.sh
```

Manual local path:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
cd frontend
python -m http.server 8082 --bind 127.0.0.1
```

## Docker Deployment

```bash
docker compose -f deployment/docker-compose.yml up --build -d
```

Service URLs:

- API: <http://localhost:8000/docs>
- Frontend: <http://localhost:8082/index.html>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- MLflow: <http://localhost:5000>

Demo access tokens configured in the Docker Compose stack:

- Viewer: `viewer-token`
- Analyst: `analyst-token`
- Admin: `admin-token`

## Validation Snapshot

Latest targeted checks in this workspace:

- Full verification command:
  `./.venv/bin/pytest -q --cov=src --cov-config=.coveragerc --cov-report=term-missing`
- Latest result: `50 passed`
- Coverage result: `80%`
- Docker Compose config validates successfully.
- CI coverage gate: `--cov-fail-under=80`

## Documentation and Report Map

Primary docs:

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [MASTER_REPORT.md](MASTER_REPORT.md)
- [docs/QUICK_START.md](docs/QUICK_START.md)
- [docs/QUICK_ACCESS_GUIDE.md](docs/QUICK_ACCESS_GUIDE.md)
- [docs/COMPLETE_SYSTEM_SPECIFICATION_EXTRACTED.md](docs/COMPLETE_SYSTEM_SPECIFICATION_EXTRACTED.md)
- [docs/FULL_PROJECT_REVIEW.md](docs/FULL_PROJECT_REVIEW.md)
- [docs/SUBMISSION_FINAL_FILE_LIST.md](docs/SUBMISSION_FINAL_FILE_LIST.md)
- [latex/COMPLETE_FRAUD_DETECTION_REPORT.tex](latex/COMPLETE_FRAUD_DETECTION_REPORT.tex)
- [latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf](latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf)

## Notes for Evaluators

- Problem definition, requirements, success metrics, and architecture rationale are consolidated in the final LaTeX report so grading can be done against one coherent narrative.
- Runtime implementation evidence is visible directly in `src/`, `frontend/`, `deployment/`, `.github/workflows/`, and `artifacts/`.
- The current repository state is aligned to deployed artifact version `v0002_20260424T083412Z`, including thresholds and model-selection metadata.
- The strongest grading evidence for engineering quality is the current local verification result: `50 passed` with `80%` source coverage.
- For the live demo, the cleanest path is: open Swagger docs, score one transaction, inspect generated alert/case records, show analyst workflow in the frontend, then show Prometheus/Grafana/MLflow endpoints.

- This README is intended as a full-project preview for technical and non-technical reviewers.
- Claims are aligned with implemented code and test evidence.
- For reliable testing, avoid running local uvicorn and Docker API on the same host port at the same time.
- Git-author identities currently visible in history are documented in `CONTRIBUTING.md` for contribution review.
