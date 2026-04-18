# Real-Time Fraud Detection ML System

**End-to-End Solution for Risk Scoring & Decision Intelligence**  
*DDM501 Final Project | HCMUTE Advanced Master Program*

[![CI](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/ci.yml/badge.svg)](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/ci.yml)
[![Docker](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/docker.yml/badge.svg)](https://github.com/AnBinh1703/Final_Project_DMM501_Group1/actions/workflows/docker.yml)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen)](#-testing)

---

## 📋 Quick Summary

**Problem:** Card fraud causes financial loss. A ranking model identifies risky transactions; business divides them into tiers for action.

**Solution:** ML system that scores transactions (0-1 risk signal), maps scores to decisions (allow/review/block), and serves via API with full observability.

**Status:** ✅ Complete, tested, deployed

---

## 🎯 Core Features

- **ML Pipeline** → Data ingestion, train/evaluate, threshold tuning, model versioning
- **REST API** → `/predict`, `/health`, `/metrics` (FastAPI + Pydantic validation)
- **3-Tier Decisions** → LOW (allow), REVIEW (review, top 1%), HIGH (block, top 0.2%)
- **Real-Time Monitoring** → Prometheus metrics + Grafana dashboards + alert rules
- **Interactive Dashboard** → Streaming fraud predictions (Vanilla JavaScript)
- **Docker Stack** → Compose orchestration (API, frontend, Prometheus, Grafana, MLflow)
- **Rigorous Testing** → 80%+ coverage, unit + integration + data quality tests
- **Production Deployment** → GitHub Actions CI/CD, versioned artifacts, health checks

---

## 📊 Performance

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| **PR-AUC** (test) | ≥ 0.75 | **0.769** | ✅ |
| **ROC-AUC** (test) | — | **0.965** | ✅ |
| **p95 Latency** | ≤ 500ms | **~150ms** | ✅ |
| **Test Coverage** | ≥ 80% | **80%+** | ✅ |
| **Model PR-AUC** (selected) | — | 0.769 | ✅ |
| **Review Tier Recall** | High | 85.1% | ✅ |
| **High Tier Precision** | High | 84.3% | ✅ |

---

## 🚀 Quick Start (5 minutes)

### 1. Setup
```bash
# Clone & setup environment
git clone https://github.com/AnBinh1703/Final_Project_DMM501_Group1.git
cd Final_Project_DMM501_Group1
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Train Model
```bash
python -m src.pipelines.run_model_workflow \
    --data-path data/archive/creditcard.csv \
    --artifacts-dir artifacts
```

### 3. Run API Locally
```bash
python -m src.api.main
# Visit http://localhost:8000/docs
```

### 4. Deploy with Docker
```bash
cd deployment
docker-compose up --build

# Services:
# API: http://localhost:8000
# Frontend: http://localhost:8082
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

### 5. Test
```bash
pytest -v
pytest --cov=src --cov-report=html
```

---

## 📁 Directory Structure

```
Final_Project_DMM501_Group1/
│
├── 📄 README.md                           # This file
├── 📄 ARCHITECTURE.md                     # System design & data flows
├── 📄 QUICK_START.md                      # Detailed setup guide
├── 📄 RESPONSIBLE_AI.md                   # Fairness, explainability, privacy
├── 📄 CONTRIBUTING.md                     # Git workflow & code standards
├── 📄 SYSTEM_SPECIFICATION_DOCUMENT.md    # Complete formal spec (12K words, 23 sections)
│
├── 📁 src/                                # Source code (production)
│   ├── api/                               # FastAPI application
│   │   ├── main.py                        # /predict, /health, /metrics
│   │   └── schemas.py                     # Pydantic models
│   ├── pipelines/                         # ML training
│   │   ├── run_model_workflow.py          # Main training orchestration
│   │   ├── train_baselines.py
│   │   ├── train_improved.py
│   │   └── evaluate.py
│   ├── models/                            # Model artifact handling
│   │   ├── loader.py                      # Load models & metadata
│   │   └── predictor.py                   # Inference logic
│   ├── data/                              # Data operations
│   │   ├── loader.py                      # CSV ingestion
│   │   ├── validation.py                  # Schema validation
│   │   └── sampling.py
│   ├── features/                          # Feature engineering
│   │   └── preprocessing.py
│   ├── monitoring/                        # Prometheus metrics
│   │   └── metrics.py
│   ├── streaming/                         # Event simulation (demo)
│   │   └── simulator.py
│   └── utils/                             # Utilities
│       ├── ids.py
│       └── logging.py
│
├── 📁 tests/                              # Test suite (80%+ coverage)
│   ├── unit/                              # Unit tests
│   ├── integration/                       # Integration tests
│   ├── data/                              # Data quality tests
│   ├── model/                             # Model pipeline tests
│   ├── test_frontend_api.py               # Frontend integration
│   └── verify_system.py                   # Smoke test
│
├── 📁 frontend/                           # Web dashboard (Vanilla JS)
│   ├── index.html
│   ├── app.js
│   ├── ui.js
│   ├── api-client.js
│   └── styles.css
│
├── 📁 deployment/                         # Docker & monitoring
│   ├── docker-compose.yml
│   ├── api/Dockerfile
│   ├── frontend/Dockerfile
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts.yml
│   └── grafana/
│       └── dashboards/fraud_api.json
│
├── 📁 artifacts/                          # Model outputs
│   ├── models/
│   │   ├── final_model.joblib             # Deployed model
│   │   ├── baseline_logistic_regression_pipeline.joblib
│   │   ├── improved_lightgbm.joblib
│   │   └── model_info.json                # Metadata (thresholds, version)
│   ├── figures/                           # Visualizations (29 PNG)
│   ├── benchmarks/                        # Performance tables (CSV)
│   ├── reports/                           # Analysis artifacts (JSON)
│   └── mlflow.db
│
├── 📁 data/
│   └── archive/
│       └── creditcard.csv                 # Kaggle fraud dataset (284K rows)
│
├── 📁 latex/                              # PDF reports
│   ├── SYSTEM_SPECIFICATION_COMPLETE.tex
│   └── SYSTEM_SPECIFICATION_COMPLETE.pdf  # 23-page formatted PDF
│
├── 📁 docs/                               # Archived reports & guides
│   ├── SYSTEM_DELIVERY_REPORT.md
│   ├── EXECUTION_NOTES_PRESENTATION_GUIDE.md
│   └── ... (other audit/reference docs)
│
├── .github/workflows/                     # CI/CD
│   ├── ci.yml                             # Test + coverage gate
│   └── docker.yml                         # Docker build
│
├── Makefile                               # Development shortcuts
├── requirements.txt                       # Python dependencies
├── pytest.ini                             # Test configuration
└── .gitignore
```

---

## 📚 Documentation

| Document | Purpose | Link |
|----------|---------|------|
| **This File** | Overview & quick start | README.md ← |
| **ARCHITECTURE.md** | System design, data flows, components | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **QUICK_START.md** | Detailed setup (local + Docker) | [QUICK_START.md](QUICK_START.md) |
| **RESPONSIBLE_AI.md** | Fairness, privacy, ethics, explainability | [RESPONSIBLE_AI.md](RESPONSIBLE_AI.md) |
| **SYSTEM_SPECIFICATION_DOCUMENT.md** | Complete formal spec (12K words) | [SYSTEM_SPECIFICATION_DOCUMENT.md](SYSTEM_SPECIFICATION_DOCUMENT.md) |
| **CONTRIBUTING.md** | Git workflow & code standards | [CONTRIBUTING.md](CONTRIBUTING.md) |
| **SYSTEM_SPECIFICATION_COMPLETE.pdf** | Formatted PDF report (23 pages) | [latex/SYSTEM_SPECIFICATION_COMPLETE.pdf](latex/SYSTEM_SPECIFICATION_COMPLETE.pdf) |

---

## 🔄 API Specification

### POST /predict
**Score a transaction**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": [10.0, -1.3, 1.5, ..., 0.5]  # 30 floats
  }'
```

**Response (200):**
```json
{
  "request_id": "req-abc123...",
  "risk_score": 0.85,
  "risk_tier": "REVIEW",
  "action": "review",
  "threshold_review": 0.7391,
  "threshold_high": 0.9999,
  "score_semantics": "risk_score_uncalibrated",
  "model_version": "20260415T094316Z"
}
```

**Error (422):** Feature count mismatch  
**Error (503):** Model not loaded

### GET /health
**System status**

```bash
curl -X GET http://localhost:8000/health
```

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "20260415T094316Z",
  "expected_features": 30,
  "threshold_review": 0.7391,
  "threshold_high": 0.9999,
  "score_semantics": "risk_score_uncalibrated"
}
```

### GET /metrics
**Prometheus metrics**

```bash
curl -X GET http://localhost:8000/metrics
```

### GET /stream/pull
**Event stream (demo)**

Returns paginated scored events for dashboard simulation.

---

## 🧪 Testing

### Run All Tests
```bash
pytest -v
```

### Coverage Report
```bash
pytest --cov=src --cov-report=html
# Opens: htmlcov/index.html
```

### Test Suites

| Suite | Location | Tests | Status |
|-------|----------|-------|--------|
| **Unit** | tests/unit/ | 25+ | ✅ Passing |
| **Integration** | tests/integration/ | 15+ | ✅ Passing |
| **Data** | tests/data/ | 10+ | ✅ Passing |
| **Model** | tests/model/ | 12+ | ✅ Passing |
| **Smoke** | tests/ | 5+ | ✅ Passing |

**Coverage:** 80%+ (enforced gate)

---

## 🛠️ Development

### Setup Dev Environment
```bash
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest-cov black flake8

# Pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Code Style
```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, test
pytest -v

# Commit with conventional commits
git commit -m "feat: add new endpoint"

# Push and create PR
git push origin feature/my-feature
```

---

## 🚢 Deployment

### Local Docker
```bash
cd deployment
docker-compose up --build
```

### Single Services
```bash
# API
docker build -f deployment/api/Dockerfile -t fraud-api .
docker run -p 8000:8000 -v "$PWD/artifacts:/app/artifacts" fraud-api

# Frontend
docker build -f deployment/frontend/Dockerfile -t fraud-frontend .
docker run -p 8082:8082 fraud-frontend
```

### Production Checklist
- ✅ Model artifact versioned & tested
- ✅ API health checks configured
- ✅ Monitoring (Prometheus + Grafana) active
- ✅ Tests passing (80%+ coverage)
- ⏱️ TODO: Add authentication/rate limiting
- ⏱️ TODO: Add drift detection
- ⏱️ TODO: Configure TLS/HTTPS

---

## 📊 Monitoring

### Prometheus
- **URL:** http://localhost:9090
- **Metrics:** API requests, latency, predictions, errors
- **Alert Rules:** High error rate, high latency, low traffic

### Grafana
- **URL:** http://localhost:3000 (admin/admin)
- **Dashboards:** Fraud Detection API Monitoring
- **Panels:** Request rate, latency p95, fraud distribution

---

## 🤖 Model Details

### Selected Model: Logistic Regression ✅

**Why:**
- Test PR-AUC: **0.769** (≥ 0.75 target)
- Interpretable (coefficient-based explainability)
- Stable and robust to imbalance

**Baseline Comparison:**
| Baseline | LightGBM | Winner |
|----------|----------|--------|
| Val PR-AUC: 0.630 | Val PR-AUC: 0.629 | Baseline ✅ |
| Review Recall: 0.851 | Review Recall: 0.770 | Baseline ✅ |

### Decision Policy: Top-K Tiering

| Tier | Threshold | Rate | Action |
|------|-----------|------|--------|
| LOW | < 0.7391 | — | allow |
| REVIEW | 0.7391–0.9999 | Top 1% | review |
| HIGH | ≥ 0.9999 | Top 0.2% | block |

### ⚠️ Critical Limitation

**Risk score is NOT a calibrated probability of fraud.**

It's an uncalibrated ranking signal. Use for prioritization, not for "Customer X has 85% chance of fraud" claims.

See [RESPONSIBLE_AI.md](RESPONSIBLE_AI.md) for details.

---

## 🔐 Security & Privacy

### Current ✅
- No PII in inputs (feature vectors only)
- Pydantic schema validation
- Generic error messages
- CORS configured for localhost

### Future (Production Gap) ⏱️
- [ ] Authentication (JWT/API key)
- [ ] Rate limiting
- [ ] TLS/HTTPS
- [ ] Audit logging
- [ ] Secrets management

---

## ✅ Acceptance Criteria (All Met)

- ✅ PR-AUC ≥ 0.75 on test set (0.769 achieved)
- ✅ API endpoints correct with error handling
- ✅ Docker Compose deployment working
- ✅ Prometheus metrics & Grafana dashboards
- ✅ Frontend connects to API
- ✅ 80% test coverage enforced
- ✅ Documentation complete
- ✅ CI/CD pipeline running
- ✅ Responsible AI analysis
- ✅ Clean repository

---

## 👥 Team

**DDM501 Group 1 | HCMUTE Advanced Master Program**

| Name | Role | ID |
|------|------|-----|
| Duong Binh An | ML Engineering Lead | 25MSA23234 |
| Nguyen Le Hong Nhi | Full Stack | 25MSA23235 |
| Le Quang Tuyen | DevOps & Testing | 25MSA23232 |

**Instructor:** PhD Huynh Cong Viet Ngu

---

## 📝 License

Part of DDM501 Advanced Master Program at HCMUTE.

---

**Last Updated:** April 16, 2026 | **Status:** Complete ✅
