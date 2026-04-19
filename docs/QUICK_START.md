# Quick Start (Full Project + Local E2E)

This guide focuses on local execution for the full fraud decision-support workflow:

- ML artifact loading
- FastAPI backend
- frontend dashboard
- alert and case lifecycle APIs
- tests (unit, integration, and local E2E smoke)

## 0) One-Command Interactive Local E2E (Recommended)

Run from repository root:

```bash
bash ./rune2e.sh
```

The script prompts through this flow:

- install libraries
- ensure dataset (uses `data/archive/creditcard.csv`, falls back to `data/raw/creditcard.csv`)
- run model pipeline
- start API backend
- start frontend
- build Docker images and validate compose

If you want the quickest reliable local path, use this section first.

## 1) Environment Setup

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

Windows bash note:

```powershell
bash --version
```

If `bash` is not recognized, install Git Bash:

```powershell
winget install --id Git.Git -e
```

## 2) Ensure Model Artifacts Exist

If `artifacts/models/final_model.joblib` already exists, skip this step.

```bash
python -m src.pipelines.run_model_workflow --data-path data/archive/creditcard.csv --artifacts-root artifacts
```

## 3) Run Backend API

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Quick checks:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/metrics
```

## 4) Run Frontend

Open a second terminal:

```bash
cd frontend
python -m http.server 8082 --bind 127.0.0.1
```

Open `http://127.0.0.1:8082/index.html`.

## 5) Local Test Paths

Run these from repository root.

Unit tests:

```bash
python -m pytest -q tests/unit tests/data
```

Integration tests:

```bash
python -m pytest -q tests/integration
```

Frontend API contract smoke test (API must already be running):

```bash
python tests/test_frontend_api.py
```

Full local E2E script (API must already be running):

```bash
python tests/verify_system.py
```

## 6) Optional Full Stack (Docker Compose)

```bash
docker compose -f deployment/docker-compose.yml up --build
```

Service URLs:

- API docs: <http://localhost:8000/docs>
- Frontend: <http://localhost:8082/index.html>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>
- MLflow: <http://localhost:5000>

## 7) Operational Notes

- `risk_score` is uncalibrated (`risk_score_uncalibrated`) and should be treated as a ranking signal.
- Alert and case persistence mode depends on environment config. In local default mode it may run in-memory.
- Docker Compose in this repo is for local deployment validation, not production rollout automation.
- If integration tests fail with model deserialization or scikit-learn version mismatch warnings, regenerate artifacts in your current environment using step 2 before re-running tests.

## 8) Troubleshooting

### `rune2e.sh` exits during model pipeline

- Confirm virtual environment is active and dependencies are installed.
- Re-run help check to confirm pipeline parser starts correctly:

```powershell
.\.venv\Scripts\python.exe -m src.pipelines.run_model_workflow --help
```

- If dataset is not at `data/archive/creditcard.csv`, place it there or keep `data/raw/creditcard.csv` and let `rune2e.sh` copy it.

### API or frontend did not start

- Check logs:
  - `artifacts/deploys/api.log`
  - `artifacts/deploys/frontend.log`

### Stop locally started services

- Use the `kill` command printed in the script summary.
