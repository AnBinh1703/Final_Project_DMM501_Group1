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
    "Number of fraud predictions",
    ["label"],
)

SCORES_SUM = Counter(
    "fraud_scores_sum",
    "Sum of fraud scores (for average computation)",
)

SCORES_COUNT = Counter(
    "fraud_scores_count",
    "Count of fraud scores (for average computation)",
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


def record_prediction(score: float, label: int) -> None:
    PREDICTIONS_TOTAL.labels(label=str(int(label))).inc()
    SCORES_SUM.inc(score)
    SCORES_COUNT.inc(1)
