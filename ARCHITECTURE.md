# Architecture

This document describes the current implemented architecture of the Real-Time Banking Fraud Detection and Decision Support System.

## 1. Architectural Intent

The system separates ML scoring from decision operations:
- Risk scoring layer: model inference returns uncalibrated ranking score.
- Decision policy layer: maps score to tier and recommendation.
- Case operations layer: creates and tracks alerts/cases for analyst workflow.

## 2. Actor and Component View

```mermaid
flowchart LR
  CUSTOMER[Customer] --> CHANNEL[Banking Channel]
  CHANNEL --> API[Fraud API]
  API --> SCORE[Scoring Service]
  SCORE --> POLICY[Decision Policy Service]
  POLICY --> REASON[Reason Code Service]
  REASON --> CASE[Case Service + In-Memory Repository]

  CASE --> ANALYST[Fraud Analyst]
  API --> UI[Frontend Dashboard]
  CASE --> UI

  API --> PROM[Prometheus]
  PROM --> GRAF[Grafana]
```

## 3. Runtime Transaction Flow

```mermaid
sequenceDiagram
  participant CH as Banking Channel
  participant API as API /predict
  participant M as Loaded Model
  participant P as Decision Policy
  participant R as Reason Engine
  participant C as Case Service

  CH->>API: POST /predict
  API->>API: Validate request + feature contract
  API->>M: predict_proba
  M-->>API: risk_score (uncalibrated)
  API->>P: derive tier + recommendation
  API->>R: generate reason codes
  API->>C: create alert/case if REVIEW or HIGH
  API-->>CH: decision-support response
```

## 4. Case Lifecycle

```mermaid
flowchart TD
  NEW[NEW] --> QUEUED[QUEUED]
  QUEUED --> INREV[IN_REVIEW]
  INREV --> ESC[ESCALATED]
  INREV --> CF[CONFIRMED_FRAUD]
  INREV --> FP[FALSE_POSITIVE]
  INREV --> BLK[BLOCKED]
  INREV --> REL[RELEASED]
  CF --> RES[RESOLVED]
  FP --> RES
  BLK --> RES
  REL --> RES
```

## 5. Timeline Event Model

Timeline events recorded per case include:
- TRANSACTION_RECEIVED
- RISK_SCORED
- FLAGGED
- ALERT_CREATED
- CASE_ASSIGNED
- INVESTIGATION_STARTED
- CONFIRMED_FRAUD
- FALSE_POSITIVE
- CASE_CLOSED

## 6. Module Layout

- API and schemas:
  - `src/api/main.py`
  - `src/api/schemas.py`
- Service layer:
  - `src/services/scoring_service.py`
  - `src/services/decision_service.py`
  - `src/services/reason_code_service.py`
  - `src/services/case_service.py`
- Repository layer:
  - `src/repositories/in_memory_case_repository.py`
- Monitoring:
  - `src/monitoring/metrics.py`

## 7. API Surface

### Scoring and metadata
- `POST /predict`
- `GET /health`
- `GET /stream/pull`
- `GET /metrics`

### Case operations
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`

## 8. Monitoring Design

Metrics include both technical and operational views:
- `api_requests_total`
- `api_request_latency_seconds`
- `fraud_predictions_total`
- `risk_tier_total`
- `decision_recommendations_total`
- `fraud_alerts_total`
- `fraud_cases_total`
- `fraud_case_status_total`
- `review_queue_size`
- `confirmed_fraud_total`
- `false_positive_total`

Prometheus alert rules include:
- API 5xx rate
- API p95 latency
- Prediction rate low/high anomalies
- Review queue backlog
- False-positive spike

## 9. Deployment Topology

```mermaid
flowchart LR
  FE[frontend:8082] --> API[api:8000]
  API --> PROM[prometheus:9090]
  PROM --> GRAF[grafana:3000]
  API --> MLF[mlflow:5000]
  ART[artifacts volume] --> API
```

## 10. Honest Limitations

Implemented but demo-level:
- Alert/case persistence is in-memory and process-bound.

Not implemented yet:
- Durable DB-backed case store
- Auth/RBAC and audit trails
- Streaming bus and exactly-once semantics
- Drift detection and retraining orchestration

## 11. Source of Truth

For the full audit, gap matrix, and staged roadmap, see:
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`
