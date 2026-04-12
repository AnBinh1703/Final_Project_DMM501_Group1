from __future__ import annotations

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    # Placeholder schema: will be aligned to the chosen dataset schema.
    # Keep generic and numeric to start.
    features: list[float] = Field(..., min_length=1, description="Ordered feature vector")


class PredictResponse(BaseModel):
    request_id: str
    fraud_probability: float = Field(..., ge=0.0, le=1.0)
    fraud_label: int = Field(..., ge=0, le=1)
    threshold: float = Field(..., ge=0.0, le=1.0)
    model_version: str
