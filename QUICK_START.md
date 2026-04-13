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
python -m venv .venv
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

Option A (real dataset model):
```bash
MODEL_PATH=artifacts/models/final_model.joblib \
MODEL_VERSION=creditcard-production-v1 \
FRAUD_THRESHOLD=0.99 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Option B (synthetic model):
```bash
MODEL_PATH=artifacts/model.joblib \
MODEL_VERSION=local-demo \
FRAUD_THRESHOLD=0.14 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Endpoints:
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Metrics: `http://localhost:8000/metrics`
- Random features: `http://localhost:8000/features/random`

### 1.5 Run the Frontend (demo UI)

```bash
cd frontend
python -m http.server 8080 --bind 0.0.0.0
```

Open:
- `http://localhost:8080/index.html`

### 1.6 Call `/predict` using the correct feature length

```bash
python - <<'PY'
import json
import urllib.request

import requests

health = requests.get("http://localhost:8000/health").json()
n = int(health["expected_features"] or 0)
features = [0.0] * n

req = urllib.request.Request(
    "http://localhost:8000/predict",
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
- Frontend: `http://localhost:8080`
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
sudo lsof -i :8000
sudo lsof -i :8080
```

Windows PowerShell:
```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

If you can’t stop the existing services, use different ports. Example:
```bash
# Terminal 1 (API)
MODEL_PATH=artifacts/model.joblib \
CORS_ALLOW_ORIGINS=http://localhost:8090,http://127.0.0.1:8090 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8010
```
```bash
# Terminal 2 (Frontend)
cd frontend
python -m http.server 8090 --bind 0.0.0.0
```
Open `http://localhost:8090/index.html?api=http://localhost:8010`.

### Matplotlib cache warning

If Matplotlib cannot write its cache, set:
```bash
export MPLCONFIGDIR=/tmp/matplotlib
```

### `verify_system.py`

`verify_system.py` uses the Kaggle creditcard feature order (Time + V1..V28 + Amount), so it is compatible with `creditcard.csv`.
If you trained a synthetic model (different feature length), use the Python snippet in section 1.6 to call `/predict` with the correct length.

    └── models/
        ├── final_model.joblib
        └── model_info.json
```

---

## 🚀 Workflow Demo / Quy Trình Demo

### Scenario 1: Dự Đoán Giao Dịch Hợp Pháp

1. Mở http://127.0.0.1:8080/index.html
2. Click "📋 Load Sample"
3. Giao dịch mẫu sẽ tải (Amount: $149.62)
4. Click "🔍 Predict Fraud"
5. Kết quả: "✓ LEGITIMATE" (xác suất chiếm 0%)

### Scenario 2: Dự Đoán Giao Dịch Nghi Vấn

1. Click "📋 Load Sample" để tải mẫu
2. Thay đổi "Amount" thành "$5000"
3. Click "🔍 Predict Fraud"
4. Xem kết quả dự đoán

### Scenario 3: Kiểm Tra Metrics

1. Mở http://127.0.0.1:8000/metrics
2. Xem các chỉ số:
   - `api_requests_total` - Tổng request
   - `api_request_latency_seconds` - Độ trễ
   - `fraud_predictions_total` - Dự đoán gian lận

---

## 📞 Support / Hỗ Trợ

- **API Status**: http://127.0.0.1:8000/health
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
