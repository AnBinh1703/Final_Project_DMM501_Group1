from __future__ import annotations

import time
from contextlib import contextmanager

from prometheus_client import Counter, Histogram

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


def record_prediction(score: float, tier: str, action: str) -> None:
    PREDICTIONS_TOTAL.labels(tier=str(tier)).inc()
    ACTION_TOTAL.labels(action=str(action)).inc()
    SCORES_SUM.inc(score)
    SCORES_COUNT.inc(1)
