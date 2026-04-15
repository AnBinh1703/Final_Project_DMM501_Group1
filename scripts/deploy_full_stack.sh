#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

usage() {
  cat <<'USAGE'
Usage: bash scripts/deploy_full_stack.sh [options]

Build model artifacts on the host, then start the full Docker Compose stack:
API + Frontend + MLflow (+ exporter) + Prometheus + Grafana.

Options:
  --real               Run full workflow on real dataset (default)
  --fast               Run quick synthetic training (much faster)
  --data-path PATH     Dataset path for --real (default: data/archive/creditcard.csv)
  --artifacts-root DIR Artifacts output directory (default: artifacts)
  --seed INT           Random seed for --real workflow (default: 42)
  --down               Stop and remove stack (docker compose down -v) then exit
  --logs               Follow logs after startup
  -h, --help           Show this help

Environment overrides (ports):
  API_PORT=8000 FRONTEND_PORT=8082 MLFLOW_PORT=5000 PROMETHEUS_PORT=9090 GRAFANA_PORT=3000

Examples:
  bash scripts/deploy_full_stack.sh --real
  bash scripts/deploy_full_stack.sh --fast
  FRONTEND_PORT=8083 bash scripts/deploy_full_stack.sh --real --logs
USAGE
}

MODE="real"
DATA_PATH="data/archive/creditcard.csv"
ARTIFACTS_ROOT="artifacts"
SEED="42"
DO_DOWN="0"
FOLLOW_LOGS="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --real) MODE="real"; shift ;;
    --fast) MODE="fast"; shift ;;
    --data-path) DATA_PATH="${2:-}"; shift 2 ;;
    --artifacts-root) ARTIFACTS_ROOT="${2:-}"; shift 2 ;;
    --seed) SEED="${2:-}"; shift 2 ;;
    --down) DO_DOWN="1"; shift ;;
    --logs) FOLLOW_LOGS="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

need_cmd docker
need_cmd python3

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose not found (expected: docker compose ...)." >&2
  exit 1
fi

COMPOSE_FILE="deployment/docker-compose.yml"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-fraud-stack}"

if [[ "$DO_DOWN" == "1" ]]; then
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v
  exit 0
fi

PYTHON="./.venv/bin/python"
PIP="./.venv/bin/pip"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

echo "[1/3] Build model artifacts -> ${ARTIFACTS_ROOT}"
mkdir -p "$ARTIFACTS_ROOT"

if [[ "$MODE" == "fast" ]]; then
  "$PYTHON" -m src.pipelines.train_pipeline --data-path "" --artifacts-dir "$ARTIFACTS_ROOT" --fast
else
  if [[ ! -f "$DATA_PATH" ]]; then
    echo "Dataset not found: $DATA_PATH" >&2
    echo "Tip: pass --data-path <path> or use --fast." >&2
    exit 1
  fi
  "$PYTHON" -m src.pipelines.run_model_workflow \
    --data-path "$DATA_PATH" \
    --artifacts-root "$ARTIFACTS_ROOT" \
    --seed "$SEED"
fi

if [[ -f "${ARTIFACTS_ROOT}/models/final_model.joblib" ]]; then
  echo "Model: ${ARTIFACTS_ROOT}/models/final_model.joblib"
elif [[ -f "${ARTIFACTS_ROOT}/model.joblib" ]]; then
  echo "Model: ${ARTIFACTS_ROOT}/model.joblib"
else
  echo "Expected model artifact not found under ${ARTIFACTS_ROOT}/" >&2
  echo "Look for: ${ARTIFACTS_ROOT}/models/final_model.joblib or ${ARTIFACTS_ROOT}/model.joblib" >&2
  exit 1
fi

API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8082}"
MLFLOW_PORT="${MLFLOW_PORT:-5000}"
PROMETHEUS_PORT="${PROMETHEUS_PORT:-9090}"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"

echo "[2/3] Start Docker Compose stack (project: ${PROJECT_NAME})"
API_PORT="$API_PORT" \
FRONTEND_PORT="$FRONTEND_PORT" \
MLFLOW_PORT="$MLFLOW_PORT" \
PROMETHEUS_PORT="$PROMETHEUS_PORT" \
GRAFANA_PORT="$GRAFANA_PORT" \
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --build

echo "[3/3] Wait for API health"
for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    echo "API healthy."
    break
  fi
  sleep 2
done

echo
echo "Service URLs:"
echo "- API:        http://localhost:${API_PORT}   (Swagger: /docs, Metrics: /metrics)"
echo "- Frontend:   http://localhost:${FRONTEND_PORT}/index.html"
echo "- MLflow:     http://localhost:${MLFLOW_PORT}"
echo "- Prometheus: http://localhost:${PROMETHEUS_PORT}"
echo "- Grafana:    http://localhost:${GRAFANA_PORT}   (admin / admin)"
echo

if [[ "$FOLLOW_LOGS" == "1" ]]; then
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" logs -f --tail=200
fi

