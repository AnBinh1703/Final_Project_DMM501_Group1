#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8082}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-fraud-stack}"

DATASET_TARGET="data/archive/creditcard.csv"
DATASET_FALLBACK="data/raw/creditcard.csv"
FAST_MODE="0"
TRAINED_THIS_RUN="0"

STARTED_PIDS=()

log() {
  printf "\n[run-e2e] %s\n" "$1"
}

warn() {
  printf "[run-e2e][warn] %s\n" "$1" >&2
}

die() {
  printf "[run-e2e][error] %s\n" "$1" >&2
  exit 1
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    die "Missing required command: $1"
  fi
}

ask_yes_no() {
  local question="$1"
  local default_answer="${2:-Y}"
  local prompt
  local answer

  if [[ "$default_answer" == "Y" ]]; then
    prompt="[Y/n]"
  else
    prompt="[y/N]"
  fi

  while true; do
    read -r -p "$question $prompt " answer || true
    answer="${answer:-$default_answer}"
    case "${answer,,}" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) printf "Please answer y or n.\n" ;;
    esac
  done
}

resolve_python() {
  if [[ -x ".venv/bin/python" ]]; then
    echo ".venv/bin/python"
    return
  fi
  if [[ -x ".venv/Scripts/python.exe" ]]; then
    echo ".venv/Scripts/python.exe"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return
  fi
  die "Python not found. Install Python 3 first."
}

PYTHON_BIN="$(resolve_python)"

run_pip_install() {
  log "Installing Python libraries from requirements.txt"
  "$PYTHON_BIN" -m pip install -U pip
  "$PYTHON_BIN" -m pip install -r requirements.txt
}

ensure_dataset() {
  if [[ -f "$DATASET_TARGET" ]]; then
    log "Dataset found: $DATASET_TARGET"
    return
  fi

  if [[ -f "$DATASET_FALLBACK" ]]; then
    log "Dataset found in fallback path: $DATASET_FALLBACK"
    mkdir -p "$(dirname "$DATASET_TARGET")"
    cp "$DATASET_FALLBACK" "$DATASET_TARGET"
    log "Copied dataset to expected path: $DATASET_TARGET"
    return
  fi

  warn "Dataset not found at $DATASET_TARGET or $DATASET_FALLBACK"

  if ask_yes_no "Try downloading dataset using Kaggle CLI (mlg-ulb/creditcardfraud)?" "Y"; then
    if command -v kaggle >/dev/null 2>&1; then
      mkdir -p "$(dirname "$DATASET_TARGET")"
      if kaggle datasets download -d mlg-ulb/creditcardfraud -p "$(dirname "$DATASET_TARGET")" --unzip; then
        if [[ -f "$DATASET_TARGET" ]]; then
          log "Kaggle download complete: $DATASET_TARGET"
          return
        fi
      fi
      warn "Kaggle download did not produce $DATASET_TARGET"
    else
      warn "Kaggle CLI not found. Install with: $PYTHON_BIN -m pip install kaggle"
    fi
  fi

  if ask_yes_no "Provide a local dataset file path now?" "Y"; then
    local custom_path=""
    read -r -p "Enter local path to creditcard.csv: " custom_path || true
    if [[ -n "$custom_path" && -f "$custom_path" ]]; then
      mkdir -p "$(dirname "$DATASET_TARGET")"
      cp "$custom_path" "$DATASET_TARGET"
      log "Copied dataset from custom path to $DATASET_TARGET"
      return
    fi
    warn "Provided dataset path is invalid or missing."
  fi

  warn "Proceeding without real dataset. Training will use fast synthetic mode."
  FAST_MODE="1"
}

run_training() {
  log "Running model pipeline"

  if [[ "$FAST_MODE" == "1" ]]; then
    "$PYTHON_BIN" -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts --fast
  else
    if [[ ! -f "$DATASET_TARGET" ]]; then
      warn "Dataset missing unexpectedly. Falling back to fast synthetic training."
      "$PYTHON_BIN" -m src.pipelines.train_pipeline --data-path "" --artifacts-dir artifacts --fast
      FAST_MODE="1"
    else
      "$PYTHON_BIN" -m src.pipelines.run_model_workflow --data-path "$DATASET_TARGET" --artifacts-root artifacts --seed 42
    fi
  fi

  TRAINED_THIS_RUN="1"
}

resolve_model_artifact() {
  if [[ -f "artifacts/models/final_model.joblib" ]]; then
    echo "artifacts/models/final_model.joblib"
    return
  fi
  if [[ -f "artifacts/model.joblib" ]]; then
    echo "artifacts/model.joblib"
    return
  fi
  echo ""
}

wait_for_http() {
  local url="$1"
  local retries="${2:-60}"
  local sleep_sec="${3:-2}"

  for _ in $(seq 1 "$retries"); do
    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "$url" >/dev/null 2>&1; then
        return 0
      fi
    else
      if "$PYTHON_BIN" - <<'PY' "$url"; then
import sys
import urllib.request
url = sys.argv[1]
try:
    with urllib.request.urlopen(url, timeout=2):
        pass
except Exception:
    raise SystemExit(1)
raise SystemExit(0)
PY
        return 0
      fi
    fi
    sleep "$sleep_sec"
  done

  return 1
}

start_backend() {
  local model_path="$1"
  mkdir -p artifacts/deploys

  log "Starting API backend on port $API_PORT"
  (
    export MODEL_PATH="$model_path"
    "$PYTHON_BIN" -m uvicorn src.api.main:app --host 127.0.0.1 --port "$API_PORT" > artifacts/deploys/api.log 2>&1
  ) &

  local api_pid=$!
  STARTED_PIDS+=("$api_pid")

  if wait_for_http "http://127.0.0.1:${API_PORT}/health" 60 2; then
    log "API backend is healthy (PID: $api_pid)"
  else
    die "API backend did not become healthy. Check artifacts/deploys/api.log"
  fi
}

start_frontend() {
  mkdir -p artifacts/deploys

  log "Starting frontend static server on port $FRONTEND_PORT"
  (
    cd frontend
    "$PYTHON_BIN" -m http.server "$FRONTEND_PORT" --bind 127.0.0.1 > ../artifacts/deploys/frontend.log 2>&1
  ) &

  local front_pid=$!
  STARTED_PIDS+=("$front_pid")

  if wait_for_http "http://127.0.0.1:${FRONTEND_PORT}/index.html" 60 2; then
    log "Frontend is up (PID: $front_pid)"
  else
    die "Frontend did not become reachable. Check artifacts/deploys/frontend.log"
  fi
}

build_docker_assets() {
  need_cmd docker

  if ! docker compose version >/dev/null 2>&1; then
    die "Docker Compose plugin is required (docker compose ...)."
  fi

  log "Building Docker images"
  docker build -f deployment/api/Dockerfile -t fraud-api:e2e .
  docker build -f deployment/frontend/Dockerfile -t fraud-frontend:e2e .

  log "Validating docker-compose"
  docker compose -f deployment/docker-compose.yml config >/dev/null

  if ask_yes_no "Start full docker compose stack now?" "N"; then
    log "Starting docker compose stack"
    docker compose -p "$PROJECT_NAME" -f deployment/docker-compose.yml up -d --build
  fi
}

print_summary() {
  local model_path="$1"

  cat <<EOF

==================== E2E SUMMARY ====================
Python:            $PYTHON_BIN
Dataset target:    $DATASET_TARGET
Training mode:     $( [[ "$FAST_MODE" == "1" ]] && echo "fast synthetic" || echo "real dataset" )
Model artifact:    $model_path
API URL:           http://127.0.0.1:${API_PORT}
Frontend URL:      http://127.0.0.1:${FRONTEND_PORT}/index.html
API log:           artifacts/deploys/api.log
Frontend log:      artifacts/deploys/frontend.log

To stop local API/frontend started by this script:
  kill ${STARTED_PIDS[*]:-<pid>}

Docker compose (if started):
  docker compose -p "$PROJECT_NAME" -f deployment/docker-compose.yml down
=====================================================
EOF
}

main() {
  log "Interactive full-project E2E runner"

  if ask_yes_no "Install Python libraries now?" "Y"; then
    run_pip_install
  else
    log "Skipping library installation"
  fi

  ensure_dataset

  if ask_yes_no "Run model pipeline now?" "Y"; then
    run_training
  else
    log "Skipping model pipeline run"
  fi

  local model_path
  model_path="$(resolve_model_artifact)"
  if [[ -z "$model_path" ]]; then
    if [[ "$TRAINED_THIS_RUN" == "1" ]]; then
      die "Model pipeline finished but no model artifact was found."
    fi
    die "No model artifact found. Run training first."
  fi

  if ask_yes_no "Start API backend now?" "Y"; then
    start_backend "$model_path"
  else
    log "Skipping API backend start"
  fi

  if ask_yes_no "Start frontend now?" "Y"; then
    start_frontend
  else
    log "Skipping frontend start"
  fi

  if ask_yes_no "Build Docker images and validate compose now?" "Y"; then
    build_docker_assets
  else
    log "Skipping Docker build/compose"
  fi

  print_summary "$model_path"
}

main "$@"
