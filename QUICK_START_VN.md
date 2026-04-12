# Hướng Dẫn Chạy Hệ Thống Phát Hiện Gian Lận (Fraud Detection System)

## 📋 Quick Start / Bắt Đầu Nhanh

### Prerequisites / Yêu Cầu
- Python 3.11+ với virtual environment đã được thiết lập
- Tất cả dependencies đã được install trong `.venv`

### Chạy Hệ Thống Cục Bộ / Running Locally

#### **Bước 1: Mở Terminal / Open Terminal**

```bash
# Đi đến thư mục dự án
cd "d:\MSE\12. AI in DevOps, DataOps, MLOps\Final_Project"
```

#### **Bước 2: Khởi Động Backend API**

**Terminal 1:**
```powershell
$env:MODEL_PATH="artifacts/models/improved_lightgbm.joblib"
$env:FRAUD_THRESHOLD="0.14"
$env:MODEL_VERSION="lightgbm-production-v1"
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

**Expected Output:**
```
INFO:     Started server process [27440]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

✓ **API is Ready** → http://127.0.0.1:8000

#### **Bước 3: Khởi Động Frontend**

**Terminal 2:**
```powershell
cd "d:\MSE\12. AI in DevOps, DataOps, MLOps\Final_Project\frontend"
python -m http.server 8080 --bind 127.0.0.1
```

**Expected Output:**
```
Serving HTTP on 127.0.0.1 port 8080 (http://127.0.0.1:8080/) ...
```

✓ **Frontend is Ready** → http://127.0.0.1:8080/index.html

---

## 🎯 Sử Dụng Hệ Thống / Using the System

### Truy Cập Giao Diện Web

1. **Mở trình duyệt** / Open Browser
2. **Điều hướng đến** / Navigate to: `http://127.0.0.1:8080/index.html`
3. **Kết quả** / Result:

```
┌─────────────────────────────────────┐
│  🔒 Fraud Detection System          │
│  Real-time fraud prediction         │
├─────────────────────────────────────┤
│  Transaction Details                │
│  Time: [0]                          │
│  Amount: [149.62]                   │
│  Features V1-V28: [Loaded Sample]   │
├─────────────────────────────────────┤
│  📋 Load Sample  🔍 Predict Fraud   │
├─────────────────────────────────────┤
│  Prediction Result                  │
│  ✓ LEGITIMATE                       │
│  Fraud Probability: 0.00%           │
└─────────────────────────────────────┘
```

### API Endpoints / Các Điểm Cuối API

#### 1. **Health Check** - Kiểm tra trạng thái mô hình

```bash
# Request
curl http://127.0.0.1:8000/health

# Response
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "lightgbm-production-v1",
  "expected_features": 30
}
```

#### 2. **Prediction** - Dự đoán gian lận

```bash
# Request (30 features: Time + V1-V28 + Amount)
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": [0.0, -1.36, -0.07, 2.54, 1.38, -0.34, 0.46, 0.24, 0.10, 0.36, 0.09, -0.55, -0.62, -0.99, -0.31, 1.47, -0.47, 0.21, 0.03, 0.40, 0.25, -0.02, 0.28, -0.11, 0.07, 0.13, -0.19, 0.13, -0.02, 149.62]
  }'

# Response
{
  "request_id": "abc-123-def",
  "fraud_probability": 0.000000,
  "fraud_label": 0,
  "threshold": 0.14,
  "model_version": "lightgbm-production-v1"
}
```

#### 3. **Metrics** - Chỉ số hiệu suất

```bash
# Request
curl http://127.0.0.1:8000/metrics

# Response: Prometheus format metrics
api_requests_total{endpoint="/predict",http_status="200",method="POST"} 5.0
api_request_latency_seconds_bucket{endpoint="/predict",le="0.05",method="POST"} 5.0
fraud_predictions_total{label="0"} 4.0
```

#### 4. **Documentation** - Tài liệu API

```
http://127.0.0.1:8000/docs
```

Swagger UI sẽ hiển thị tất cả endpoints và cho phép test trực tiếp.

---

## 🐳 Docker (Nếu Docker Được Cài Đặt / If Docker is Installed)

### Kiểm Tra Docker

```bash
docker --version
docker-compose --version
```

### Xây Dựng Images

```bash
cd deployment
docker build -f api/Dockerfile -t fraud-detection-api:latest ..
docker build -f frontend/Dockerfile -t fraud-detection-frontend:latest ..
```

### Chạy Full Stack

```bash
cd deployment
docker-compose up --build
```

**Services sẽ available:**
- API: http://localhost:8000
- Frontend: http://localhost:8080
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

---

## 📊 Model Information / Thông Tin Mô Hình

| Thuộc Tính | Giá Trị |
|-----------|--------|
| **Model Type** | LightGBM Classifier |
| **Features** | 30 (Time + V1-V28 + Amount) |
| **Threshold** | 0.14 |
| **PR-AUC** | 0.8156 |
| **F1 Score** | 0.8321 |
| **Status** | ✓ Production Ready |

### Feature Order / Thứ Tự Các Đặc Trưng

```
1. Time              - Khung thời gian
2-29. V1 to V28     - Principal Component Analysis features
30. Amount          - Số tiền giao dịch
```

---

## ✓ Verification / Kiểm Tra Hệ Thống

### Run Verification Script

```bash
cd "d:\MSE\12. AI in DevOps, DataOps, MLOps\Final_Project"
.\.venv\Scripts\python.exe verify_system.py
```

**Expected Output:**
```
======================================================================
FRAUD DETECTION SYSTEM - END-TO-END VERIFICATION
======================================================================

[1/6] Checking API Health...
      ✓ API Available (Status: 200)
      ✓ Model Loaded: True
      ✓ Model Version: lightgbm-production-v1
      ✓ Expected Features: 30

[2/6] Testing Legitimate Transaction Prediction...
      ✓ Prediction Success (Status: 200)
      ✓ Fraud Probability: 0.000000
      ✓ Fraud Label: 0

[3/6] Testing High-Value Transaction...
      ✓ Prediction with Different Amount

[4/6] Testing Error Handling...
      ✓ Error Handling Works

[5/6] Checking Metrics Endpoint...
      ✓ Metrics Endpoint Available

[6/6] Checking Frontend...
      ✓ Frontend Available
      ✓ Frontend HTML Valid
      ✓ URL: http://127.0.0.1:8080/index.html

======================================================================
✓ END-TO-END VERIFICATION COMPLETE
======================================================================
```

---

## 🔧 Xử Lý Sự Cố / Troubleshooting

### Problem: Port 8000 đã được sử dụng

**Solution:**
```bash
# Tìm process sử dụng port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F

# Hoặc sử dụng port khác
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8001
```

### Problem: ModuleNotFoundError: prometheus_client

**Solution:**
```bash
# Đảm bảo sử dụng đúng virtual environment
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000

# KHÔNG dùng
uvicorn src.api.main:app --host 127.0.0.1 --port 8000  # ❌ Sai
```

### Problem: Frontend không thể gọi API

**Solution:**
```javascript
// Nếu frontend và API chạy trên máy tính khác:
// Thay đổi API_URL trong frontend/index.html
const API_URL = 'http://<server-ip>:8000';  // Thay <server-ip>
```

---

## 📝 File Structure / Cấu Trúc File

```
Final_Project/
├── src/
│   ├── api/
│   │   ├── main.py           (FastAPI application)
│   │   └── schemas.py        (Pydantic request/response models)
│   ├── models/
│   │   └── loader.py         (Model loading logic)
│   ├── features/
│   │   └── preprocess.py     (Feature preprocessing)
│   └── monitoring/
│       └── metrics.py        (Prometheus metrics)
├── frontend/
│   └── index.html            (Interactive UI)
├── artifacts/
│   └── models/
│       └── improved_lightgbm.joblib  (Trained model)
├── deployment/
│   ├── api/
│   │   └── Dockerfile        (API container)
│   ├── frontend/
│   │   └── Dockerfile        (Frontend container)
│   ├── docker-compose.yml    (Multi-service orchestration)
│   ├── prometheus/
│   │   └── prometheus.yml    (Metrics scraping config)
│   └── grafana/
│       └── dashboards/       (Monitoring dashboards)
├── .env                      (Environment variables)
├── requirements.txt          (Python dependencies)
└── verify_system.py          (System verification script)
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
