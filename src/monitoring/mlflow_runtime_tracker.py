from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from typing import Any


def _truthy(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


class MlflowRuntimeTracker:
    def __init__(
        self,
        *,
        enabled: bool,
        tracking_uri: str,
        experiment_name: str,
        run_name: str,
        log_every: int,
    ) -> None:
        self.enabled = bool(enabled)
        self.tracking_uri = str(tracking_uri).strip()
        self.experiment_name = str(experiment_name).strip() or "fraud-runtime-traffic"
        self.run_name = str(run_name).strip() or "api-online-traffic"
        self.log_every = max(1, int(log_every))

        self._lock = threading.Lock()
        self._client: Any = None
        self._run_id: str | None = None
        self._step = 0
        self._flush_count = 0
        self._last_error: str | None = None

        self._requests_total = 0
        self._predict_calls_total = 0
        self._stream_pull_calls_total = 0
        self._scored_events_total = 0
        self._score_sum = 0.0
        self._score_count = 0

        self._tier_totals: dict[str, int] = defaultdict(int)
        self._decision_totals: dict[str, int] = defaultdict(int)
        self._http_status_family_totals: dict[str, int] = defaultdict(int)

        self._updates_since_flush = 0

    @classmethod
    def from_env(cls) -> "MlflowRuntimeTracker":
        return cls(
            enabled=_truthy(os.getenv("MLFLOW_RUNTIME_ENABLED", "false")),
            tracking_uri=os.getenv("MLFLOW_RUNTIME_TRACKING_URI", ""),
            experiment_name=os.getenv("MLFLOW_RUNTIME_EXPERIMENT", "fraud-runtime-traffic"),
            run_name=os.getenv("MLFLOW_RUNTIME_RUN_NAME", "api-online-traffic"),
            log_every=int(os.getenv("MLFLOW_RUNTIME_LOG_EVERY", "20")),
        )

    def _ensure_client(self) -> None:
        if not self.enabled:
            return
        if self._client is not None and self._run_id:
            return

        try:
            import mlflow
            from mlflow.tracking import MlflowClient

            if self.tracking_uri:
                mlflow.set_tracking_uri(self.tracking_uri)
                client = MlflowClient(tracking_uri=self.tracking_uri)
            else:
                client = MlflowClient()

            experiment = client.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                experiment_id = str(client.create_experiment(self.experiment_name))
            else:
                exp_id_raw = getattr(experiment, "experiment_id", None)
                if exp_id_raw is None:
                    raise RuntimeError("MLflow experiment has no experiment_id")
                experiment_id = str(exp_id_raw)

            run = client.create_run(
                experiment_id=experiment_id,
                tags={
                    "mlflow.runName": self.run_name,
                    "source": "api-runtime-monitoring",
                },
            )
            run_id = getattr(getattr(run, "info", None), "run_id", None)
            if run_id is None:
                raise RuntimeError("MLflow create_run returned no run_id")

            self._client = client
            self._run_id = str(run_id)
        except Exception:
            self._client = None
            self._run_id = None

    def record_response(self, *, endpoint: str, method: str, http_status: int) -> None:
        del method
        if not self.enabled:
            return

        with self._lock:
            self._requests_total += 1
            family = f"{int(http_status) // 100}xx"
            self._http_status_family_totals[family] += 1
            if endpoint == "/predict":
                self._predict_calls_total += 1
            elif endpoint == "/stream/pull":
                self._stream_pull_calls_total += 1

            self._updates_since_flush += 1
            self._flush_if_needed_locked()

    def record_prediction(self, *, score: float, tier: str, decision_recommendation: str | None) -> None:
        if not self.enabled:
            return

        with self._lock:
            self._scored_events_total += 1
            self._score_sum += float(score)
            self._score_count += 1
            self._tier_totals[str(tier)] += 1

            if decision_recommendation is not None:
                self._decision_totals[str(decision_recommendation)] += 1

            self._updates_since_flush += 1
            self._flush_if_needed_locked()

    def flush(self) -> None:
        if not self.enabled:
            return

        with self._lock:
            self._flush_locked(force=True)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "enabled": bool(self.enabled),
                "tracking_uri": self.tracking_uri,
                "experiment_name": self.experiment_name,
                "run_name": self.run_name,
                "log_every": int(self.log_every),
                "run_id": self._run_id,
                "step": int(self._step),
                "flush_count": int(self._flush_count),
                "updates_since_flush": int(self._updates_since_flush),
                "requests_total": int(self._requests_total),
                "scored_events_total": int(self._scored_events_total),
                "last_error": self._last_error,
            }

    def _flush_if_needed_locked(self) -> None:
        if self._updates_since_flush >= self.log_every:
            self._flush_locked(force=False)

    def _log_metric(self, key: str, value: float, *, ts_ms: int, step: int) -> None:
        if self._client is None or self._run_id is None:
            return
        self._client.log_metric(self._run_id, key, float(value), timestamp=ts_ms, step=step)

    def _flush_locked(self, *, force: bool) -> None:
        if not force and self._updates_since_flush < self.log_every:
            return
        if self._updates_since_flush == 0:
            return

        self._ensure_client()
        if self._client is None or self._run_id is None:
            self._updates_since_flush = 0
            return

        ts_ms = int(time.time() * 1000)
        step = self._step

        try:
            self._log_metric("traffic_requests_total", float(self._requests_total), ts_ms=ts_ms, step=step)
            self._log_metric("traffic_predict_calls_total", float(self._predict_calls_total), ts_ms=ts_ms, step=step)
            self._log_metric(
                "traffic_stream_pull_calls_total",
                float(self._stream_pull_calls_total),
                ts_ms=ts_ms,
                step=step,
            )
            self._log_metric("traffic_scored_events_total", float(self._scored_events_total), ts_ms=ts_ms, step=step)

            avg_score = (self._score_sum / self._score_count) if self._score_count else 0.0
            self._log_metric("traffic_avg_risk_score", float(avg_score), ts_ms=ts_ms, step=step)

            for tier in ("LOW", "REVIEW", "HIGH"):
                self._log_metric(
                    f"traffic_tier_{tier.lower()}_total",
                    float(self._tier_totals.get(tier, 0)),
                    ts_ms=ts_ms,
                    step=step,
                )

            for family in ("2xx", "4xx", "5xx"):
                self._log_metric(
                    f"traffic_http_{family}_total",
                    float(self._http_status_family_totals.get(family, 0)),
                    ts_ms=ts_ms,
                    step=step,
                )

            known_decisions = ("ALLOW", "STEP_UP_AUTH", "MANUAL_REVIEW", "HOLD", "BLOCK")
            for decision in known_decisions:
                self._log_metric(
                    f"traffic_decision_{decision.lower()}_total",
                    float(self._decision_totals.get(decision, 0)),
                    ts_ms=ts_ms,
                    step=step,
                )

            self._step += 1
            self._flush_count += 1
            self._updates_since_flush = 0
            self._last_error = None
        except Exception as exc:
            self._last_error = repr(exc)
            self._client = None
            self._run_id = None


MLFLOW_RUNTIME_TRACKER = MlflowRuntimeTracker.from_env()
