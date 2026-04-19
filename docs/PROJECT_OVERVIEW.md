# Project Overview

## Real-Time Banking Transaction Fraud Detection and Decision Support System

Repository: Final_Project_DMM501_Group1
Program: DDM501 Final Project
Date: 2026-04-18

## Executive Summary

This repository now implements a decision-support workflow, not only a classifier endpoint.

Implemented runtime flow:
Incoming Transaction -> Input Validation -> Feature Preparation -> ML Risk Scoring -> Decision Recommendation -> Reason Code Generation -> Alert/Case Creation (for REVIEW/HIGH) -> Case Lifecycle Tracking -> Timeline Events -> Monitoring Metrics -> Frontend Visualization

## What Is Actually Implemented

- ML scoring API with strict input contract checks
- Decision tiering (`LOW`, `REVIEW`, `HIGH`)
- Decision recommendations (`ALLOW`, `STEP_UP_AUTH`, `MANUAL_REVIEW`, `HOLD`, `BLOCK`)
- Reason-code engine (demo-level heuristic + policy-derived)
- Alert APIs and case APIs with lifecycle updates
- Timeline endpoint for case investigation history
- Frontend integration for queue, status transitions, and timeline
- Operational metrics (alerts/cases/status/queue) and additional Prometheus rules
- Automated tests covering lifecycle workflow

## Honest Classification

- Fully implemented:
  - scoring, decision policy, alerts/cases/timeline APIs, frontend workflow integration, tests
- Partially implemented:
  - Grafana panel coverage for newly added operational metrics
- Demo-level simulated:
  - in-memory case persistence (non-durable)
- Proposed future enhancement:
  - durable DB persistence, auth/RBAC, retraining feedback loop, drift automation

## Model and Score Framing

Current deployed artifact metadata indicates:
- model type: logistic_regression_pipeline
- selected model: logistic_regression
- score semantics: risk_score_uncalibrated
- threshold policy loaded from `artifacts/models/model_info.json`

Important:
`risk_score` is an uncalibrated ranking signal and is not claimed as calibrated fraud probability.

## API Surface Summary

Core endpoints:
- `POST /predict`
- `GET /health`
- `GET /metrics`
- `GET /stream/pull`

Operational endpoints:
- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`

## Frontend Scope

The frontend now supports:
- alert queue view
- case table with lifecycle status and decision recommendation
- case detail panel with reason codes
- timeline visualization
- analyst actions: move to review, confirm fraud, mark false positive, resolve

## Monitoring Scope

Technical metrics:
- request counts
- latency histograms
- prediction/tier/action metrics

Operational metrics:
- `fraud_alerts_total`
- `fraud_cases_total`
- `fraud_case_status_total`
- `decision_recommendations_total`
- `risk_tier_total`
- `confirmed_fraud_total`
- `false_positive_total`
- `review_queue_size`

## Verification State

Verified now:
- Full test suite passed (`30 passed`)
- Integration tests include lifecycle and timeline workflow
- Docker Compose configuration renders successfully

Not verified now:
- Full runtime `docker compose up --build` stack execution in this session
- Manual browser walkthrough after latest UI code changes

## Key Documents

- `README.md`
- `ARCHITECTURE.md`
- `SYSTEM_SPECIFICATION_DOCUMENT.md`
- `RESPONSIBLE_AI.md`
- `DEPLOYMENT_REPORT.md`
- `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`

## Feature Status Matrix

| Feature | Backend Status | Frontend Status | Deployment Status | Overall |
|---|---|---|---|---|
| Fraud scoring | Implemented | Integrated | Ready | Fully implemented |
| Decision recommendations | Implemented | Integrated | Ready | Fully implemented |
| Reason codes | Implemented (heuristic) | Integrated | Ready | Partially implemented |
| Alert queue | Implemented | Integrated | Ready | Fully implemented |
| Case lifecycle | Implemented | Integrated | Ready | Fully implemented |
| Investigation timeline | Implemented | Integrated | Ready | Fully implemented |
| Durable persistence | Not implemented | N/A | Not ready | Proposed |
| Auth/RBAC | Not implemented | Not implemented | Not ready | Proposed |
| Retraining feedback loop | Not implemented | N/A | Not ready | Proposed |
