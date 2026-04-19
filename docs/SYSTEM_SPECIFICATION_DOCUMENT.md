# System Specification Document

System name:
Real-Time Banking Transaction Fraud Detection and Decision Support System

Version:
2.0

Date:
2026-04-18

Repository:
Final_Project_DMM501_Group1

## 1. Purpose

This specification defines the operational, technical, and model requirements for a banking fraud decision-support platform.

The system is designed to support:
- fraud risk scoring
- decision recommendation
- alert generation
- case lifecycle tracking
- analyst workflow visibility
- monitoring and deployment readiness

## 2. Design Principles

- Separate risk scoring from decision policy.
- Avoid overclaiming score semantics.
- Keep implementation, UI, and documentation consistent.
- Distinguish implemented vs simulated vs proposed capabilities.

## 3. System Context and Actors

Actors:
- Customer
- Banking Channel (mobile app, internet banking, API, ATM/branch inputs)
- Fraud API
- Fraud Scoring Engine
- Decision Policy Engine
- Fraud Analyst
- Monitoring/Ops
- ML/Model Ops

## 4. Functional Requirements

### FR-A. Scoring and Validation
- FR-1: The system shall score incoming transactions with a deployed ML model.
- FR-2: The system shall validate feature vector length against model metadata.
- FR-3: The system shall reject requests that provide both `features` and `features_by_name`.
- FR-4: The system shall reject non-finite numeric feature values.
- FR-5: The system shall support optional transaction metadata (`transaction_id`, `timestamp`, `amount`, `channel`, `metadata`).
- FR-6: The system shall return model metadata (`model_version`, `model_type`, `score_semantics`).

### FR-B. Decision Support
- FR-7: The system shall assign risk tiers (`LOW`, `REVIEW`, `HIGH`).
- FR-8: The system shall return decision recommendations (`ALLOW`, `STEP_UP_AUTH`, `MANUAL_REVIEW`, `HOLD`, `BLOCK`).
- FR-9: The system shall return backward-compatible legacy action labels.
- FR-10: The system shall return reason codes for scored transactions.

### FR-C. Alert and Case Workflow
- FR-11: The system shall create alerts/cases for `REVIEW` and `HIGH` tiers.
- FR-12: The system shall assign unique `alert_id` and `case_id`.
- FR-13: The system shall expose alert list and detail endpoints.
- FR-14: The system shall expose case list and detail endpoints.
- FR-15: The system shall support case status transitions.
- FR-16: The system shall support case resolution actions.
- FR-17: The system shall expose case timeline events.

### FR-D. Frontend and Analyst Flow
- FR-18: The frontend shall display an alert queue.
- FR-19: The frontend shall show decision recommendation per case.
- FR-20: The frontend shall show reason codes per case.
- FR-21: The frontend shall show lifecycle status per case.
- FR-22: The frontend shall display investigation timeline events.
- FR-23: The frontend shall execute analyst status transitions via API.

### FR-E. Monitoring and Operations
- FR-24: The system shall expose Prometheus metrics.
- FR-25: The system shall expose operational metrics for alerts/cases/status/review queue.
- FR-26: The system shall include Prometheus alert rules for API health and queue behavior.

### FR-F. Deployment and Testing
- FR-27: The system shall support Docker Compose deployment.
- FR-28: The system shall include automated tests for scoring and case workflow endpoints.
- FR-29: The system shall include health checks for API and frontend containers.

## 5. Non-Functional Requirements

### NFR-Performance
- NFR-1: API single-request scoring should remain low latency under normal demo load.
- NFR-2: Metrics collection must not block request handling.

### NFR-Reliability
- NFR-3: API shall return deterministic validation errors for invalid contracts.
- NFR-4: Case lifecycle endpoints shall maintain coherent status state in repository.

### NFR-Maintainability
- NFR-5: Backend shall be modularized into services and repositories.
- NFR-6: API schemas shall define contracts explicitly.

### NFR-Observability
- NFR-7: Request, tier, decision, alert, case status, and queue metrics shall be observable.
- NFR-8: Alert rules shall include technical and operational conditions.

### NFR-Scalability
- NFR-9: Current persistence is in-memory and is not horizontally durable.
- NFR-10: Durable persistence is required before production scale-out.

### NFR-Security
- NFR-11: Authentication/RBAC is required for production and currently not implemented.
- NFR-12: Internal labeled dataset endpoint shall require token.

### NFR-Usability
- NFR-13: Analyst UI must surface queue, status, and timeline context with minimal navigation.

## 6. Business Requirements

- BR-1: Reduce fraud loss through earlier high-risk intervention.
- BR-2: Reduce false positives through explicit case outcomes and tracking.
- BR-3: Support operational review with queue and lifecycle controls.
- BR-4: Improve decision visibility for analysts and auditors.
- BR-5: Reduce response time by mapping model scores to direct recommendations.

## 7. Model Requirements

- MR-1: The model pipeline shall handle class imbalance using fraud-appropriate metrics.
- MR-2: Feature schema shall be preserved and validated at inference.
- MR-3: Threshold metadata shall be stored and loaded from artifacts.
- MR-4: Score semantics shall be exposed as uncalibrated unless calibration is implemented and validated.
- MR-5: Policy mapping shall be explicit and deterministic.

## 8. API Contract Summary

### Required Endpoints
- `POST /predict`
- `GET /health`
- `GET /metrics`
- `GET /stream/pull`
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`

## 9. Implementation Classification

| Capability | Classification | Notes |
|---|---|---|
| Risk scoring API | Fully implemented | Artifact-backed model loading and inference |
| Decision recommendations | Fully implemented | Tier-aware and channel/amount aware policy |
| Reason codes | Partially implemented | Demo-level heuristic reasoning, not causal |
| Alert/case workflow | Fully implemented | In-memory repository |
| Timeline | Fully implemented | Event history endpoint and frontend view |
| Durable persistence | Proposed | DB-backed repository not implemented |
| Security hardening | Proposed | Auth/RBAC/rate limiting not implemented |
| Feedback retraining loop | Proposed | No automated closed-loop retraining yet |

## 10. Deployment Requirements

- DR-1: Docker Compose config shall render successfully.
- DR-2: API shall expose `/health` and `/metrics`.
- DR-3: Frontend shall connect to API base URL and render workflow data.
- DR-4: Prometheus shall load alert rules.

## 11. Verification Snapshot

Verified in this environment:
- Full pytest suite passed (`30 passed`).
- Integration workflow includes alert/case lifecycle and timeline.
- Compose configuration validation passed.

Not verified in this environment:
- Full live stack runtime via `docker compose up --build` in this execution window.
- Manual browser E2E walkthrough after frontend update.

## 12. References

- `src/api/main.py`
- `src/api/schemas.py`
- `src/services/`
- `src/repositories/`
- `src/monitoring/metrics.py`
- `deployment/prometheus/alerts.yml`
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`
