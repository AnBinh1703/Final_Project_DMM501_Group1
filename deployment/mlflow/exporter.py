from __future__ import annotations

import os
import sqlite3
import threading
import time
import urllib.request

from prometheus_client import Gauge, start_http_server


MLFLOW_URL = os.getenv("MLFLOW_URL", "http://127.0.0.1:5000/")
DB_PATH = os.getenv("MLFLOW_DB_PATH", "/mlflow/mlflow.db")
EXPORTER_PORT = int(os.getenv("MLFLOW_EXPORTER_PORT", "5001"))
SCRAPE_INTERVAL_SECONDS = float(os.getenv("MLFLOW_EXPORTER_INTERVAL_SECONDS", "15"))
HTTP_TIMEOUT_SECONDS = float(os.getenv("MLFLOW_EXPORTER_HTTP_TIMEOUT_SECONDS", "2"))


MLFLOW_SERVER_UP = Gauge("mlflow_server_up", "Whether the MLflow HTTP server is reachable (1/0)")
MLFLOW_SERVER_PROBE_LATENCY_SECONDS = Gauge(
    "mlflow_server_probe_latency_seconds", "Latency for probing the MLflow HTTP server"
)

MLFLOW_BACKEND_DB_SIZE_BYTES = Gauge("mlflow_backend_db_size_bytes", "Size of MLflow backend SQLite DB in bytes")
MLFLOW_ARTIFACTS_DISK_TOTAL_BYTES = Gauge("mlflow_artifacts_disk_total_bytes", "Total bytes on /mlflow filesystem")
MLFLOW_ARTIFACTS_DISK_FREE_BYTES = Gauge("mlflow_artifacts_disk_free_bytes", "Free bytes on /mlflow filesystem")

MLFLOW_DB_QUERY_SUCCESS = Gauge("mlflow_db_query_success", "Whether the exporter could query MLflow DB (1/0)")
MLFLOW_EXPERIMENTS_TOTAL = Gauge("mlflow_experiments_total", "Total number of MLflow experiments")
MLFLOW_RUNS_TOTAL = Gauge("mlflow_runs_total", "Total number of MLflow runs")
MLFLOW_RUNS_ACTIVE_TOTAL = Gauge("mlflow_runs_active_total", "Number of MLflow runs with status RUNNING")


def _probe_mlflow_server() -> None:
    start = time.perf_counter()
    ok = 0
    try:
        req = urllib.request.Request(MLFLOW_URL, method="GET")
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            ok = 1 if 200 <= int(resp.status) < 500 else 0
    except Exception:
        ok = 0
    elapsed = time.perf_counter() - start
    MLFLOW_SERVER_UP.set(ok)
    MLFLOW_SERVER_PROBE_LATENCY_SECONDS.set(elapsed)


def _collect_filesystem_metrics() -> None:
    try:
        st = os.stat(DB_PATH)
        MLFLOW_BACKEND_DB_SIZE_BYTES.set(float(st.st_size))
    except FileNotFoundError:
        MLFLOW_BACKEND_DB_SIZE_BYTES.set(0.0)
    except Exception:
        # Keep last value.
        pass

    try:
        vfs = os.statvfs("/mlflow")
        total = float(vfs.f_frsize * vfs.f_blocks)
        free = float(vfs.f_frsize * vfs.f_bavail)
        MLFLOW_ARTIFACTS_DISK_TOTAL_BYTES.set(total)
        MLFLOW_ARTIFACTS_DISK_FREE_BYTES.set(free)
    except Exception:
        # Keep last values.
        pass


def _query_sqlite_scalar(conn: sqlite3.Connection, sql: str) -> int:
    cur = conn.execute(sql)
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _collect_db_metrics() -> None:
    try:
        conn = sqlite3.connect(DB_PATH, timeout=1)
        try:
            experiments = _query_sqlite_scalar(conn, "SELECT COUNT(1) FROM experiments;")
            runs_total = _query_sqlite_scalar(conn, "SELECT COUNT(1) FROM runs;")
            runs_running = _query_sqlite_scalar(conn, "SELECT COUNT(1) FROM runs WHERE status = 'RUNNING';")
        finally:
            conn.close()

        MLFLOW_DB_QUERY_SUCCESS.set(1)
        MLFLOW_EXPERIMENTS_TOTAL.set(experiments)
        MLFLOW_RUNS_TOTAL.set(runs_total)
        MLFLOW_RUNS_ACTIVE_TOTAL.set(runs_running)
    except Exception:
        MLFLOW_DB_QUERY_SUCCESS.set(0)


def _loop() -> None:
    while True:
        _probe_mlflow_server()
        _collect_filesystem_metrics()
        _collect_db_metrics()
        time.sleep(SCRAPE_INTERVAL_SECONDS)


def main() -> None:
    start_http_server(EXPORTER_PORT)
    t = threading.Thread(target=_loop, name="mlflow-metrics-exporter", daemon=True)
    t.start()
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()

