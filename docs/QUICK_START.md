# Quick Start

This guide runs the upgraded fraud decision-support stack locally.

## 1) Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Train artifacts (optional)

If artifacts already exist in `artifacts/models/`, you can skip this step.

```bash
python -m src.pipelines.run_model_workflow \
  --data-path data/archive/creditcard.csv \
  --artifacts-root artifacts
```

## 3) Run API

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Quick check:
```bash
curl -s http://localhost:8000/health
```

## 4) Run Frontend

```bash
cd frontend
python3 -m http.server 8082 --bind 127.0.0.1
```

Open:
- http://127.0.0.1:8082/index.html

## 5) Verify Contracts

### Predict request
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "tx-demo-001",
    "timestamp": "2026-04-18T10:30:00+00:00",
    "amount": 1500.0,
    "channel": "internet_banking",
    "metadata": {"new_beneficiary": true, "velocity_1h": 6},
    "features": [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
  }'
```

### Case workflow checks
```bash
curl -s http://localhost:8000/alerts?limit=10
curl -s http://localhost:8000/cases?limit=10
```

## 6) Run Tests

```bash
python -m pytest -q
```

## 7) Docker Compose (full stack)

```bash
docker compose -f deployment/docker-compose.yml up --build
```

## 8) Important Notes

- `risk_score` is uncalibrated (`risk_score_uncalibrated`).
- Alert/case persistence is currently in-memory.
- Full audit and implementation matrix:
  - `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`
