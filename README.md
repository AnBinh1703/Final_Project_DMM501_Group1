# Real-Time Fraud Detection ML System

[![CI](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/ci.yml/badge.svg)](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/ci.yml)
[![Docker](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/docker.yml/badge.svg)](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/docker.yml)

End-to-end ML system for near-real-time fraud scoring on tabular financial transactions:

- ML pipeline: data ingestion, train/evaluate, threshold tuning, artifacts
- Experiment tracking: MLflow (local file backend in this repo)
- Serving: FastAPI `/predict` with Prometheus metrics
- Deployment: Docker + Docker Compose (API + frontend + MLflow + Prometheus + Grafana)
- Monitoring: Prometheus scrape + Grafana dashboard + alert rules
- Testing: unit + integration + data quality + model validation, with coverage gate

See `ARCHITECTURE.md` for system design and `CONTRIBUTING.md` for team workflow.
For a step-by-step run guide (Local + Docker), see `QUICK_START.md`.

## Problem Definition

### Business context
Card and payment fraud causes direct financial loss and operational cost. A fraud scoring service helps:

- reduce fraud loss by flagging risky transactions earlier
- reduce manual review cost by prioritizing suspicious transactions
- reduce customer friction by calibrating thresholds to control false positives

### Personas
- **Risk Operations Analyst**: needs an interpretable risk score plus threshold-based tiers (review vs high-risk auto action)
- **Backend/Platform Engineer**: needs a stable, observable API with clear deployment steps
- **Compliance/Audit**: needs explainability artifacts and documented limitations

### Primary use cases
1. Score a single transaction in milliseconds (API call) and return fraud probability + label.
2. Monitor service health/latency/error-rate and the fraud score distribution.
3. Re-train and version the model; deploy a new artifact with defined review/high thresholds.

## Requirements

### Functional requirements
| ID | Requirement | Priority |
|---|---|---|
| F1 | Provide `/predict` endpoint that returns `risk_score` plus tiered decision (`risk_tier`, `action`) | Must |
| F2 | Provide `/health` endpoint including `model_loaded` and `model_version` | Must |
| F3 | Provide `/metrics` Prometheus endpoint | Must |
| F4 | Provide training pipeline that produces a loadable model artifact + metadata | Must |
| F5 | Provide experiment tracking using MLflow | Should |
| F6 | Provide dashboards (Grafana) and alerting rules (Prometheus) | Must |
| F7 | Provide basic demo frontend calling the API | Could |

### Non-functional requirements
| ID | Requirement | Priority |
|---|---|---|
| N1 | p95 API latency <= 500ms for single request on a laptop-class environment | Should |
| N2 | Error rate < 1% under steady local demo load | Should |
| N3 | Containerized deployment with Compose and health checks | Must |
| N4 | CI runs tests and enforces coverage gate | Must |
| N5 | Responsible AI documentation (fairness, privacy, ethics, explainability) | Must |

## Success Metrics (Targets)

These are demo-grade targets aligned to imbalanced fraud detection.

### Business metrics
- **PR-AUC (proxy for review efficiency)**: target >= 0.75 on held-out test set (dataset-dependent)
- **Precision at operating threshold**: target >= 0.10 (controls false positives for review queue)

### System metrics
- **p95 latency** (`api_request_latency_seconds`): target <= 0.5 seconds
- **5xx error rate**: target < 5% (alert threshold; see Prometheus rules)

### Model metrics
- **PR-AUC** and **ROC-AUC** on test split
- **Recall** at tuned threshold (trade-off vs precision; threshold is a business decision)

## Repository Layout

- `src/api`: FastAPI app (`/predict`, `/health`, `/metrics`)
- `src/pipelines`: training workflow scripts
- `src/monitoring`: Prometheus metrics
- `deployment/`: Dockerfiles, Compose, Prometheus and Grafana configs
- `tests/`: unit + integration + data + model tests

## Quickstart (Local, No Docker)

### 1) Setup Python environment
```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pip install pytest-cov
```

### 2) Train a model and create artifacts

Option A (recommended for quick demo): synthetic dataset
```bash
python -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts
```

Option B: Kaggle Credit Card Fraud dataset (not stored in this repo)
- Place CSV at `data/raw/creditcard.csv` with target column `Class`
```bash
python -m src.pipelines.train_pipeline --data-path data/raw/creditcard.csv --artifacts-dir artifacts
```

Artifacts created:
- `artifacts/model.joblib` (loadable model)
- `artifacts/model_info.json` (threshold_review/high, version, n_features)
- `artifacts/metrics_report.json` (evaluation metrics)

### 3) Run the API with the model loaded
```bash
MODEL_PATH=artifacts/models/final_model.joblib \
MODEL_VERSION=final-model \
FRAUD_THRESHOLD=0.99 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 4) Use the API
Health:
```bash
curl -s http://localhost:8000/health | jq
```

Swagger UI:
- `http://localhost:8000/docs`

Export OpenAPI:
```bash
curl -s http://localhost:8000/openapi.json -o openapi.json
```

Predict:
```bash
curl -s http://localhost:8000/features/random?mode=creditcard | jq '{features:.features}' > payload.json
curl -s http://localhost:8000/predict -H 'Content-Type: application/json' -d @payload.json | jq
```

Error cases:
- `503` if model is not loaded (missing/invalid `MODEL_PATH`)
- `422` if feature vector length does not match training metadata

### 5) Run tests + coverage gate
```bash
pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80
```

## Docker (Single Services)

API image:
```bash
docker build -f deployment/api/Dockerfile -t fraud-api .
docker run --rm -p 8000:8000 \
  -e MODEL_PATH=/app/artifacts/models/final_model.joblib \
  -v "$PWD/artifacts:/app/artifacts" \
  fraud-api
```

Frontend image:
```bash
docker build -f deployment/frontend/Dockerfile -t fraud-frontend .
docker run --rm -p 8080:8080 fraud-frontend
```

## Docker Compose (Full Stack)

1) Generate artifacts locally (required so the API can load a model):
```bash
python -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts
```

2) Start stack:
```bash
docker compose -f deployment/docker-compose.yml up --build
```

Service URLs:
- API: `http://localhost:8000` (Swagger: `/docs`, Metrics: `/metrics`)
- Frontend: `http://localhost:8080`
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin/admin by default)

## Monitoring

Grafana dashboard is auto-provisioned:
- Dashboard: **Fraud Detection API Monitoring**
- Primary panels: RPS, p95 latency, average fraud score, label distribution

Alert rules are loaded by Prometheus from `deployment/prometheus/alerts.yml`:
- High 5xx error rate
- High p95 latency
- Prediction rate anomaly

## Responsible AI

See `RESPONSIBLE_AI.md` for:
- fairness and bias analysis (and limitations)
- explainability via SHAP artifacts
- privacy considerations and logging stance
- ethics risks and mitigations

## Demo Script (5–7 minutes)
1. Train model (synthetic) to produce `artifacts/` outputs.
2. Start Compose stack.
3. Show API `/health` and Swagger `/docs`.
4. Call `/predict` from Swagger or curl; show response includes `model_version` and thresholds (review/high).
5. Open Prometheus and Grafana; show live request rate and latency.
6. Show `artifacts/metrics_report.json` and Responsible AI doc.

## Notes
- The real Kaggle dataset CSV is excluded by `.gitignore` to keep the repo light; place it locally when running real-data experiments.
- For full benchmarking + SHAP artifact generation on real dataset, run:
  ```bash
  python -m src.pipelines.run_model_workflow --data-path data/raw/creditcard.csv --artifacts-root artifacts
  ```
