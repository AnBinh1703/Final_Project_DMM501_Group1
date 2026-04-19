from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionResult:
    risk_tier: str
    action: str
    decision_recommendation: str
    decision_label: str
    decision_explanation: str
    fraud_label: int


_DIGITAL_CHANNELS = {
    "mobile_app",
    "internet_banking",
    "web",
    "api",
    "card_not_present",
}


def _normalize_channel(channel: str | None) -> str | None:
    if channel is None:
        return None
    cleaned = str(channel).strip().lower()
    return cleaned or None


def decide_risk_action(
    *,
    score: float,
    threshold_review: float,
    threshold_high: float,
    amount: float | None = None,
    channel: str | None = None,
) -> DecisionResult:
    """
    Policy engine for risk tier and recommendation mapping.

    `action` is a backward-compatible field (`allow|review|block`) for existing clients.
    `decision_recommendation` is the richer decision-support action used by analyst workflows.
    """
    normalized_channel = _normalize_channel(channel)

    if score >= threshold_high:
        recommendation = "BLOCK" if amount is not None and amount >= 1500.0 else "HOLD"
        return DecisionResult(
            risk_tier="HIGH",
            action="block",
            decision_recommendation=recommendation,
            decision_label="BLOCK",
            decision_explanation="High-risk transaction flagged for immediate containment.",
            fraud_label=1,
        )

    if score >= threshold_review:
        recommendation = "STEP_UP_AUTH" if normalized_channel in _DIGITAL_CHANNELS else "MANUAL_REVIEW"
        return DecisionResult(
            risk_tier="REVIEW",
            action="review",
            decision_recommendation=recommendation,
            decision_label="REVIEW",
            decision_explanation="Transaction flagged for enhanced verification.",
            fraud_label=0,
        )

    return DecisionResult(
        risk_tier="LOW",
        action="allow",
        decision_recommendation="ALLOW",
        decision_label="ALLOW",
        decision_explanation="No additional intervention required.",
        fraud_label=0,
    )
