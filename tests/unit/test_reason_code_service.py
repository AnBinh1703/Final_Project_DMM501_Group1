import math

from src.services.reason_code_service import (
    _amount_from_features,
    _parse_hour_from_timestamp,
    _safe_float,
    _time_hour_from_features,
    generate_reason_codes,
    summarize_reason_codes,
)


def test_safe_float_handles_valid_and_invalid_values() -> None:
    assert _safe_float(1) == 1.0
    assert _safe_float("2.5") == 2.5
    assert _safe_float(None) is None
    assert _safe_float("bad") is None
    assert _safe_float(float("nan")) is None
    assert _safe_float(float("inf")) is None
    assert _safe_float(float("-inf")) is None


def test_parse_hour_from_timestamp_accepts_common_formats() -> None:
    assert _parse_hour_from_timestamp("2026-04-20 23:10:00") == 23
    assert _parse_hour_from_timestamp("2026-04-20T04:15:00") == 4
    assert _parse_hour_from_timestamp("not-a-timestamp") is None
    assert _parse_hour_from_timestamp(None) is None


def test_amount_and_time_extractors_handle_named_and_fallback_paths() -> None:
    features = [3600.0, 1500.0]
    names = ["Time", "Amount"]

    assert _amount_from_features(features, names) == 1500.0
    assert _amount_from_features([1.0, 2500.0], None) == 2500.0
    assert _amount_from_features([], names) is None
    assert _time_hour_from_features(features, names) == 1
    assert _time_hour_from_features(["bad"], ["Time"]) is None


def test_generate_reason_codes_includes_policy_and_signal_reasons_with_dedupe() -> None:
    reasons = generate_reason_codes(
        score=0.96,
        risk_tier="HIGH",
        threshold_review=0.5,
        threshold_high=0.9,
        feature_vector=[120.0, 2500.0],
        feature_names=["Time", "Amount"],
        amount=None,
        timestamp=None,
        channel="kiosk",
        metadata={
            "high_velocity_txns": True,
            "velocity_1h": 9,
            "new_beneficiary": True,
            "device_mismatch": True,
            "geo_anomaly": True,
            "ato_pattern": True,
        },
    )

    assert reasons[0] == "MODEL_HIGH_RISK_SCORE"
    assert "HIGH_AMOUNT_ANOMALY" in reasons
    assert "UNUSUAL_TIME_PATTERN" in reasons
    assert "HIGH_VELOCITY_TXNS" in reasons
    assert "NEW_BENEFICIARY" in reasons
    assert "DEVICE_MISMATCH" in reasons
    assert "GEO_ANOMALY" in reasons
    assert "ATO_PATTERN" in reasons
    assert "CHANNEL_ANOMALY" in reasons
    assert reasons.count("HIGH_VELOCITY_TXNS") == 1


def test_generate_reason_codes_review_and_low_paths() -> None:
    review_reasons = generate_reason_codes(
        score=0.8,
        risk_tier="REVIEW",
        threshold_review=0.6,
        threshold_high=0.9,
        feature_vector=[100.0],
        feature_names=["Amount"],
        amount=100.0,
        timestamp="2026-04-20T12:00:00",
        channel="web",
        metadata=None,
    )
    low_reasons = generate_reason_codes(
        score=0.1,
        risk_tier="HIGH",
        threshold_review=0.6,
        threshold_high=0.9,
        feature_vector=[100.0],
        feature_names=["Amount"],
        amount=100.0,
        timestamp="2026-04-20T12:00:00",
        channel="mobile_app",
        metadata={},
    )

    assert review_reasons[0] == "MODEL_REVIEW_RISK_SCORE"
    assert low_reasons[0] == "MODEL_LOW_RISK_SCORE"


def test_summarize_reason_codes_for_known_unknown_and_empty_codes() -> None:
    summary = summarize_reason_codes(["MODEL_HIGH_RISK_SCORE", "CUSTOM_UNKNOWN_CODE"])
    assert "HIGH-risk policy" in summary
    assert "Custom Unknown Code" in summary

    empty_summary = summarize_reason_codes([])
    assert empty_summary == "No explicit reason code generated."


def test_safe_float_rejects_nan_from_string() -> None:
    assert _safe_float(str(math.nan)) is None
