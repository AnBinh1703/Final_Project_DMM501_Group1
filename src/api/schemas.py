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
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    fraud_label: int = Field(..., ge=0, le=1)
    threshold: float = Field(..., ge=0.0, le=1.0)
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
    class_label: int | None = Field(None, ge=0, le=1, description="Ground truth label from the dataset (if available).")
    time_s: float | None = Field(None, ge=0.0)
    amount: float | None = Field(None, ge=0.0)


class DatasetSamplesResponse(BaseModel):
    n_features: int = Field(..., ge=1)
    feature_names: list[str] = Field(..., min_length=1)
    dataset_path: str | None = None
    samples: list[DatasetSample] = Field(..., min_length=1)
