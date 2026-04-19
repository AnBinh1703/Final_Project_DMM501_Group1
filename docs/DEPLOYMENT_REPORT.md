# Deployment Report

Date: 2026-04-18

## 1. Scope

This report reflects deployment readiness for the upgraded decision-support system.

## 2. Compose Stack

Defined services in `deployment/docker-compose.yml`:
- api
- frontend
- prometheus
- grafana
- mlflow

Ports:
- API: 8000
- Frontend: 8082
- Prometheus: 9090
- Grafana: 3000
- MLflow: 5000

## 3. Verification Performed in This Session

Verified:
- Compose file renders successfully via:
  - `docker compose -f deployment/docker-compose.yml config`
- Backend test verification:
  - full pytest suite passed (`30 passed`)
  - includes new alert/case/timeline workflow integration tests

Not executed in this session:
- Full runtime launch and interactive validation of all containers (`docker compose up --build`)

## 4. API Runtime Contracts (Deployment-Relevant)

Critical endpoints used by frontend and monitoring:
- `GET /health`
- `POST /predict`
- `GET /stream/pull`
- `GET /alerts`
- `GET /cases`
- `GET /metrics`

## 5. Monitoring and Alerts

Prometheus rules now include:
- API 5xx and p95 latency checks
- prediction traffic anomaly checks
- review queue backlog check (`review_queue_size`)
- false-positive spike check (`false_positive_total`)

## 6. Health and Readiness Notes

Container health checks currently defined:
- API health check on `/health`
- Frontend health check on `/index.html`

Operational readiness caveats:
- case persistence is in-memory; data is lost on restart
- auth/RBAC not implemented for case mutation endpoints

## 7. Recommended Production Hardening Before Go-Live

- Replace in-memory case repository with durable DB
- Add auth/RBAC and endpoint-level authorization
- Add TLS termination and secrets management
- Add backup and retention for case records
- Add load/performance testing under expected peak traffic

## 8. Conclusion

Deployment configuration is structurally valid and test-backed at code level.

Final production readiness is conditional on hardening items above and full live-stack runtime verification.
