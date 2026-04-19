from __future__ import annotations

from datetime import datetime


_REASON_TEXT = {
    "MODEL_HIGH_RISK_SCORE": "Model score exceeded the HIGH-risk policy threshold.",
    "MODEL_REVIEW_RISK_SCORE": "Model score exceeded the REVIEW policy threshold.",
    "MODEL_LOW_RISK_SCORE": "Model score is below investigation thresholds.",
    "HIGH_AMOUNT_ANOMALY": "Transaction amount is unusually high for baseline behavior.",
    "UNUSUAL_TIME_PATTERN": "Transaction happened at an atypical time window.",
    "HIGH_VELOCITY_TXNS": "Multiple transactions were reported in a short time window.",
    "NEW_BENEFICIARY": "Transfer targets a newly-added beneficiary.",
    "DEVICE_MISMATCH": "Device fingerprint differs from expected profile.",
    "GEO_ANOMALY": "Geographic pattern appears unusual.",
    "ATO_PATTERN": "Signals are consistent with account-takeover behavior.",
    "CHANNEL_ANOMALY": "Transaction channel is unusual for the account profile.",
}


_KNOWN_CHANNELS = {
    "mobile_app",
    "internet_banking",
    "atm",
    "branch",
    "api",
    "pos",
    "web",
}


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out:  # NaN check
        return None
    if out in (float("inf"), float("-inf")):
        return None
    return out


def _parse_hour_from_timestamp(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    try:
        # Accept both `YYYY-mm-dd HH:MM:SS` and ISO-8601.
        normalized = timestamp.replace(" ", "T")
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return int(dt.hour)


def _amount_from_features(feature_vector: list[float], feature_names: list[str] | None) -> float | None:
    if not feature_vector:
        return None

    if feature_names and "Amount" in feature_names:
        idx = feature_names.index("Amount")
        if idx < len(feature_vector):
            return _safe_float(feature_vector[idx])

    # Credit-card fallback convention: final column is Amount.
    return _safe_float(feature_vector[-1])


def _time_hour_from_features(feature_vector: list[float], feature_names: list[str] | None) -> int | None:
    if feature_names and "Time" in feature_names:
        idx = feature_names.index("Time")
        if idx < len(feature_vector):
            sec = _safe_float(feature_vector[idx])
            if sec is None:
                return None
            # Dataset uses elapsed seconds; map into 24h clock for demo heuristics.
            return int((sec % 86400.0) // 3600.0)
    return None


def generate_reason_codes(
    *,
    score: float,
    risk_tier: str,
    threshold_review: float,
    threshold_high: float,
    feature_vector: list[float],
    feature_names: list[str] | None,
    amount: float | None,
    timestamp: str | None,
    channel: str | None,
    metadata: dict[str, object] | None,
) -> list[str]:
    """
    Demo-level reason-code generator.

    This implementation mixes policy-based reason codes (always available) with optional
    metadata/heuristic signals. It is intentionally labeled as heuristic and should not be
    interpreted as a causal explanation engine.
    """
    reasons: list[str] = []

    if risk_tier == "HIGH" and score >= threshold_high:
        reasons.append("MODEL_HIGH_RISK_SCORE")
    elif risk_tier == "REVIEW" and score >= threshold_review:
        reasons.append("MODEL_REVIEW_RISK_SCORE")
    else:
        reasons.append("MODEL_LOW_RISK_SCORE")

    resolved_amount = _safe_float(amount)
    if resolved_amount is None:
        resolved_amount = _amount_from_features(feature_vector, feature_names)

    if resolved_amount is not None and resolved_amount >= 1000.0:
        reasons.append("HIGH_AMOUNT_ANOMALY")

    hour = _parse_hour_from_timestamp(timestamp)
    if hour is None:
        hour = _time_hour_from_features(feature_vector, feature_names)
    if hour is not None and (hour < 5 or hour >= 23):
        reasons.append("UNUSUAL_TIME_PATTERN")

    md = metadata or {}
    velocity_1h = _safe_float(md.get("velocity_1h"))
    if bool(md.get("high_velocity_txns")) or (velocity_1h is not None and velocity_1h >= 5.0):
        reasons.append("HIGH_VELOCITY_TXNS")

    if bool(md.get("new_beneficiary")):
        reasons.append("NEW_BENEFICIARY")
    if bool(md.get("device_mismatch")):
        reasons.append("DEVICE_MISMATCH")
    if bool(md.get("geo_anomaly")):
        reasons.append("GEO_ANOMALY")
    if bool(md.get("ato_pattern")):
        reasons.append("ATO_PATTERN")

    normalized_channel = str(channel).strip().lower() if channel is not None else None
    if normalized_channel and normalized_channel not in _KNOWN_CHANNELS:
        reasons.append("CHANNEL_ANOMALY")

    # Preserve order while removing duplicates.
    deduped: list[str] = []
    seen: set[str] = set()
    for r in reasons:
        if r in seen:
            continue
        deduped.append(r)
        seen.add(r)

    return deduped


def summarize_reason_codes(reason_codes: list[str]) -> str:
    if not reason_codes:
        return "No explicit reason code generated."

    phrases = [_REASON_TEXT.get(code, code.replace("_", " ").title()) for code in reason_codes]
    return "; ".join(phrases)
