from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from src.api.schemas import PredictRequest, PredictResponse
from src.features.preprocess import preprocess_feature_vector
from src.models.loader import maybe_load_model_from_env
from src.monitoring.metrics import (
    record_prediction,
    record_response,
    track_request,
)
from src.utils.ids import new_request_id

app = FastAPI(title="Fraud Detection API", version="0.1.0")

_default_origins = ["http://localhost:8080", "http://127.0.0.1:8080"]
_env_origins = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_loaded = maybe_load_model_from_env()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_loaded": _loaded is not None,
        "model_version": _loaded.model_version if _loaded else None,
        "expected_features": _loaded.n_features if _loaded else None,
    }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    endpoint = "/predict"
    method = "POST"

    with track_request(endpoint=endpoint, method=method):
        if _loaded is None:
            record_response(endpoint=endpoint, method=method, http_status=503)
            raise HTTPException(status_code=503, detail="Model not loaded. Set MODEL_PATH and restart.")

        model = _loaded.model
        threshold = _loaded.threshold

        if _loaded.n_features is not None and len(req.features) != _loaded.n_features:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid feature length: expected {_loaded.n_features}, received {len(req.features)}",
            )

        # Expect scikit-learn style predict_proba.
        if not hasattr(model, "predict_proba"):
            record_response(endpoint=endpoint, method=method, http_status=500)
            raise HTTPException(status_code=500, detail="Loaded model does not support predict_proba")

        X = preprocess_feature_vector(req.features)
        try:
            proba = float(model.predict_proba(X)[0][1])
        except ValueError as exc:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        label = int(proba >= threshold)

        record_prediction(score=proba, label=label)
        record_response(endpoint=endpoint, method=method, http_status=200)

        return PredictResponse(
            request_id=new_request_id(),
            fraud_probability=proba,
            fraud_label=label,
            threshold=threshold,
            model_version=_loaded.model_version,
        )
