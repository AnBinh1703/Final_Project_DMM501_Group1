# Quick Access Guide — Deployed Services

**Status:** ✅ All Services Running  
**Deployment Time:** April 16, 2026  
**Environment:** Docker Compose

---

## 🚀 Access Services

### 📊 API & Documentation

| Service | URL | Description |
|---------|-----|-------------|
| **API Swagger** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive API documentation |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Model status JSON |
| **Metrics** | [http://localhost:8000/metrics](http://localhost:8000/metrics) | Prometheus metrics (text format) |
| **OpenAPI** | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) | OpenAPI specification |

### 🎨 Dashboard

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | [http://localhost:8082](http://localhost:8082) | Real-time fraud detection dashboard |

### 📈 Monitoring

| Service | URL | Login | Description |
|---------|-----|-------|-------------|
| **Prometheus** | [http://localhost:9090](http://localhost:9090) | None | Metrics database & query engine |
| **Grafana** | [http://localhost:3000](http://localhost:3000) | admin/admin | Pre-built dashboards & alerts |
| **MLflow** | [http://localhost:5000](http://localhost:5000) | None | Experiment tracking & model registry |

---

## 🔧 Common Tasks

### Test API Prediction

```bash
# Get health status
curl http://localhost:8000/health | python -m json.tool

# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": [10.0, -1.3, 1.5, -0.657, -1.2624, 0.235, 0.2, -0.045, 0.0, 0.089, -0.256, -0.166, 0.14, 0.1, -0.21, 0.05, 0.044, -0.043, -0.073, 0.008, 0.019, -0.389, 0.386, 0.51, -0.481, 0.01, 0.02, 0.03, 0.04, 100.50]
  }'

# Export metrics
curl http://localhost:8000/metrics > metrics.txt
```

### View Prometheus Metrics

1. Visit [http://localhost:9090](http://localhost:9090)
2. Enter a query (examples):
   - `api_requests_total` — Total API requests
   - `api_request_latency_seconds` — Request latency distribution
   - `fraud_predictions_total` — Predictions by tier

### Access Grafana Dashboards

1. Visit [http://localhost:3000](http://localhost:3000)
2. Login: `admin` / `admin`
3. Dashboard: "Fraud Detection API Monitoring"
4. View panels:
   - Request rate over time
   - Error rate percentage
   - p95 latency
   - Prediction distribution

### Manage Deployment

```bash
# View running containers
docker ps

cd /path/to/deployment

# Stop services
docker compose down

# Restart services
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f prometheus

# Rebuild containers
docker compose up -d --build
```

---

## 📋 API Endpoints

### POST /predict
**Score a transaction**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [...]}'
```

**Response:** Risk score, tier, action, metadata

### GET /health
**System status**

```bash
curl http://localhost:8000/health
```

**Response:** Model version, thresholds, feature count, status

### GET /metrics
**Prometheus metrics**

```bash
curl http://localhost:8000/metrics
```

**Response:** Text-format metrics for scraping

### GET /stream/pull
**Event stream (demo)**

```bash
curl http://localhost:8000/stream/pull?page=0
```

**Response:** Paginated scored events

---

## 📊 Model Information

**Selected Model:** Logistic Regression (Production)

```
├─ Version: creditcard-production-v1
├─ Test PR-AUC: 0.769
├─ Test ROC-AUC: 0.965
├─ Features: 30
├─ Review Tier Threshold: 0.7391
└─ High Tier Threshold: 0.9999
```

**Decision Policy:** Top-K Capacity-Driven

```
├─ LOW (auto-allow): < 0.7391
├─ REVIEW (analyst review): 0.7391 - 0.9999
└─ HIGH (auto-block): ≥ 0.9999
```

---

## 🧪 Test the System

### Step 1: Check API Health
```bash
curl http://localhost:8000/health
# Should return: {"status": "ok", "model_loaded": true, ...}
```

### Step 2: Make a Prediction
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [10.0, -1.3, 1.5, ...]}'
# Should return: {"risk_score": 0.xxx, "risk_tier": "LOW/REVIEW/HIGH", ...}
```

### Step 3: Check Metrics
```bash
curl http://localhost:9090/-/healthy
# Should return: HTTP 200 OK
```

### Step 4: View Dashboard
Open [http://localhost:3000](http://localhost:3000) in browser

---

## 🔐 Security Notes

**Current (Demo):**
- ✅ No authentication required
- ✅ No rate limiting
- ✅ Localhost only (CORS restricted)

**For Production:**
- Add JWT/API key authentication
- Implement rate limiting
- Use TLS/HTTPS
- Add audit logging

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| README.md | Project overview & quick start |
| ARCHITECTURE.md | System design & components |
| QUICK_START.md | Detailed setup guide |
| DEPLOYMENT_REPORT.md | Deployment verification |
| SYSTEM_STATUS_REPORT_UPDATED.md | Current system status |
| RESPONSIBLE_AI.md | Fairness, privacy, ethics |

---

## 🆘 Troubleshooting

### Services Not Starting
```bash
# Check if ports are in use
lsof -i :8000  # API
lsof -i :8082  # Frontend
lsof -i :9090  # Prometheus
lsof -i :3000  # Grafana

# Kill existing processes if needed
kill -9 <PID>

# Retry deployment
cd deployment && docker compose restart
```

### Connection Refused
```bash
# Ensure containers are running
docker compose ps

# If not, start them
docker compose up -d
```

### API Returning 503
```bash
# Check if model is loaded
curl http://localhost:8000/health

# If not loaded, check container logs
docker compose logs api

# Verify model artifact exists
ls -lh artifacts/models/final_model.joblib
```

---

## 📞 Service Details

### API Service
- **Container:** deployment-api-1
- **Port:** 8000
- **Framework:** FastAPI
- **Health Check:** `/health`
- **Startup Time:** ~2-3 seconds

### Frontend Service
- **Container:** deployment-frontend-1
- **Port:** 8082
- **Server:** Python http.server
- **Files:** Vanilla HTML/CSS/JS
- **Startup Time:** ~1 second

### Prometheus Service
- **Container:** deployment-prometheus-1
- **Port:** 9090
- **Scrape Interval:** 5 seconds
- **Retention:** 15 days (default)
- **Startup Time:** ~2 seconds

### Grafana Service
- **Container:** deployment-grafana-1
- **Port:** 3000
- **Default Login:** admin/admin
- **Datasource:** Prometheus (pre-configured)
- **Startup Time:** ~3-5 seconds

### MLflow Service
- **Container:** deployment-mlflow-1
- **Port:** 5000
- **Backend:** Local file
- **Startup Time:** ~2-3 seconds

---

## ✅ Verification Checklist

- [ ] Can curl http://localhost:8000/health
- [ ] Can access API docs at http://localhost:8000/docs
- [ ] Can view frontend at http://localhost:8082
- [ ] Can access Prometheus at http://localhost:9090
- [ ] Can login to Grafana at http://localhost:3000
- [ ] Prediction endpoint returns valid response
- [ ] Metrics are being collected

---

**Last Updated:** April 16, 2026  
**Status:** ✅ All Services Running

