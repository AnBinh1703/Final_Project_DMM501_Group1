# Báo cáo Step 1 — Repository Structure

## Phạm vi

Tài liệu này ghi nhận kết quả kiểm tra **Step 1 — Repository Structure** của dự án *Real-Time Banking Fraud Detection and Decision Support System*.
Nội dung tập trung vào cấu trúc thư mục, vai trò từng lớp, artefact sinh ra, và các rủi ro cấu trúc thấy ngay từ cây thư mục.

## Nguồn đã kiểm tra

- `README.md`
- `ARCHITECTURE.md`
- `deployment/docker-compose.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/docker.yml`
- Cây thư mục `src/`, `artifacts/`, `frontend/`, `deployment/`, `tests/`, `docs/`, `.github/`, `data/`, `latex/`, `mlruns/`, `scripts/`, `notebooks/`

## Tóm tắt ngắn

- `src/` chứa toàn bộ runtime code của backend, ML pipeline, persistence, security, streaming và monitoring.
- `frontend/` là UI analyst, dùng file tĩnh JavaScript/HTML/CSS thay vì một app frontend chuẩn `package.json`/bundler.
- `deployment/` gom Dockerfiles, Compose, Prometheus, Grafana, và MLflow.
- `artifacts/` là output sinh ra: model, benchmark, report, figure, screenshot deploy, và MLflow state.
- `tests/` có unit, integration, data, model, và test cho frontend API.
- `docs/` chứa spec/report PDF và một số markdown hướng dẫn, nhưng có một file được README/architecture nhắc tới lại không thấy trong tree.

## Bảng cấu trúc

| Folder | Role | Layer | Notes |
|---|---|---|---|
| `src/` | Mã nguồn runtime | Backend / ML / Ops | Có `api`, `services`, `repositories`, `pipelines`, `monitoring`, `security`, `streaming`, `data`, `features`, `models`, `utils`. |
| `artifacts/` | Output sinh ra | ML / MLOps evidence | Chứa `models/`, `benchmarks/`, `figures/`, `reports/`, `deploys/`, `mlflow.db`, `mlruns/`. |
| `frontend/` | Giao diện analyst | Presentation | Có `index.html`, `app.js`, `ui.js`, `api-client.js`, `demo-data.js`, `styles.css`. |
| `deployment/` | Hạ tầng chạy local | Infra / MLOps | Có `docker-compose.yml`, Dockerfiles, Prometheus, Grafana, MLflow exporter. |
| `tests/` | Kiểm thử | QA | Có `unit`, `integration`, `data`, `model`, và test cho frontend API. |
| `docs/` | Tài liệu | Documentation | Có report/spec PDF và markdown guide; không thấy file `FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md` dù bị tham chiếu. |
| `.github/workflows/` | CI/CD | Automation | Workflow `ci.yml` chạy unit/integration/coverage, `docker.yml` build image và validate Compose. |
| `data/` | Dữ liệu gốc | Data | Có `archive/creditcard.csv` là dataset đầu vào chính. |
| `latex/` | Nguồn và build report | Documentation build | Có `.tex`, `.pdf`, và file build trung gian (`.aux`, `.log`, `.toc`). |
| `mlruns/` | MLflow local store | Experiment tracking | Có run artifacts riêng, tách với `artifacts/mlruns/`. |
| `scripts/` | Script vận hành | Ops helper | Hiện thấy `deploy_full_stack.sh`. |
| `notebooks/` | Khu vực thử nghiệm | Research | Hiện chỉ có `.keep`, chưa có notebook thực chất. |

## Bằng chứng cấu trúc từ repo

### 1) Sơ đồ lớp trong README

```text
src/
  api/            # FastAPI endpoints and schemas
  services/       # scoring, decision, reason code, case services
  repositories/   # in-memory and SQL persistence paths
  pipelines/      # model workflow and training pipelines
  monitoring/     # Prometheus metrics and MLflow runtime tracking
frontend/         # analyst dashboard UI and API client
deployment/       # docker compose, Dockerfiles, Prometheus, Grafana, MLflow
artifacts/        # models, figures, reports, benchmarks, deploy screenshots
tests/            # unit, data, model, integration, system checks
docs/             # architecture, specification, deployment, responsible AI
```

### 2) Compose topology

```yaml
services:
  postgres:
  api:
  frontend:
  mlflow:
  prometheus:
  grafana:
```

### 3) Workflow coverage

```text
.github/workflows/ci.yml
.github/workflows/docker.yml
```

## Ảnh tham chiếu

Các ảnh dưới đây là artefact đã có sẵn trong repo, dùng để minh hoạ rằng `artifacts/` không phải source code mà là output của hệ thống.

![Swagger docs](../artifacts/deploys/swagger-docs.png)

![Analyst dashboard live](../artifacts/figures/frontend_dashboard_live.png)

![Grafana dashboard](../artifacts/deploys/Grafana-dashboard.png)

## Nhận xét kỹ thuật

- Cấu trúc repo khá rõ: source, deploy, test, artifact, và docs tách tương đối tốt.
- Có dấu hiệu repo lưu cả trạng thái sinh ra tại local (`__pycache__`, `.pytest_cache`, `latex/*.aux`, `mlruns/`), nên tree không còn “source-only”.
- Có mismatch tài liệu: `README.md` và `ARCHITECTURE.md` đều nhắc tới `docs/FINAL_DECISION_SUPPORT_UPGRADE_REPORT.md`, nhưng file đó không có trong tree hiện tại.
- `frontend/` có `package-lock.json` nhưng không thấy `package.json`; nếu đây là app npm thực sự thì manifest đang thiếu hoặc đã bị bỏ.

## Kết luận Step 1

Repository có đủ các lớp chính để tạo thành một hệ thống fraud decision-support end-to-end:

- runtime code ở `src/`
- giao diện ở `frontend/`
- orchestration ở `deployment/`
- output và bằng chứng ở `artifacts/`
- kiểm thử ở `tests/`
- tài liệu ở `docs/`

Tuy nhiên, hiện còn hai vấn đề cấu trúc đáng chú ý:

1. tài liệu tham chiếu bị thiếu file thực tế
2. repo đang chứa nhiều artefact sinh ra, làm tăng nhiễu cho review và bảo trì

## Trạng thái

**Step 1 đã hoàn tất.**
Sẵn sàng chuyển sang Step 2 khi bạn yêu cầu.
