from __future__ import annotations

from pydantic import BaseModel, Field


MetadataValue = str | int | float | bool | None


class PredictRequest(BaseModel):
    transaction_id: str | None = Field(
        None,
        max_length=128,
        description="Optional upstream banking transaction identifier.",
    )
    timestamp: str | None = Field(
        None,
        description="Optional transaction timestamp (ISO-8601 preferred).",
    )
    amount: float | None = Field(
        None,
        ge=0.0,
        description="Optional transaction amount. If missing, backend attempts feature-derived fallback.",
    )
    channel: str | None = Field(
        None,
        max_length=64,
        description="Optional banking channel (mobile_app, internet_banking, atm, branch, etc.).",
    )
    features: list[float] | None = Field(None, min_length=1, description="Ordered feature vector")
    features_by_name: dict[str, float] | None = Field(
        None,
        description="Feature values keyed by feature name. If provided, the API will order features using the model's "
        "expected feature_columns.",
    )
    metadata: dict[str, MetadataValue] | None = Field(
        None,
        description=(
            "Optional contextual signals for reason-code heuristics, e.g. "
            "velocity_1h, new_beneficiary, device_mismatch, geo_anomaly, ato_pattern."
        ),
    )


class PredictResponse(BaseModel):
    request_id: str
    transaction_id: str | None = None
    timestamp: str = Field(..., description="Timestamp used by the decision-support workflow.")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Uncalibrated risk score in [0,1].")
    risk_tier: str = Field(..., description="Decision tier derived from thresholds: LOW, REVIEW, HIGH.")
    action: str = Field(..., description="Suggested action: allow, review, block.")
    decision_recommendation: str = Field(
        ...,
        description="Decision recommendation for operations: ALLOW, STEP_UP_AUTH, MANUAL_REVIEW, HOLD, BLOCK.",
    )
    decision_label: str = Field(
        ...,
        description="Legacy decision label (ALLOW/REVIEW/BLOCK) kept for backward compatibility.",
    )
    decision_explanation: str = Field(..., description="Plain-language explanation of recommended handling.")
    reason_codes: list[str] = Field(
        default_factory=list,
        description="Interpretable reason codes (demo-level heuristics + policy-based indicators).",
    )
    reason_summary: str = Field(..., description="Plain-language summary derived from reason codes.")
    fraud_label: int = Field(
        ...,
        ge=0,
        le=1,
        description="Heuristic binary fraud indicator for backward compatibility. Not ground truth.",
    )
    case_status: str | None = Field(None, description="Case lifecycle status when alert/case is created.")
    alert_id: str | None = Field(None, description="Alert identifier when transaction is flagged.")
    case_id: str | None = Field(None, description="Case identifier when transaction is flagged.")
    threshold_review: float = Field(..., ge=0.0, le=1.0, description="Threshold to send to manual review.")
    threshold_high: float = Field(..., ge=0.0, le=1.0, description="Threshold to trigger high-risk auto action.")
    score_semantics: str = Field(..., description="Describes how to interpret risk_score (e.g., uncalibrated).")
    model_version: str
    model_type: str | None = None
    n_features: int | None = Field(None, ge=1)
    feature_names: list[str] | None = None
    selection_timestamp_utc: str | None = None


class FeatureSchemaResponse(BaseModel):
    n_features: int = Field(..., ge=1)
    feature_names: list[str] = Field(..., min_length=1)


class RandomFeaturesResponse(BaseModel):
    n_features: int = Field(..., ge=1)
    mode: str = Field(..., description="Generation mode actually used (e.g. 'creditcard' or 'normal').")
    seed: int | None = Field(None, description="Seed used for reproducible generation (if provided).")
    features: list[float] = Field(..., min_length=1, description="Ordered feature vector")
    time_s: float | None = Field(None, ge=0.0, description="Time feature for creditcard mode (seconds).")
    amount: float | None = Field(None, ge=0.0, description="Amount feature for creditcard mode.")


class DatasetSample(BaseModel):
    features: list[float] = Field(..., min_length=1, description="Ordered feature vector")
    time_s: float | None = Field(None, ge=0.0)
    amount: float | None = Field(None, ge=0.0)


class DatasetSamplesResponse(BaseModel):
    n_features: int = Field(..., ge=1)
    feature_names: list[str] = Field(..., min_length=1)
    dataset_path: str | None = None
    samples: list[DatasetSample] = Field(..., min_length=1)


class DatasetSampleWithLabel(BaseModel):
    features: list[float] = Field(..., min_length=1, description="Ordered feature vector")
    class_label: int = Field(..., ge=0, le=1, description="Ground truth label from the dataset (internal use only).")
    time_s: float | None = Field(None, ge=0.0)
    amount: float | None = Field(None, ge=0.0)


class DatasetSamplesWithLabelResponse(BaseModel):
    n_features: int = Field(..., ge=1)
    feature_names: list[str] = Field(..., min_length=1)
    dataset_path: str | None = None
    samples: list[DatasetSampleWithLabel] = Field(..., min_length=1)


class StreamScoredEvent(BaseModel):
    event_id: str
    event_time_utc: str
    source: str = Field(..., description="Event source (e.g., dataset or synthetic).")
    transaction_id: str | None = None
    features: list[float] = Field(..., min_length=1, description="Ordered feature vector (for re-score).")
    time_s: float | None = Field(None, ge=0.0)
    amount: float | None = Field(None, ge=0.0)

    risk_score: float = Field(..., ge=0.0, le=1.0, description="Uncalibrated risk score in [0,1].")
    risk_percentile: float | None = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Optional percentile rank of risk_score under a reference score distribution.",
    )
    risk_tier: str = Field(..., description="Decision tier derived from thresholds: LOW, REVIEW, HIGH.")
    action: str = Field(..., description="Suggested action: allow, review, block.")
    decision_label: str = Field(..., description="Decision label (ALLOW, REVIEW, BLOCK). Not ground truth.")
    decision_explanation: str | None = Field(None, description="Plain-language explanation of decision recommendation.")
    decision_recommendation: str | None = Field(
        None,
        description="Decision-support recommendation for operations.",
    )
    reason_codes: list[str] = Field(default_factory=list)
    case_status: str | None = None
    alert_id: str | None = None
    case_id: str | None = None


class StreamPullResponse(BaseModel):
    model_version: str
    model_type: str | None = None
    score_semantics: str = Field(..., description="Describes how to interpret risk_score (e.g., uncalibrated).")
    threshold_review: float = Field(..., ge=0.0, le=1.0)
    threshold_high: float = Field(..., ge=0.0, le=1.0)
    events: list[StreamScoredEvent] = Field(..., min_length=1)


class TimelineEvent(BaseModel):
    event_type: str
    event_time_utc: str
    actor: str = "system"
    details: dict[str, object] = Field(default_factory=dict)


class AlertResponseItem(BaseModel):
    alert_id: str
    case_id: str
    request_id: str
    transaction_id: str | None = None
    transaction_timestamp: str
    amount: float | None = None
    channel: str | None = None
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str
    decision_recommendation: str
    legacy_action: str
    reason_codes: list[str] = Field(default_factory=list)
    case_status: str
    analyst_note: str | None = None
    created_at: str
    updated_at: str


class AlertListResponse(BaseModel):
    total: int = Field(..., ge=0)
    alerts: list[AlertResponseItem] = Field(default_factory=list)


class UpdateAlertStatusRequest(BaseModel):
    case_status: str = Field(..., description="Target status for the linked case.")
    analyst_note: str | None = Field(None, description="Optional analyst note.")
    actor: str | None = Field(None, description="Actor performing the transition.")


class CaseResponseItem(BaseModel):
    case_id: str
    alert_id: str
    request_id: str
    transaction_id: str | None = None
    transaction_timestamp: str
    features: list[float] | None = None
    amount: float | None = None
    channel: str | None = None
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str
    decision_recommendation: str
    legacy_action: str
    reason_codes: list[str] = Field(default_factory=list)
    case_status: str
    analyst_note: str | None = None
    created_at: str
    updated_at: str
    model_version: str | None = None
    model_type: str | None = None
    score_semantics: str | None = None
    timeline: list[TimelineEvent] | None = None


class CaseListResponse(BaseModel):
    total: int = Field(..., ge=0)
    cases: list[CaseResponseItem] = Field(default_factory=list)


class UpdateCaseStatusRequest(BaseModel):
    case_status: str = Field(..., description="Target status for case lifecycle transition.")
    analyst_note: str | None = Field(None, description="Optional analyst note.")
    actor: str | None = Field(None, description="Actor performing the transition.")


class ResolveCaseRequest(BaseModel):
    resolution: str = Field(..., description="Resolution status (e.g., CONFIRMED_FRAUD, FALSE_POSITIVE, RESOLVED).")
    analyst_note: str | None = Field(None, description="Optional analyst resolution note.")
    actor: str | None = Field(None, description="Actor performing the resolution.")


class CaseTimelineResponse(BaseModel):
    case_id: str
    timeline: list[TimelineEvent] = Field(default_factory=list)


class AuditEventResponse(BaseModel):
    audit_id: str
    event_time_utc: str
    event_type: str
    actor: str
    role: str | None = None
    endpoint: str | None = None
    method: str | None = None
    status_code: int | None = None
    request_id: str | None = None
    case_id: str | None = None
    alert_id: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class AuditEventListResponse(BaseModel):
    total: int = Field(..., ge=0)
    events: list[AuditEventResponse] = Field(default_factory=list)
