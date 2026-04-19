# Runtime Verification Checklist (Live Stack)

Date: 2026-04-18
Scope: Full Docker stack runtime validation with endpoint and UI evidence
Workspace: Final_Project_DMM501_Group1

Run note:
- Host port 5432 was already allocated on this machine.
- Stack was launched with `POSTGRES_PORT=5433`.
- Internal API-to-PostgreSQL connectivity remains `postgres:5432` inside Docker network.

## 1) Stack Boot and Service Health

- [x] Docker Compose services are running.
  - Evidence: `docker compose -f deployment/docker-compose.yml ps`
  - Result: all six services up (`postgres`, `api`, `frontend`, `prometheus`, `grafana`, `mlflow`), with `api`, `postgres`, and `frontend` healthy.

- [x] API health endpoint is reachable and reports loaded model metadata.
  - Evidence: `GET http://localhost:8000/health`
  - Result snippet:
    - `status=ok`
    - `model_loaded=true`
    - `model_version=creditcard-production-v1`
    - `threshold_review=0.7391262534904675`
    - `threshold_high=0.9999047447184487`
    - `score_semantics=risk_score_uncalibrated`
    - `review_queue_size=0`
    - `case_repository_mode=postgresql`

## 2) Core Endpoint Reachability

- [x] API documentation endpoint is reachable.
  - Evidence: `GET http://localhost:8000/docs`
  - Result: `HTTP 200`

- [x] Frontend entrypoint is reachable.
  - Evidence: `GET http://localhost:8082/index.html`
  - Result: `HTTP 200`

- [x] MLflow UI endpoint is reachable.
  - Evidence: `GET http://localhost:5000/`
  - Result: `HTTP 200`

- [x] Auth enforcement is active on protected case endpoints.
  - Evidence:
    - `GET /cases?limit=1` without token -> `cases_no_auth=401`
    - `GET /cases?limit=1` with `Authorization: Bearer viewer-token` -> `cases_viewer=200`

## 3) Deterministic Alert/Case Lifecycle Validation

- [x] A guaranteed high-risk transaction creates alert/case through `POST /predict`.
  - Method:
    - Loaded `artifacts/models/final_model.joblib`.
    - Scored `data/archive/creditcard.csv` locally.
    - Selected max-score row (`argmax`) to force HIGH-risk path.
  - Evidence output:
    - `predict_status=200`
    - `risk_tier=HIGH`
    - `decision_recommendation=HOLD`
    - `alert_id=ALERT-BEC604E831DA`
    - `case_id=CASE-8BA7673614EA`

- [x] RBAC blocks unauthorized role transitions.
  - Evidence:
    - `POST /cases/{case_id}/resolve` with `viewer-token` -> `viewer_resolve_status=403`
    - Detail: `Insufficient role. Required one of: ['admin', 'analyst']`

- [x] Alert status update workflow works.
  - Evidence: `POST /alerts/{alert_id}/status` with `case_status=IN_REVIEW`
  - Result:
    - `in_review_status=200`
    - `in_review_case_status=IN_REVIEW`

- [x] Case resolution workflow works.
  - Evidence: `POST /cases/{case_id}/resolve` with `resolution=FALSE_POSITIVE`
  - Result:
    - `resolve_status=200`
    - `resolve_case_status=FALSE_POSITIVE`

- [x] Timeline endpoint includes expected lifecycle events.
  - Evidence: `GET /cases/{case_id}/timeline`
  - Result (`timeline_status=200`) events:
    - `TRANSACTION_RECEIVED`
    - `RISK_SCORED`
    - `FLAGGED`
    - `ALERT_CREATED`
    - `CASE_ASSIGNED`
    - `INVESTIGATION_STARTED`
    - `FALSE_POSITIVE`
    - `CASE_CLOSED`

## 4) Security Hardening Evidence

- [x] Token authentication and role mapping are active in runtime.
  - Evidence:
    - Anonymous request to protected endpoint fails with `401`.
    - Viewer role can read queue endpoints (`200`) but cannot resolve cases (`403`).
    - Analyst role can update status and resolve cases (`200`).

- [x] Audit trail endpoint is restricted and records security-relevant events.
  - Evidence:
    - `GET /audit/events?limit=80` with `admin-token` -> `audit_status=200`
    - `audit_total=5`
    - Head events include:
      - `CASE_RESOLVED`
      - `ALERT_STATUS_UPDATED`
      - `RBAC_FORBIDDEN`
      - `CASE_CREATED_FROM_PREDICTION`
      - `AUTH_MISSING_TOKEN`

- [x] Rate limiting middleware is active on protected endpoints.
  - Evidence: response headers on `GET /cases?limit=1` include:
    - `x-ratelimit-limit: 240`
    - `x-ratelimit-remaining: 234`
    - `x-ratelimit-window-seconds: 60`

## 5) Monitoring and Alerting Evidence

- [x] Prometheus readiness endpoint is healthy.
  - Evidence: `GET http://localhost:9090/-/ready`
  - Result: `Prometheus Server is Ready.`

- [x] Grafana health endpoint is healthy.
  - Evidence: `GET http://localhost:3000/api/health`
  - Result snippet:
    - `database=ok`
    - `version=11.1.0`

- [x] Prometheus alert rules are loaded, including fraud workflow rules.
  - Evidence: `GET http://localhost:9090/api/v1/rules`
  - Loaded alert rule names:
    - `FraudApiHigh5xxErrorRate`
    - `FraudApiHighP95Latency`
    - `FraudApiPredictionRateTooHigh`
    - `FraudApiPredictionRateTooLow`
    - `FraudFalsePositiveSpike`
    - `FraudReviewQueueBacklogHigh`

- [x] Operational metrics are emitted at runtime.
  - Evidence: `GET http://localhost:8000/metrics`
  - Confirmed metric series:
    - `decision_recommendations_total`
    - `fraud_alerts_total`
    - `fraud_cases_total`
    - `fraud_case_status_total`
    - `false_positive_total`
    - `review_queue_size`

## 6) UI Evidence (Served Frontend)

- [x] Fraud operations UI sections/controls are present in served HTML.
  - Evidence source: `GET http://localhost:8082/index.html`
  - Confirmed markers:
    - `Fraud Alert Queue`
    - `Check &amp; Handle Queue`
    - `Investigation Timeline`
    - `caseConfirmFraudBtn`
    - `caseFalsePositiveBtn`
    - `caseResolveBtn`

## 7) Regression Test Evidence

- [x] Full Python test suite passes after PostgreSQL migration fix.
  - Evidence: `python -m pytest -q`
  - Result: `33 passed, 11 warnings`

## 8) Verdict

- [x] Runtime verification passed for the current live stack.
- Notes:
  - Persistence is now PostgreSQL-backed (`case_repository_mode=postgresql`).
  - Security hardening is active at runtime (token auth, RBAC, rate limiting, audit trail).
  - Environment-specific launch override used: host `POSTGRES_PORT=5433` due local port 5432 conflict.
