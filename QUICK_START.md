# Quick Start (Local + Docker)

This guide runs the full Fraud Detection system in two ways:
- Local (Python venv, train pipeline, run API, run frontend, run tests)
- Local Docker Compose (API + Frontend + MLflow + Prometheus + Grafana)

Dataset (included in this repo):
- `data/archive/creditcard.csv`

Notes:
- Docker Compose mounts `./artifacts` from your host. Generate artifacts before running `docker compose up`.

## 0) Prerequisites
- Python 3.11+
- Docker + Docker Compose (only needed for the full stack)

## 1) Run Local (no Docker)

### 1.1 Create venv + install dependencies

Linux/macOS:
```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pip install pytest-cov
export MPLCONFIGDIR=/tmp/matplotlib
```

Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
pip install pytest-cov
$env:MPLCONFIGDIR="C:\Temp\matplotlib"
```

### 1.2 Generate artifacts from the real dataset (recommended)

This is the full workflow: data validation + EDA + baseline + improved models + threshold tuning + model selection + SHAP.

```bash
python -m src.pipelines.run_model_workflow \
  --data-path data/archive/creditcard.csv \
  --artifacts-root artifacts \
  --seed 42
```

Key outputs:
- Data validation:
  - `artifacts/reports/dataset_schema.json`
  - `artifacts/reports/missing_values.csv`
  - `artifacts/reports/class_distribution.json`
- EDA figures: `artifacts/figures/*.png`
- Model figures (useful for reports/presentations):
  - `artifacts/figures/baseline_threshold_sweep.png`
  - `artifacts/figures/improved_threshold_sweep.png`
  - `artifacts/figures/threshold_comparison.png`
  - `artifacts/figures/model_comparison.png`
  - `artifacts/figures/feature_importance.png`
  - `artifacts/figures/shap_summary.png`
- Model selection:
  - `artifacts/benchmarks/model_comparison.csv`
  - `artifacts/reports/model_selection_summary.json`
- Deployable model:
  - `artifacts/models/final_model.joblib`
  - `artifacts/models/model_info.json` (threshold + feature columns)

### 1.3 (Optional) Generate artifacts quickly (synthetic dataset)

For a fast demo you can train on synthetic data:
```bash
python -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts --fast
```
Outputs:
- `artifacts/model.joblib`
- `artifacts/model_info.json`
- `artifacts/metrics_report.json`

### 1.4 Run the Backend API (FastAPI)

Option A (real dataset model, explicit):
```bash
MODEL_PATH=artifacts/models/final_model.joblib \
MODEL_VERSION=creditcard-production-v1 \
FRAUD_THRESHOLD=0.99 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Option B (synthetic model, explicit):
```bash
MODEL_PATH=artifacts/model.joblib \
MODEL_VERSION=local-demo \
FRAUD_THRESHOLD=0.14 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Option C (real dataset model, zero-config):
- If you already generated `artifacts/models/final_model.joblib`, the API will auto-load it when `MODEL_PATH` is not set.
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Endpoints:
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Metrics: `http://localhost:8000/metrics`
- Random features: `http://localhost:8000/features/random`

### 1.5 Run the Frontend (demo UI)

The frontend is a real-time fraud monitoring dashboard that calls the backend (no fake predictions).

Recommended (pick a free port automatically):
```bash
cd frontend
python3 -m http.server 0 --bind 127.0.0.1
```

The server will print the chosen port, e.g.:
- `Serving HTTP on 127.0.0.1 port 46321 ...`

Open the UI:
- `http://127.0.0.1:<PORT>/index.html`

If you prefer a fixed port (only if free):
```bash
python3 -m http.server 8082 --bind 127.0.0.1
```
Open `http://127.0.0.1:8082/index.html`.

Using the UI:
1. Confirm the top-left connection pill turns green (backend reachable + `model_loaded=true`).
2. Ensure `/health` reports `expected_features=30` (required by the trained CreditCard model contract).
3. Click **Start Stream** (Real Sample Stream or Random Generated Stream).
4. Watch:
   - KPI cards update live
   - Alerts populate for Suspicious/Fraud
   - Transaction feed appends rows (append-only, keeps recent history)
   - Chart updates in real time

If API is not on `http://localhost:8000`, set **API Base URL** in the control panel and click **Apply**.

### 1.6 Call `/predict` using the correct feature length

```bash
python3 - <<'PY'
import json
import urllib.request
import urllib.error

API = "http://localhost:8000"

health = json.loads(urllib.request.urlopen(f"{API}/health").read().decode("utf-8"))
n = int(health.get("expected_features") or 0)
if n != 30:
    raise SystemExit(f"expected_features must be 30 for the creditcard contract, got {n}")

features = [0.0] * 30

req = urllib.request.Request(
    f"{API}/predict",
    data=json.dumps({"features": features}).encode(),
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req).read().decode())
PY
```

### 1.7 Run tests + coverage gate

```bash
pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80
```

## 2) Run Docker Compose (full stack)

### 2.1 Generate artifacts on the host (required)

Recommended (real dataset):
```bash
python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts --seed 42
```

### 2.2 Start the stack

```bash
docker compose -f deployment/docker-compose.yml up --build
```

Service URLs:
- API: `http://localhost:8000` (Swagger: `/docs`, Metrics: `/metrics`)
- Frontend: `http://localhost:8080` (change the port mapping in `deployment/docker-compose.yml` if 8080 is already in use)
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (admin/admin by default)

### 2.3 Quick checks

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | grep -m1 api_requests_total
```

### 2.4 Alert rules (Prometheus)

- Open Prometheus: `http://localhost:9090`
- Navigate to `Status -> Rules` or the `Alerts` tab
- Rules are loaded from: `deployment/prometheus/alerts.yml`

## 3) Troubleshooting

### Ports 8000/8080 already in use

Linux:
```bash
ss -ltnp | grep -E ':(8000|8080)\\b' || true
```

Windows PowerShell:
```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

If you can’t stop the existing services, use different ports.

Example (API on 8010):
```bash
# Terminal 1 (API)
MODEL_PATH=artifacts/model.joblib \
uvicorn src.api.main:app --host 0.0.0.0 --port 8010
```

Then start the frontend on any free port:
```bash
cd frontend
python3 -m http.server 0 --bind 127.0.0.1
```
And set the **API Base URL** in the UI to `http://localhost:8010`.

Note: Local dev CORS no longer requires `CORS_ALLOW_ORIGINS` when using localhost ports.

### Matplotlib cache warning

If Matplotlib cannot write its cache, set:
```bash
export MPLCONFIGDIR=/tmp/matplotlib
```

### `verify_system.py`

`verify_system.py` uses the Kaggle creditcard feature order (Time + V1..V28 + Amount), so it is compatible with `creditcard.csv`.
If you trained a synthetic model (different feature length), use the Python snippet in section 1.6 to call `/predict` with the correct length.
- **Documentation**: http://127.0.0.1:8000/docs
- **Metrics**: http://127.0.0.1:8000/metrics

---

## ✅ Checklist

- [ ] API chạy trên port 8000
- [ ] Frontend chạy trên port 8080
- [ ] Model loaded successfully
- [ ] Predictions working
- [ ] Metrics collecting
- [ ] End-to-end test passed

---

**Hệ thống sẵn sàng để demo! / System ready for demo!**
