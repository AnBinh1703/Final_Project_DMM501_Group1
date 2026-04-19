# Service Links & Quick Reference

## 🔗 API & Documentation

| Service | URL | Purpose |
|---------|-----|---------|
| **API Health** | http://localhost:8000/health | Model status, thresholds, repository mode |
| **Swagger UI** | http://localhost:8000/docs | Interactive API documentation |
| **OpenAPI Spec** | http://localhost:8000/openapi.json | Machine-readable API specification |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics export (text format) |

## 📊 Frontend Dashboard

| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | http://localhost:8082/ | Fraud alert queue, case management, timeline |
| **Index** | http://localhost:8082/index.html | Alternative entry point |

## 📈 Monitoring & Observability

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Prometheus** | http://localhost:9090/ | None | Metrics database & query engine |
| **Grafana** | http://localhost:3000/ | admin/admin | Pre-built fraud detection dashboards |
| **MLflow** | http://localhost:5000/ | None | Experiment tracking & model registry |

## 🗄️ Database (Internal Container Network)

| Property | Value |
|----------|-------|
| **Host** | postgres (inside Docker) / localhost:5433 (from host) |
| **Port** | 5432 (internal) / 5433 (external host) |
| **Database** | fraud_ops |
| **Username** | fraud |
| **Password** | fraud |
| **Note** | Port 5433 used on host due to local 5432 conflict |

## 🔐 Authentication Tokens

All tokens must be sent as `Authorization: Bearer <token>` header.

| Role | Token | Permissions |
|------|-------|-------------|
| **Viewer** | viewer-token | Read-only: alerts, cases, timeline |
| **Analyst** | analyst-token | Read + Write: case status updates, resolutions |
| **Admin** | admin-token | Full access: case ops + audit events |

## 📝 Example API Calls

### Check API Health
```bash
curl http://localhost:8000/health | python -m json.tool
```

### Get Alerts (Viewer)
```bash
curl -H "Authorization: Bearer viewer-token" \
  http://localhost:8000/alerts?limit=10 | python -m json.tool
```

### Get Cases (Viewer)
```bash
curl -H "Authorization: Bearer viewer-token" \
  http://localhost:8000/cases?limit=10 | python -m json.tool
```

### Get Case Timeline
```bash
curl -H "Authorization: Bearer viewer-token" \
  "http://localhost:8000/cases/{case_id}/timeline" | python -m json.tool
```

### Update Case Status (Analyst)
```bash
curl -X POST -H "Authorization: Bearer analyst-token" \
  -H "Content-Type: application/json" \
  -d '{"case_status":"IN_REVIEW","analyst_note":"triage started","actor":"analyst-1"}' \
  "http://localhost:8000/cases/{case_id}/status"
```

### Resolve Case as False Positive (Analyst)
```bash
curl -X POST -H "Authorization: Bearer analyst-token" \
  -H "Content-Type: application/json" \
  -d '{"resolution":"FALSE_POSITIVE","analyst_note":"customer confirmed legitimate","actor":"analyst-1"}' \
  "http://localhost:8000/cases/{case_id}/resolve"
```

### Get Audit Events (Admin Only)
```bash
curl -H "Authorization: Bearer admin-token" \
  "http://localhost:8000/audit/events?limit=50&event_type=RBAC_FORBIDDEN" | python -m json.tool
```

### Get Metrics (No Auth Required)
```bash
curl http://localhost:8000/metrics | head -50
```

## 🐳 Docker Compose Management

### Start Stack (with port override for 5432 conflict)
```bash
cd deployment
POSTGRES_PORT=5433 docker compose -f docker-compose.yml up -d --build
```

### Check Service Status
```bash
cd deployment
docker compose -f docker-compose.yml ps
```

### View Logs
```bash
cd deployment
docker compose logs -f api          # API logs
docker compose logs -f postgres     # PostgreSQL logs
docker compose logs -f frontend     # Frontend logs
```

### Stop Stack
```bash
cd deployment
docker compose -f docker-compose.yml down
```

### Stop & Remove Data
```bash
cd deployment
docker compose -f docker-compose.yml down -v
```

## ✅ Service Status

All 6 services running:
- ✓ **postgres:5433** → PostgreSQL (durable case repository)
- ✓ **api:8000** → FastAPI fraud decision engine
- ✓ **frontend:8082** → JavaScript dashboard
- ✓ **prometheus:9090** → Metrics scraper & query engine
- ✓ **grafana:3000** → Dashboard visualization
- ✓ **mlflow:5000** → Experiment tracking

## 📚 Documentation

| Document | Path | Purpose |
|----------|------|---------|
| **Executive Report** | docs/EXECUTIVE_COMPLETION_REPORT.md | Summary of all features & verification |
| **Full Specification** | docs/SYSTEM_SPECIFICATION_DOCUMENT.md | 23-page detailed spec with diagrams |
| **Runtime Checklist** | docs/RUNTIME_VERIFICATION_CHECKLIST.md | Live-stack endpoint evidence |
| **Quick Start** | docs/QUICK_START.md | Setup & API usage guide |
| **Decision Support Details** | docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md | Complete feature matrix |
| **Responsible AI** | docs/RESPONSIBLE_AI.md | Fairness, privacy, ethics analysis |

## 🎯 Quick Verification Checklist

- [ ] API responds at http://localhost:8000/health (status=ok)
- [ ] Swagger docs available at http://localhost:8000/docs
- [ ] Frontend loads at http://localhost:8082
- [ ] Prometheus accessible at http://localhost:9090 (click Status → Targets)
- [ ] Grafana dashboard available at http://localhost:3000 (login admin/admin)
- [ ] Auth enforced: `/cases` without token returns 401
- [ ] Role-based: viewer token can read `/cases`, analyst token can update
- [ ] Rate limiting: X-RateLimit-* headers present in responses

---

**Last Updated:** April 18, 2026  
**Status:** ✅ All services operational
