from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    features: list[float] | None = Field(None, min_length=1, description="Ordered feature vector")
    features_by_name: dict[str, float] | None = Field(
        None,
        description="Feature values keyed by feature name. If provided, the API will order features using the model's "
        "expected feature_columns.",
    )


class PredictResponse(BaseModel):
    request_id: str
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Uncalibrated risk score in [0,1].")
    risk_tier: str = Field(..., description="Decision tier derived from thresholds: LOW, REVIEW, HIGH.")
    action: str = Field(..., description="Suggested action: allow, review, block.")
    decision_label: str = Field(
        ...,
        description="Decision label derived from the policy (ALLOW, REVIEW, BLOCK). HIGH tier is not confirmed fraud.",
    )
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


class StreamPullResponse(BaseModel):
    model_version: str
    model_type: str | None = None
    score_semantics: str = Field(..., description="Describes how to interpret risk_score (e.g., uncalibrated).")
    threshold_review: float = Field(..., ge=0.0, le=1.0)
    threshold_high: float = Field(..., ge=0.0, le=1.0)
    events: list[StreamScoredEvent] = Field(..., min_length=1)
