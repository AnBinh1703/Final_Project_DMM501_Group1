from __future__ import annotations

import time
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram

from src.monitoring.mlflow_runtime_tracker import MLFLOW_RUNTIME_TRACKER

REQUESTS_TOTAL = Counter(
    "api_requests_total",
    "Total number of requests",
    ["endpoint", "method", "http_status"],
)

LATENCY_SECONDS = Histogram(
    "api_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
)

PREDICTIONS_TOTAL = Counter(
    "fraud_predictions_total",
    "Number of scored transactions by decision tier",
    ["tier"],
)

ACTION_TOTAL = Counter(
    "fraud_actions_total",
    "Number of suggested actions from the scoring policy",
    ["action"],
)

RISK_TIER_TOTAL = Counter(
    "risk_tier_total",
    "Total scored transactions by risk tier",
    ["tier"],
)

DECISION_RECOMMENDATIONS_TOTAL = Counter(
    "decision_recommendations_total",
    "Number of decision recommendations produced by the policy engine",
    ["decision"],
)

FRAUD_ALERTS_TOTAL = Counter(
    "fraud_alerts_total",
    "Number of fraud alerts generated for REVIEW/HIGH tiers",
    ["tier"],
)

FRAUD_CASES_TOTAL = Counter(
    "fraud_cases_total",
    "Number of cases created",
    ["status"],
)

FRAUD_CASE_STATUS_TOTAL = Counter(
    "fraud_case_status_total",
    "Case lifecycle status transition counter",
    ["status"],
)

CONFIRMED_FRAUD_TOTAL = Counter(
    "confirmed_fraud_total",
    "Number of cases resolved as confirmed fraud",
)

FALSE_POSITIVE_TOTAL = Counter(
    "false_positive_total",
    "Number of cases resolved as false positives",
)

REVIEW_QUEUE_SIZE = Gauge(
    "review_queue_size",
    "Current number of active cases awaiting analyst decision",
)

SCORES_SUM = Counter(
    "risk_scores_sum",
    "Sum of risk scores (for average computation)",
)

SCORES_COUNT = Counter(
    "risk_scores_count",
    "Count of risk scores (for average computation)",
)


@contextmanager
def track_request(endpoint: str, method: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        LATENCY_SECONDS.labels(endpoint=endpoint, method=method).observe(elapsed)


def record_response(endpoint: str, method: str, http_status: int) -> None:
    REQUESTS_TOTAL.labels(
        endpoint=endpoint,
        method=method,
        http_status=str(http_status),
    ).inc()
    MLFLOW_RUNTIME_TRACKER.record_response(endpoint=endpoint, method=method, http_status=int(http_status))


def record_prediction(score: float, tier: str, action: str, decision_recommendation: str | None = None) -> None:
    PREDICTIONS_TOTAL.labels(tier=str(tier)).inc()
    RISK_TIER_TOTAL.labels(tier=str(tier)).inc()
    ACTION_TOTAL.labels(action=str(action)).inc()
    if decision_recommendation is not None:
        DECISION_RECOMMENDATIONS_TOTAL.labels(decision=str(decision_recommendation)).inc()
    SCORES_SUM.inc(score)
    SCORES_COUNT.inc(1)
    MLFLOW_RUNTIME_TRACKER.record_prediction(
        score=float(score),
        tier=str(tier),
        decision_recommendation=str(decision_recommendation) if decision_recommendation is not None else None,
    )


def record_alert_created(*, tier: str, case_status: str) -> None:
    FRAUD_ALERTS_TOTAL.labels(tier=str(tier)).inc()
    FRAUD_CASES_TOTAL.labels(status=str(case_status)).inc()


def record_case_status(case_status: str) -> None:
    resolved = str(case_status)
    FRAUD_CASE_STATUS_TOTAL.labels(status=resolved).inc()
    if resolved == "CONFIRMED_FRAUD":
        CONFIRMED_FRAUD_TOTAL.inc()
    if resolved == "FALSE_POSITIVE":
        FALSE_POSITIVE_TOTAL.inc()


def set_review_queue_size(size: int) -> None:
    REVIEW_QUEUE_SIZE.set(max(0, int(size)))


def flush_runtime_tracking() -> None:
    MLFLOW_RUNTIME_TRACKER.flush()


def runtime_tracking_status() -> dict[str, object]:
    return MLFLOW_RUNTIME_TRACKER.status()
