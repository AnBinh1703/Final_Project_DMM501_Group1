# Huong Dan Chay Project (Local + Docker)

Tai lieu nay huong dan cach chay day du he thong Fraud Detection theo 2 cach:
- Chay local (Python venv, run ML pipeline, run API, run frontend, run tests)
- Chay Docker Compose local (API + Frontend + MLflow + Prometheus + Grafana)

Dataset (da co san tren may):
- `data/archive/creditcard.csv`

Luu y:
- File dataset CSV lon thuong KHONG commit vao Git (chi dat local).
- Docker Compose mount thu muc `./artifacts` tu may host; hay tao artifacts truoc khi `docker compose up`.

## 0) Prerequisites
- Python 3.11+
- Docker + Docker Compose (neu muon chay full stack bang Docker)

## 1) Chay Local (khong can Docker)

### 1.1 Tao virtual env + cai dependencies

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

### 1.2 Tao artifacts tu dataset that (khuyen nghi)

Day la workflow day du: data validation + EDA + baseline + improved + threshold tuning + model selection + SHAP.

```bash
python -m src.pipelines.run_model_workflow \
  --data-path data/archive/creditcard.csv \
  --artifacts-root artifacts \
  --seed 42
```

Artifacts quan trong:
- Data validation:
  - `artifacts/reports/dataset_schema.json`
  - `artifacts/reports/missing_values.csv`
  - `artifacts/reports/class_distribution.json`
- EDA figures: `artifacts/figures/*.png`
- Model figures (phuc vu bao cao/presentation):
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

### 1.3 (Option) Tao artifacts nhanh (synthetic dataset)

Neu can demo nhanh, co the train synthetic:
```bash
python -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts --fast
```
Output:
- `artifacts/model.joblib`
- `artifacts/model_info.json`
- `artifacts/metrics_report.json`

### 1.4 Run Backend API (FastAPI)

Option A (dung final model tu dataset that):
```bash
MODEL_PATH=artifacts/models/final_model.joblib \
MODEL_VERSION=creditcard-production-v1 \
FRAUD_THRESHOLD=0.99 \
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Option B (dung model synthetic):
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

### 1.5 Run Frontend (demo UI)

```bash
cd frontend
python -m http.server 8080 --bind 0.0.0.0
```

Mo trinh duyet:
- `http://localhost:8080/index.html`

### 1.6 Goi thu /predict (tu dong lay dung feature length)

```bash
python - <<'PY'
import json, urllib.request
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

## 2) Chay Docker Compose Local (full stack)

### 2.1 Tao artifacts tren host (bat buoc)

Khuyen nghi (dataset that):
```bash
python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts --seed 42
```

### 2.2 Start full stack

```bash
docker compose -f deployment/docker-compose.yml up --build
```

Services:
- API: `http://localhost:8000` (Swagger: `/docs`, Metrics: `/metrics`)
- Frontend: `http://localhost:8080`
- MLflow: `http://localhost:5000`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (mac dinh: admin/admin)

### 2.3 Kiem tra nhanh

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | grep -m1 api_requests_total
```

### 2.4 Kiem tra alerts (Prometheus)

- Mo Prometheus: `http://localhost:9090`
- Vao `Status -> Rules` hoac tab `Alerts`
- Alert rules duoc load tu: `deployment/prometheus/alerts.yml`

## 3) Troubleshooting

### Port 8000/8080 bi chiem

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

### Matplotlib cache warning

Neu thay warning ve Matplotlib cache khong ghi duoc, hay set:
```bash
export MPLCONFIGDIR=/tmp/matplotlib
```

### verify_system.py

`verify_system.py` co payload mau theo schema Kaggle (Time + V1..V28 + Amount), nen phu hop voi dataset `creditcard.csv`.
Neu ban train synthetic (so feature khac), hay dung doan Python o muc 1.6 de goi /predict theo dung feature length.

## File Structure (rut gon)

```
.
├── src/
├── tests/
├── frontend/
├── deployment/
├── data/archive/creditcard.csv
└── artifacts/
    ├── reports/
    ├── figures/
    ├── benchmarks/
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
