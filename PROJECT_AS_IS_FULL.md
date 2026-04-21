<!-- markdownlint-disable MD013 MD033 MD025 MD041 MD036 -->

# MASTER REVIEW “AS-IS” — Final_Project_DMM501_Group1

Ngày tạo: **2026-04-21**  
Mục tiêu: **1 file `.md` duy nhất** mô tả *toàn bộ những gì project đang có và đang là*, theo kiểu **master reviewer**: inventory + hành vi hệ thống + mapping file/module + cấu hình + deploy + monitoring + test + *findings/gaps/risks*.

---

## 0) Executive Snapshot (đọc 2 phút)

Project này là một **Fraud Decision-Support System** end-to-end:

- **ML**: pipeline training + benchmark + chọn model; xuất artifacts (model + metadata + figures + reports).
- **Backend (FastAPI)**: `/predict` trả `risk_score` (uncalibrated), map `risk_tier` & `decision_recommendation`, tạo `alert` + `case` + `timeline` khi REVIEW/HIGH; có `/stream/pull` mô phỏng traffic.
- **Workflow Ops**: list/update status/resolve case; audit events.
- **Frontend**: dashboard live + review view; kết nối API bằng token.
- **Observability**: Prometheus metrics + alert rules; Grafana dashboards; MLflow runtime tracking (API ghi metrics vào MLflow) + exporter để Prometheus scrape.
- **Deploy**: Docker Compose (Postgres + API + frontend + Prometheus + Grafana + MLflow).
- **CI**: GitHub Actions (pytest unit/integration + coverage gate, build images, validate compose).

Điểm cốt lõi: hệ thống không chỉ “model predict”, mà là **score → policy → workflow → monitoring**.

---

## 1) Trạng thái workspace (as-is) & generated artifacts

### 1.1 Workspace có nhiều file artifacts sinh ra (và đang “dirty”)

Trong workspace hiện tại, có các thay đổi chưa commit (điển hình do chạy pipeline + build report):

- `artifacts/**` có rất nhiều file **bị modify** (figures `.png`, reports `.json`, `.csv`, `mlflow.db`, `model_info.json`, `.joblib`…)
- có thêm folder versioning: `artifacts/models/versions/`
- có thêm report PDF: `latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf`

Điều này **bình thường** với repo demo kiểu “artifact-backed”, nhưng khi nộp/đóng gói cần quyết định:

- có commit artifacts vào git không (để “evidence-based”), hay chỉ commit code + script sinh artifacts.

### 1.2 Những thư mục “không phải source”

Repo chứa/hiện hữu trên disk các thư mục như `.venv/`, `.pytest_cache/`, `__pycache__/`.  
Master review note:

- các thư mục này thường **không nên commit** (tuỳ repo hiện tại đang quản lý bằng git hay chỉ là workspace local).

---

## 2) Inventory repo (top-level) — file-by-file (có note)

### 2.1 Top-level files

- `README.md` — overview + quick start + links ảnh + deploy notes.
- `MASTER_REPORT.md` — report dài (Markdown) có mermaid diagrams + requirements + mapping.
- `ARCHITECTURE.md` — architecture narrative + mermaid diagrams + endpoint list.
- `Makefile` — shortcut chạy test + run api.
- `requirements.txt` — dependency list (không pin version).
- `.env.example` — env mẫu (có dấu hiệu “outdated”, xem phần Findings).
- `rune2e.sh` — script interactive chạy E2E local (train → run api → run frontend → build docker).
- `scripts/deploy_full_stack.sh` — build artifacts rồi chạy Docker Compose full stack.
- `PROJECT_AS_IS_FULL.md` — file này.

### 2.2 Source code

- `src/api/main.py` — FastAPI app + endpoints + orchestration scoring/decision/workflow/metrics/audit.
- `src/api/schemas.py` — Pydantic request/response schema contracts.
- `src/models/loader.py` — load model từ `MODEL_PATH` hoặc default `artifacts/models/final_model.joblib`.
- `src/services/scoring_service.py` — validate features + `predict_proba`.
- `src/services/decision_service.py` — policy engine: tier + recommendation.
- `src/services/reason_code_service.py` — heuristic reason codes + summary.
- `src/services/case_service.py` — wrapper tạo/list/update case/alert/timeline/audit qua repository.
- `src/repositories/*` — in-memory repo + SQL repo + migrations + lifecycle mapping + env factory.
- `src/security/*` — auth token/role + audit append + rate limiting middleware.
- `src/monitoring/*` — Prometheus metrics + MLflow runtime tracker.
- `src/pipelines/*` — training pipelines (2 hướng: `train_pipeline` và `run_model_workflow`).
- `src/streaming/simulator.py` — simulator tạo event stream (burst + attack window).
- `src/data/*` — dataset loading + dataset sampling utilities.
- `src/features/*` — preprocess (identity reshape) + random feature generator.

### 2.3 Frontend

- `frontend/index.html` — UI shell (Dashboard + Review/Handle).
- `frontend/styles.css` — styling.
- `frontend/app.js` — app logic: poll health, stream loop, render feed + case queue.
- `frontend/api-client.js` — REST client với shape assertions.
- `frontend/ui.js` — UI rendering helpers.
- `frontend/demo-data.js` — inline sample data + random generator cho demo mode.
- `frontend/screenshot_server.py` — static server có endpoint `/__delay` phục vụ chụp screenshot reproducible.
- `frontend/package-lock.json` — file Node lock rất nhỏ; master review note: **không thấy `package.json`** → khả năng “leftover”.

### 2.4 Deployment / Observability

- `deployment/docker-compose.yml` — full stack services.
- `deployment/api/Dockerfile` — build API image.
- `deployment/frontend/Dockerfile` — serve frontend bằng `python -m http.server`.
- `deployment/mlflow/Dockerfile` — MLflow server + exporter dependencies.
- `deployment/mlflow/exporter.py` — exporter Prometheus metrics cho MLflow.
- `deployment/prometheus/prometheus.yml` — scrape jobs.
- `deployment/prometheus/alerts.yml` — alert rules.
- `deployment/grafana/provisioning/*` — datasource + dashboards providers.
- `deployment/grafana/dashboards/fraud_api.json` — dashboard cho API.
- `deployment/grafana/dashboards/mlflow.json` — dashboard cho MLflow exporter.
- `deployment/.env.example` + `deployment/.env` — port override cho compose.

### 2.5 Artifacts (generated / evidence)

- `artifacts/models/final_model.joblib` — model artifact chính (được compose mount vào API container).
- `artifacts/models/model_info.json` — metadata + thresholds + score percentiles + metrics (source-of-truth runtime).
- `artifacts/figures/*.png` — EDA + model evaluation + UI screenshots.
- `artifacts/reports/*` — json/csv evidence + API example outputs.
- `artifacts/benchmarks/*` — tables threshold tuning + comparison.
- `artifacts/mlflow.db` — sqlite backend cho MLflow tracking (workflow).
- `artifacts/mlruns/**` — mlflow file-store (một phần).
- `artifacts/deploys/*.png` — deployment evidence screenshots.
- `artifacts/models/versions/**` — per-run “immutable copies” + run history (tạo bởi `src/models/versioning.py`).

---

## 3) Hành vi hệ thống (runtime) — end-to-end logic

### 3.1 Trạng thái model load (startup)

Trong `src/api/main.py` lifecycle:

- validate auth config (`validate_auth_configuration()`)
- load model: `maybe_load_model_from_env()`
  - nếu không set `MODEL_PATH`, fallback `artifacts/models/final_model.joblib`
- nếu model loaded: tạo `StreamSimulator` (dataset-based nếu tìm được dataset; không thì synthetic)
- tạo `CaseService` với repo theo env (`build_case_repository_from_env()`)

### 3.2 `POST /predict` (core endpoint)

File điều phối: `src/api/main.py` + schema: `src/api/schemas.py`

Flow:

1) RBAC: `require_roles(*READ_ROLES)` (viewer/analyst/admin)  
2) Nếu model chưa load → `503`  
3) Resolve features:
   - `features` **XOR** `features_by_name`
   - `features_by_name` chỉ dùng được khi metadata có `feature_columns`
4) Validate:
   - feature length khớp `loaded.n_features` (nếu có)
   - tất cả finite numbers (`validate_feature_vector`)
5) Score:
   - `score_transaction` → `predict_proba()[0][1]`
6) Normalize timestamp + amount:
   - amount có thể lấy từ request hoặc fallback từ feature (cột `Amount`/last)
7) Decision policy:
   - `decide_risk_action(score, threshold_review, threshold_high, amount, channel)`
8) Reason codes (heuristic):
   - `generate_reason_codes(...)` + `summarize_reason_codes`
9) Nếu tier ∈ {REVIEW, HIGH}:
   - tạo alert+case qua `CaseService.create_from_prediction(...)`
   - ghi metrics + audit events
10) Trả `PredictResponse` đầy đủ (tier + recommendation + reason + IDs + thresholds + model metadata)

### 3.3 `GET /stream/pull` (demo stream)

Purpose: mô phỏng stream traffic để dashboard chạy “real-time”.

- `StreamSimulator`:
  - burst traffic (TPS tăng) với xác suất
  - rare attack windows (fraud rate tăng)
  - nếu có dataset: sample fraud/legit theo strategy
  - nếu không có dataset: random features `generate_random_features`

`/stream/pull`:

- tạo events trong window `pace_ms` và giới hạn `max_events`
- scoring batch bằng model (vectorized)
- map policy + reason codes
- tạo alert/case khi REVIEW/HIGH (giống /predict)
- thêm `risk_percentile` nếu `model_info.json` có `score_percentiles` (0..100)

Master note: `/stream/pull` **có side-effect**: tạo alert/case + tăng metrics, giống như traffic thật.

---

## 4) API Surface (đầy đủ) + RBAC matrix

### 4.1 Endpoints (đọc từ `src/api/main.py`)

Public-ish:

- `GET /` → redirect `/docs`
- `GET /docs` (Swagger UI; do FastAPI)
- `GET /openapi.json`
- `GET /health`
- `GET /metrics`
- `GET /features/schema`
- `GET /features/random`

Scoring/stream:

- `POST /predict`
- `GET /stream/pull`

Workflow:

- `GET /alerts`
- `GET /alerts/{alert_id}`
- `POST /alerts/{alert_id}/status`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/status`
- `POST /cases/{case_id}/resolve`
- `GET /cases/{case_id}/timeline`

Audit:

- `GET /audit/events`

Dataset utilities:

- `GET /dataset/samples`
- `GET /internal/dataset/samples` (hidden khỏi OpenAPI; cần internal token)

### 4.2 RBAC matrix (as implemented)

Role constants: `src/security/auth.py`

- `READ_ROLES = ("viewer","analyst","admin")`
- `ANALYST_ROLES = ("analyst","admin")`
- `ADMIN_ROLES = ("admin",)`

Matrix:

| Endpoint | Roles |
|---|---|
| `GET /health` | public (không `Depends`), nhưng vẫn đi qua middleware rate-limit |
| `GET /metrics` | public |
| `GET /features/*` | public |
| `POST /predict` | READ |
| `GET /stream/pull` | READ |
| `GET /alerts`, `GET /cases` | READ |
| `POST /alerts/*/status`, `POST /cases/*/status`, `POST /cases/*/resolve` | ANALYST |
| `GET /audit/events` | ADMIN |
| `GET /dataset/samples` | READ |
| `GET /internal/dataset/samples` | READ + `INTERNAL_EVAL_TOKEN` header |

Master note: khi `API_AUTH_ENABLED=false`, `get_auth_context` trả role `"admin"` cho mọi request → demo-friendly nhưng **không an toàn** nếu exposed.

---

## 5) Config & Environment Variables (đầy đủ, as implemented)

### 5.1 Model load / scoring

Trong `src/models/loader.py`:

- `MODEL_PATH` — nếu set, load đúng path đó; nếu trống/không tồn tại → model không load.
- `MODEL_VERSION` — override `model_version` (traceability).
- `FRAUD_THRESHOLD` — backward-compat: override threshold_high nếu metadata không có threshold_high (hoặc nếu set thì vẫn được ưu tiên theo code).
- `REVIEW_THRESHOLD` — override `threshold_review` nếu hợp lệ (0..1 và <= threshold_high).

### 5.2 Data

Trong `src/data/samples.py`:

- `DATASET_CSV_PATH` — override dataset path (ưu tiên cao nhất cho sampling/stream nếu set).

### 5.3 Case persistence

Trong `src/repositories/factory.py`:

- `CASE_REPOSITORY_MODE`:
  - `auto` (default): dùng SQL nếu có DSN, không thì in-memory
  - `in_memory|memory|demo`
  - `postgres|postgresql|sql|database`
- `CASE_DB_URL` hoặc `DATABASE_URL`
- `CASE_DB_AUTO_MIGRATE` (default true)

### 5.4 Auth

Trong `src/security/auth.py`:

- `API_AUTH_ENABLED` (default false)
- `API_TOKENS` (format: `token:role,token:role,...`)

Headers:

- `Authorization: Bearer <token>` hoặc `X-API-Key: <token>`
- `X-Actor: <string>` (audit actor)

### 5.5 Rate limiting

Trong `src/security/rate_limit.py`:

- `RATE_LIMIT_ENABLED` (default false)
- `RATE_LIMIT_REQUESTS` (default 180)
- `RATE_LIMIT_WINDOW_SECONDS` (default 60)

Exempt paths: `/`, `/health`, `/metrics`, `/docs`, `/openapi.json`, `/redoc*`.

### 5.6 Streaming simulator

Trong `src/api/main.py` + `src/streaming/simulator.py`:

- `STREAM_SEED` (default 42)
- `STREAM_BASE_FRAUD_RATE` (default 0.0017) (nếu model metadata không có base rate)
- `STREAM_BASE_TPS` (default 1.2)
- `STREAM_BURST_TPS` (default 14.0)

### 5.7 CORS

Trong `src/api/main.py`:

- `CORS_ALLOW_ORIGINS`:
  - nếu có: allowlist theo CSV
  - nếu không: allow origin regex localhost/127.0.0.1 ports

### 5.8 MLflow runtime tracking (API → MLflow)

Trong `src/monitoring/mlflow_runtime_tracker.py`:

- `MLFLOW_RUNTIME_ENABLED` (default false)
- `MLFLOW_RUNTIME_TRACKING_URI` (compose set: `http://mlflow:5000`)
- `MLFLOW_RUNTIME_EXPERIMENT` (default `fraud-runtime-traffic`)
- `MLFLOW_RUNTIME_RUN_NAME` (default `api-online-traffic`)
- `MLFLOW_RUNTIME_LOG_EVERY` (default 20)

### 5.9 Internal dataset sampling

Trong `src/api/main.py`:

- `INTERNAL_EVAL_TOKEN` — nếu không set: `/internal/dataset/samples` trả 404.
- Header: `X-Internal-Token: <token>` (tên header param: `x_internal_token`)

---

## 6) ML: pipelines + artifacts + versioning (review sâu)

### 6.1 Hai pipeline chính

1) `src/pipelines/run_model_workflow.py` (full benchmark workflow, evidence-heavy)

- đọc `data/archive/creditcard.csv`
- EDA + schema checks + split train/val/test
- train baseline Logistic Regression (pipeline scaler+LR)
- train improved LightGBM + HP tuning (grid)
- threshold policy: **top-K rate** (review/high)
- chọn model dựa trên validation PR-AUC, tie-break recall ở REVIEW operating point
- final train trên train+val
- final evaluate trên test
- export:
  - `artifacts/figures/*.png`
  - `artifacts/benchmarks/*.csv`
  - `artifacts/reports/*.json`
  - `artifacts/models/final_model.joblib`
  - `artifacts/models/model_info.json` (có score percentiles 0..100)
  - MLflow local sqlite `artifacts/mlflow.db` (experiment: `fraud-detection-benchmark`)
  - versioning copy: `artifacts/models/versions/<model_version>/...`

2) `src/pipelines/train_pipeline.py` (training nhanh hơn / fallback)

- có thể train với CSV hoặc synthetic (`make_classification`)
- train baseline LR (scaled) + candidate RF + final model (LightGBM nếu có)
- tune thresholds theo “min precision, maximize recall” (không phải top-K)
- export `artifacts/model.joblib` (khác layout), `metrics_report.json`, `model_info.json`
- cũng gọi `register_model_version` để versioning.

### 6.2 Versioning layout (as implemented)

`src/models/versioning.py` tạo:

- `artifacts/models/versions/index.json`
- `artifacts/models/versions/<model_version>/model_info.json`
- `artifacts/reports/model_run_history.jsonl`
- `artifacts/reports/latest_model_run.json`

Mục tiêu: mỗi run có bản copy immutable model artifact + metadata + extra artifacts.

---

## 7) Model loading & metadata coupling — master findings (quan trọng)

### 7.1 Cách loader lấy metadata

`src/models/loader.py::_read_metadata()` tìm:

- cùng thư mục với model: `model_info.json`
- hoặc `<model_path>.metadata.json`

### 7.2 Finding: `MODEL_PATH=artifacts/models/improved_lightgbm.joblib` có thể đọc nhầm metadata

Trong `artifacts/models/` hiện có:

- `improved_lightgbm.joblib`
- `final_model.joblib`
- **1 file metadata chung**: `artifacts/models/model_info.json`

Nếu bạn set `MODEL_PATH=artifacts/models/improved_lightgbm.joblib`, loader sẽ đọc `artifacts/models/model_info.json` (vì cùng thư mục) → metadata/thresholds/model_type có thể **không khớp** với actual model đang load (tùy state artifacts).

=> Đây là điểm cần ghi rõ khi demo và khi đóng gói:  
**mỗi model artifact nên có metadata riêng** (ví dụ `improved_lightgbm.model_info.json`), hoặc loader phải map đúng.

### 7.3 Finding: `.env.example` có dấu hiệu outdated / inconsistent

`.env.example` đang set:

```
MODEL_PATH=artifacts/models/improved_lightgbm.joblib
FRAUD_THRESHOLD=0.14
MODEL_VERSION=lightgbm-production-v1
```

Trong khi Docker Compose (`deployment/docker-compose.yml`) dùng:

```
MODEL_PATH: /app/artifacts/models/final_model.joblib
MODEL_VERSION: creditcard-production-v1
```

=> Master note: cần thống nhất “official deploy path” và “official model”.

---

## 8) Workflow Ops: Alert/Case/Timeline/Audit — storage modes

### 8.1 In-memory repository (demo)

File: `src/repositories/in_memory_case_repository.py`

- lưu alerts/cases/audit_events trong RAM
- timeline stored inline trong case record
- `review_queue_size` tính theo status ∈ `ACTIVE_REVIEW_STATUSES`
- update status sẽ append timeline event theo mapping `status_to_event`

### 8.2 SQL repository (Postgres/SQLAlchemy)

File: `src/repositories/sql_case_repository.py`

- auto migrate (default) chạy SQL files trong `src/repositories/migrations/`
- schema file: `src/repositories/migrations/001_case_lifecycle.sql`
  - tables: `alerts`, `cases`, `case_timeline`, `audit_events`
  - JSON được lưu dạng `TEXT` (serialized JSON)

Master note:

- Schema không dùng FK constraints (đơn giản; demo OK).
- `features_json` có thể lớn; cần cân nhắc trong production.

---

## 9) Security review (as-is)

### 9.1 Auth model

File: `src/security/auth.py`

- nếu `API_AUTH_ENABLED=false`: role luôn `"admin"` (mọi endpoint protected đều pass).
- nếu bật: cần `API_TOKENS` hợp lệ (token:role,...).
- token parsing hỗ trợ `Authorization: Bearer` hoặc `X-API-Key`.

### 9.2 Rate limiting review

File: `src/security/rate_limit.py`

- sliding window limiter in-memory (per token hoặc per IP)
- không persist; restart là reset.
- key `token:<token>` lưu raw token trong memory key.

Master note:

- demo OK; production nên hash token, và dùng store distributed (Redis) nếu multi-instance.

### 9.3 Audit logging review

File: `src/security/audit.py`

- audit event “best effort”, swallow exception, không break request.
- audit storage nằm trong repository (in-memory hoặc SQL table `audit_events`).

---

## 10) Monitoring / Observability review (as-is)

### 10.1 Prometheus metrics (API)

File: `src/monitoring/metrics.py`

Nhóm metrics:

- HTTP: `api_requests_total{endpoint,method,http_status}`, `api_request_latency_seconds`
- scoring: `fraud_predictions_total{tier}`, `risk_tier_total{tier}`, `fraud_actions_total{action}`, `decision_recommendations_total{decision}`
- workflow: `fraud_alerts_total{tier}`, `fraud_cases_total{status}`, `fraud_case_status_total{status}`, `review_queue_size`
- outcomes: `confirmed_fraud_total`, `false_positive_total`
- aggregates: `risk_scores_sum`, `risk_scores_count`

### 10.2 Prometheus scrape + rules

Files:

- `deployment/prometheus/prometheus.yml`:
  - scrape `api:8000/metrics`
  - scrape `mlflow:5001/metrics`
- `deployment/prometheus/alerts.yml`:
  - 5xx rate
  - p95 latency
  - prediction rate too low/high
  - review queue backlog
  - false positive spike

### 10.3 Grafana provisioning + dashboards

Files:

- datasource: `deployment/grafana/provisioning/datasources/datasource.yml` (Prometheus)
- provider: `deployment/grafana/provisioning/dashboards/dashboards.yml`
- dashboards:
  - `deployment/grafana/dashboards/fraud_api.json`
  - `deployment/grafana/dashboards/mlflow.json`

### 10.4 MLflow runtime tracking (API → MLflow)

`src/monitoring/mlflow_runtime_tracker.py`:

- API ghi counters vào MLflow run (experiment: `fraud-runtime-traffic`)
- flush theo `MLFLOW_RUNTIME_LOG_EVERY`
- nếu MLflow unreachable: tracker drop updates (không crash)

MLflow exporter:

- `deployment/mlflow/exporter.py` expose metrics:
  - mlflow server reachability + probe latency
  - db size + filesystem space
  - experiments/runs count

---

## 11) Frontend review (as-is)

### 11.1 UI/UX structure

Files:

- `frontend/index.html` — 2 tabs:
  - Dashboard: stream + feed + chart + alert queue
  - Check & Handle: review/filter cases + case detail + actions
- `frontend/styles.css` — dark modern UI.

### 11.2 API integration

File: `frontend/api-client.js`

- normalize base url
- set headers:
  - `Authorization: Bearer <apiKey>`
  - `X-Actor`
- assert response shapes để fail fast khi backend thay contract.

### 11.3 Demo data modes

File: `frontend/demo-data.js`

- `INLINE_REAL_SAMPLES` (3 sample vectors 30 features)
- random generator realistic-ish:
  - time cursor + jitter
  - V1..V28 normal + heavy tail occasional
  - Amount log-normal + stress event

### 11.4 Screenshot server

File: `frontend/screenshot_server.py`

- static server + endpoint `/__delay?ms=...` trả 1x1 gif và sleep để chờ UI render trước khi chụp.

Master note:

- `frontend/package-lock.json` có nhưng không có `package.json` → có thể xoá hoặc bổ sung cho rõ.

---

## 12) DevOps / Deploy (Docker Compose) — review

### 12.1 Compose services

File: `deployment/docker-compose.yml`

- `postgres` (5432 trong container; host port `POSTGRES_PORT`)
- `api` (FastAPI):
  - mount `../artifacts:/app/artifacts`
  - `CASE_REPOSITORY_MODE=postgres`
  - `CASE_DB_URL=postgresql+psycopg://fraud:fraud@postgres:5432/fraud_ops`
  - auth enabled + tokens configured
  - rate limit enabled
  - MLflow runtime enabled, tracking uri `http://mlflow:5000`
- `frontend` (HTTP server)
- `mlflow` (server + exporter)
- `prometheus`
- `grafana`

### 12.2 Dockerfiles

- `deployment/api/Dockerfile`: python:3.11-slim + curl, pip install requirements, copy `src/`.
- `deployment/frontend/Dockerfile`: python:3.11-slim + curl, copy `frontend/`, run `python -m http.server`.
- `deployment/mlflow/Dockerfile`: python:3.11-slim, install `mlflow` + `prometheus_client`, copy exporter.

### 12.3 Local ports override

- `deployment/.env.example` (defaults)
- `deployment/.env` (as-is trong workspace đang set `POSTGRES_PORT=5433` để tránh conflict)

### 12.4 Deploy scripts

- `scripts/deploy_full_stack.sh`: build artifacts trên host → `docker compose up -d --build` → wait health → optional logs.
- `rune2e.sh`: interactive local E2E (có option download dataset bằng Kaggle CLI; nếu thiếu dataset sẽ fallback synthetic fast mode).

---

## 13) CI/CD review (GitHub Actions)

Files:

- `.github/workflows/ci.yml`
  - setup python 3.11
  - install deps
  - run unit tests (`tests/unit`, `tests/data`)
  - run integration tests (`tests/integration`)
  - coverage gate `--cov-fail-under=80`
- `.github/workflows/docker.yml`
  - docker build api/frontend
  - validate compose config

---

## 14) Test coverage review (as-is)

Test suite inventory:

- Unit:
  - `tests/unit/test_ids.py`
  - `tests/unit/test_preprocess.py`
  - `tests/unit/test_loader_and_scoring.py`
  - `tests/unit/test_reason_code_service.py`
- Data:
  - `tests/data/test_samples.py`
  - `tests/data/test_data_quality_placeholder.py` (placeholder)
- Integration (ASGI client):
  - `tests/integration/test_api_health.py`
  - `tests/integration/test_api_predict_happy_path.py`
  - `tests/integration/test_api_predict_no_model.py`
  - `tests/integration/test_api_stream_pull.py`
  - `tests/integration/test_api_alert_case_workflow.py`
  - `tests/integration/test_api_dataset_samples.py`
  - `tests/integration/test_api_random_features.py`
  - `tests/integration/test_api_security.py`
  - `tests/integration/test_api_sql_persistence.py`
  - `tests/integration/test_api_docs.py`
- System checks:
  - `tests/test_frontend_api.py`
  - `tests/verify_system.py`
- Model placeholder:
  - `tests/model/test_model_validation_placeholder.py`

Master note:

- Có placeholder tests → cần clarify scope (để rubric, hoặc bỏ).
- CI có coverage gate 80% → cần đảm bảo test cover src đủ.

---

## 15) Artifacts & Evidence (đầy đủ) — mapping + gallery

### 15.1 Evidence outputs (reports)

Folder: `artifacts/reports/`

Có các loại file:

- schema/EDA: `dataset_schema.json`, `eda_summary.json`, `missing_values.csv`, `summary_statistics.csv`, `class_distribution.*`
- model: `model_selection_summary.json`, `model_validation_checks.json`, `split_info.json`
- API examples (contract snapshots):
  - `api_example_health.json`
  - `api_example_predict.json`
  - `api_example_metrics.txt`
  - `api_example_features_schema.json`
  - `api_example_dataset_samples.json`
- version tracking:
  - `benchmark_summary.md`
  - `latest_model_run.json`
  - `model_run_history.jsonl`

### 15.2 Figures gallery (artifacts/figures)

EDA + model evaluation + UI screenshots:

![class_distribution](artifacts/figures/class_distribution.png)
![amount_distribution](artifacts/figures/amount_distribution.png)
![time_distribution](artifacts/figures/time_distribution.png)
![fraud_vs_nonfraud_amount](artifacts/figures/fraud_vs_nonfraud_amount.png)
![fraud_vs_nonfraud_time](artifacts/figures/fraud_vs_nonfraud_time.png)
![correlation_overview](artifacts/figures/correlation_overview.png)
![correlation_full](artifacts/figures/correlation_full.png)

![model_comparison](artifacts/figures/model_comparison.png)
![baseline_threshold_sweep](artifacts/figures/baseline_threshold_sweep.png)
![improved_threshold_sweep](artifacts/figures/improved_threshold_sweep.png)
![threshold_comparison](artifacts/figures/threshold_comparison.png)

![final_pr_curve](artifacts/figures/final_pr_curve.png)
![final_roc_curve](artifacts/figures/final_roc_curve.png)
![final_confusion_matrix](artifacts/figures/final_confusion_matrix.png)
![final_feature_importance](artifacts/figures/final_feature_importance.png)
![shap_summary](artifacts/figures/shap_summary.png)

![frontend_dashboard](artifacts/figures/frontend_dashboard.png)
![frontend_dashboard_live](artifacts/figures/frontend_dashboard_live.png)
![frontend_dashboard_streaming](artifacts/figures/frontend_dashboard_streaming.png)

### 15.3 Deployment screenshots gallery (artifacts/deploys)

![swagger-docs](artifacts/deploys/swagger-docs.png)
![docker-compose](artifacts/deploys/docker-compose.png)
![docker-terminal](artifacts/deploys/docker-terminal.png)
![Prometheus-targets](artifacts/deploys/Prometheus-targets.png)
![Prometheus-rules](artifacts/deploys/Prometheus-rules.png)
![Grafana-dashboard](artifacts/deploys/Grafana-dashboard.png)
![grafana-api-monitoring](artifacts/deploys/gafrana-fraud-detection-api-monitoring-2026-04-15-11_54_29.png)
![screencapture](artifacts/deploys/screencapture-127-0-0-1-41001-2026-04-14-15_36_02.png)

---

## 16) MASTER REVIEW FINDINGS (ưu tiên cao → thấp)

### P0 — cần sửa/ghi rõ để tránh demo sai

1) **Metadata coupling có thể sai khi đổi `MODEL_PATH`**  
   - Loader đọc `model_info.json` cùng thư mục model → nếu có nhiều `.joblib` trong `artifacts/models/` mà chỉ có 1 `model_info.json`, dễ mismatch.
2) **`.env.example` không thống nhất với compose deploy**  
   - `.env.example` trỏ `improved_lightgbm.joblib` + `FRAUD_THRESHOLD=0.14` (rất thấp), trong khi compose dùng `final_model.joblib` + thresholds trong metadata.
3) **Auth disabled => mọi request thành admin**  
   - demo OK; nếu expose thì nguy hiểm. Cần note rõ trong report/thuyết trình.

### P1 — kỹ thuật ổn cho demo nhưng cần note hạn chế

4) **`risk_score` uncalibrated**  
   - repo đã note đúng (ranking signal). Cần nhấn mạnh khi defense.
5) **Reason codes là heuristic**  
   - không phải causal explanation.
6) **Rate limit in-memory, key chứa raw token**  
   - demo OK; production cần cải tiến.
7) **SQL schema lưu JSON trong TEXT**  
   - demo OK; production cần cân nhắc storage/indexing.

### P2 — cleanup / polish

8) `frontend/package-lock.json` có nhưng thiếu `package.json` → cần clarify hoặc dọn.
9) Có placeholder tests → hoặc implement hoặc remove để rõ scope.
10) `requirements.txt` không pin versions → reproducibility kém; có thể gây mismatch joblib/sklearn khi load artifacts.

---

## 17) Cách chạy (as-is, theo repo docs)

### 17.1 Local E2E (khuyến nghị)

```bash
bash ./rune2e.sh
```

### 17.2 Train + run API + run frontend (manual)

```bash
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts
./.venv/bin/python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
cd frontend && ../.venv/bin/python -m http.server 8082 --bind 127.0.0.1
```

### 17.3 Full stack Docker Compose

```bash
docker compose -f deployment/docker-compose.yml up --build
```

URLs:

- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:8082/`
- Prometheus: `http://localhost:9090/`
- Grafana: `http://localhost:3000/` (admin password theo compose env)
- MLflow: `http://localhost:5000/`

---

## 18) Docs & Reports folder review (as-is)

### 18.1 `docs/` đang chứa gì

Các file đáng chú ý:

- `docs/QUICK_START.md` — hướng dẫn chạy local (E2E + manual + compose).
- `docs/QUICK_ACCESS_GUIDE.md` — guide truy cập services sau deploy.
- `docs/COMPLETE_SYSTEM_SPECIFICATION_EXTRACTED.md` — đặc tả hệ thống (markdown extracted).
- `docs/*.pdf` — các bản PDF report/spec đã export.

### 18.2 Finding: `docs/QUICK_ACCESS_GUIDE.md` có nhắc tới file không thấy trong workspace

Trong `docs/QUICK_ACCESS_GUIDE.md` có bảng “Documentation Files” nhắc:

- `DEPLOYMENT_REPORT.md`
- `FINAL_REPORT_EVIDENCE_BASED.md`
- `RESPONSIBLE_AI.md`

Nhưng trong inventory hiện tại (as-is), các file `.md` này **không thấy** ở repo root hoặc `docs/`.  
Master note: cần hoặc **bổ sung** các file đó, hoặc **sửa guide** để không gây confusion khi nộp/defense.

---

## 19) Appendix A — Full file list (source + configs + docs + artifacts)

Danh sách này lấy từ `find` và **đã loại trừ**: `.git/`, `.venv/`, `.pytest_cache/`, `__pycache__/`, `*.pyc`.

```text
./.codex
./.coveragerc
./.env.example
./.github/agents/fraud-detection-techlead.agent.md
./.github/workflows/ci.yml
./.github/workflows/docker.yml
./.gitignore
./ARCHITECTURE.md
./CONTRIBUTING.md
./MASTER_REPORT.md
./Makefile
./PROJECT_AS_IS_FULL.md
./README.md
./artifacts/benchmarks/baseline_metrics_table.csv
./artifacts/benchmarks/baseline_threshold_tuning.csv
./artifacts/benchmarks/final_feature_importance.csv
./artifacts/benchmarks/improved_feature_importance.csv
./artifacts/benchmarks/improved_hyperparameter_tuning.csv
./artifacts/benchmarks/improved_metrics_table.csv
./artifacts/benchmarks/improved_threshold_tuning.csv
./artifacts/benchmarks/model_comparison.csv
./artifacts/benchmarks/model_comparison_table.csv
./artifacts/benchmarks/shap_importance_table.csv
./artifacts/benchmarks/threshold_comparison.csv
./artifacts/benchmarks/threshold_comparison_table.csv
./artifacts/deploys/Grafana-dashboard.png
./artifacts/deploys/Prometheus-rules.png
./artifacts/deploys/Prometheus-targets.png
./artifacts/deploys/docker-compose.png
./artifacts/deploys/docker-terminal.png
./artifacts/deploys/gafrana-fraud-detection-api-monitoring-2026-04-15-11_54_29.png
./artifacts/deploys/screencapture-127-0-0-1-41001-2026-04-14-15_36_02.png
./artifacts/deploys/swagger-docs.png
./artifacts/figures/amount_distribution.png
./artifacts/figures/baseline_confusion_matrix.png
./artifacts/figures/baseline_pr_curve.png
./artifacts/figures/baseline_roc_curve.png
./artifacts/figures/baseline_threshold_sweep.png
./artifacts/figures/class_distribution.png
./artifacts/figures/confusion_matrix.png
./artifacts/figures/correlation_full.png
./artifacts/figures/correlation_overview.png
./artifacts/figures/feature_importance.png
./artifacts/figures/final_confusion_matrix.png
./artifacts/figures/final_feature_importance.png
./artifacts/figures/final_pr_curve.png
./artifacts/figures/final_roc_curve.png
./artifacts/figures/fraud_vs_nonfraud_amount.png
./artifacts/figures/fraud_vs_nonfraud_time.png
./artifacts/figures/frontend_dashboard.png
./artifacts/figures/frontend_dashboard_live.png
./artifacts/figures/frontend_dashboard_stream.png
./artifacts/figures/frontend_dashboard_streaming.png
./artifacts/figures/improved_confusion_matrix.png
./artifacts/figures/improved_feature_importance.png
./artifacts/figures/improved_pr_curve.png
./artifacts/figures/improved_roc_curve.png
./artifacts/figures/improved_threshold_sweep.png
./artifacts/figures/model_comparison.png
./artifacts/figures/shap_summary.png
./artifacts/figures/threshold_comparison.png
./artifacts/figures/time_distribution.png
./artifacts/mlflow.db
./artifacts/mlruns/563722485002843249/6cd1aae894244504b2910f668b2a6ec0/meta.yaml
./artifacts/mlruns/563722485002843249/meta.yaml
./artifacts/models/baseline_logistic_regression_pipeline.joblib
./artifacts/models/final_model.joblib
./artifacts/models/final_preprocessing_identity.json
./artifacts/models/improved_lightgbm.joblib
./artifacts/models/model_info.json
./artifacts/models/versions/index.json
./artifacts/models/versions/v0001_20260421T075817Z/final_model.joblib
./artifacts/models/versions/v0001_20260421T075817Z/model_comparison_table.csv
./artifacts/models/versions/v0001_20260421T075817Z/model_info.json
./artifacts/models/versions/v0001_20260421T075817Z/model_selection_summary.json
./artifacts/models/versions/v0001_20260421T075817Z/model_validation_checks.json
./artifacts/models/versions/v0001_20260421T075817Z/threshold_comparison_table.csv
./artifacts/reports/api_example_dataset_samples.json
./artifacts/reports/api_example_features_schema.json
./artifacts/reports/api_example_health.json
./artifacts/reports/api_example_metrics.txt
./artifacts/reports/api_example_predict.json
./artifacts/reports/baseline_classification_report.json
./artifacts/reports/baseline_metrics.json
./artifacts/reports/benchmark_summary.md
./artifacts/reports/class_distribution.csv
./artifacts/reports/class_distribution.json
./artifacts/reports/dataset_schema.json
./artifacts/reports/eda_summary.json
./artifacts/reports/improved_classification_report.json
./artifacts/reports/improved_metrics.json
./artifacts/reports/latest_model_run.json
./artifacts/reports/missing_values.csv
./artifacts/reports/model_run_history.jsonl
./artifacts/reports/model_selection_summary.json
./artifacts/reports/model_validation_checks.json
./artifacts/reports/split_info.json
./artifacts/reports/summary_statistics.csv
./conftest.py
./data/.keep
./data/archive/creditcard.csv
./deployment/.env
./deployment/.env.example
./deployment/api/Dockerfile
./deployment/docker-compose.yml
./deployment/frontend/Dockerfile
./deployment/grafana/dashboards/fraud_api.json
./deployment/grafana/dashboards/mlflow.json
./deployment/grafana/provisioning/dashboards/dashboards.yml
./deployment/grafana/provisioning/datasources/datasource.yml
./deployment/mlflow/Dockerfile
./deployment/mlflow/exporter.py
./deployment/prometheus/alerts.yml
./deployment/prometheus/prometheus.yml
./docs/COMPLETE_SYSTEM_SPECIFICATION_EXTRACTED.md
./docs/EndToEnd_Fraud_Decision_Intelligence.pdf
./docs/FINAL_E2E_REPORT.pdf
./docs/FINAL_PROJECT_REPORT.pdf
./docs/QUICK_ACCESS_GUIDE.md
./docs/QUICK_START.md
./docs/SYSTEM_SPECIFICATION_COMPLETE.pdf
./frontend/api-client.js
./frontend/app.js
./frontend/demo-data.js
./frontend/index.html
./frontend/package-lock.json
./frontend/screenshot_server.py
./frontend/styles.css
./frontend/ui.js
./latex/.gitignore
./latex/COMPLETE_FRAUD_DETECTION_REPORT.aux
./latex/COMPLETE_FRAUD_DETECTION_REPORT.log
./latex/COMPLETE_FRAUD_DETECTION_REPORT.out
./latex/COMPLETE_FRAUD_DETECTION_REPORT.pdf
./latex/COMPLETE_FRAUD_DETECTION_REPORT.tex
./latex/COMPLETE_FRAUD_DETECTION_REPORT.toc
./latex/EndToEnd_Fraud_Decision_Intelligence.aux
./latex/EndToEnd_Fraud_Decision_Intelligence.log
./latex/EndToEnd_Fraud_Decision_Intelligence.out
./latex/EndToEnd_Fraud_Decision_Intelligence.toc
./latex/FINAL_E2E_REPORT.aux
./latex/FINAL_E2E_REPORT.log
./latex/FINAL_E2E_REPORT.out
./latex/FINAL_E2E_REPORT.pdf
./latex/FINAL_E2E_REPORT.toc
./latex/FINAL_PROJECT_REPORT.aux
./latex/FINAL_PROJECT_REPORT.log
./latex/FINAL_PROJECT_REPORT.out
./latex/FINAL_PROJECT_REPORT.pdf
./latex/FINAL_PROJECT_REPORT.toc
./latex/SYSTEM_SPECIFICATION_COMPLETE.aux
./latex/SYSTEM_SPECIFICATION_COMPLETE.log
./latex/SYSTEM_SPECIFICATION_COMPLETE.out
./latex/SYSTEM_SPECIFICATION_COMPLETE.toc
./latex/references.bib
./mlruns/1/7fe8b0aef45147e78055a818f513b4a3/artifacts/improved_confusion_matrix.png
./mlruns/1/7fe8b0aef45147e78055a818f513b4a3/artifacts/improved_metrics_table.csv
./mlruns/1/7fe8b0aef45147e78055a818f513b4a3/artifacts/shap_summary.png
./mlruns/1/ad5163df2be34795ac060c2944eb9663/artifacts/baseline_confusion_matrix.png
./mlruns/1/ad5163df2be34795ac060c2944eb9663/artifacts/baseline_metrics_table.csv
./notebooks/.keep
./pytest.ini
./requirements.txt
./rune2e.sh
./scripts/deploy_full_stack.sh
./src/__init__.py
./src/api/__init__.py
./src/api/main.py
./src/api/schemas.py
./src/data/__init__.py
./src/data/dataset.py
./src/data/samples.py
./src/features/__init__.py
./src/features/preprocess.py
./src/features/random_features.py
./src/models/__init__.py
./src/models/loader.py
./src/models/registry.py
./src/models/versioning.py
./src/monitoring/__init__.py
./src/monitoring/metrics.py
./src/monitoring/mlflow_runtime_tracker.py
./src/pipelines/__init__.py
./src/pipelines/batch_score_pipeline.py
./src/pipelines/run_model_workflow.py
./src/pipelines/train_pipeline.py
./src/repositories/__init__.py
./src/repositories/case_lifecycle.py
./src/repositories/case_repository_protocol.py
./src/repositories/factory.py
./src/repositories/in_memory_case_repository.py
./src/repositories/migrations.py
./src/repositories/migrations/001_case_lifecycle.sql
./src/repositories/sql_case_repository.py
./src/security/__init__.py
./src/security/audit.py
./src/security/auth.py
./src/security/rate_limit.py
./src/services/__init__.py
./src/services/case_service.py
./src/services/decision_service.py
./src/services/reason_code_service.py
./src/services/scoring_service.py
./src/streaming/__init__.py
./src/streaming/simulator.py
./src/utils/__init__.py
./src/utils/ids.py
./tests/__init__.py
./tests/data/test_data_quality_placeholder.py
./tests/data/test_samples.py
./tests/integration/__init__.py
./tests/integration/asgi_client.py
./tests/integration/conftest.py
./tests/integration/test_api_alert_case_workflow.py
./tests/integration/test_api_dataset_samples.py
./tests/integration/test_api_docs.py
./tests/integration/test_api_health.py
./tests/integration/test_api_predict_happy_path.py
./tests/integration/test_api_predict_no_model.py
./tests/integration/test_api_random_features.py
./tests/integration/test_api_security.py
./tests/integration/test_api_sql_persistence.py
./tests/integration/test_api_stream_pull.py
./tests/model/test_model_validation_placeholder.py
./tests/test_frontend_api.py
./tests/unit/test_ids.py
./tests/unit/test_loader_and_scoring.py
./tests/unit/test_preprocess.py
./tests/unit/test_reason_code_service.py
./tests/verify_system.py
```
