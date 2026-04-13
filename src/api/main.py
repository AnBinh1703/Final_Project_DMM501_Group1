from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import RedirectResponse, Response

from src.api.schemas import (
    FeatureSchemaResponse,
    PredictRequest,
    PredictResponse,
    RandomFeaturesResponse,
)
from src.features.preprocess import preprocess_feature_vector
from src.features.random_features import generate_random_features
from src.models.loader import maybe_load_model_from_env
from src.monitoring.metrics import (
    record_prediction,
    record_response,
    track_request,
)
from src.utils.ids import new_request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load at startup so tests/containers can set MODEL_PATH before app boot.
    app.state.loaded_model = maybe_load_model_from_env()
    yield
    app.state.loaded_model = None


app = FastAPI(title="Fraud Detection API", version="1.0.0", lifespan=lifespan)

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


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    # Browsers often hit `/` first. Redirect to Swagger UI for a better demo experience.
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health() -> dict:
    loaded = getattr(app.state, "loaded_model", None)
    return {
        "status": "ok",
        "model_loaded": loaded is not None,
        "model_version": loaded.model_version if loaded else None,
        "expected_features": loaded.n_features if loaded else None,
    }


def _resolve_expected_features() -> int:
    loaded = getattr(app.state, "loaded_model", None)
    n = loaded.n_features if loaded and loaded.n_features is not None else 30
    return int(n)


@app.get("/features/schema", response_model=FeatureSchemaResponse)
async def feature_schema() -> FeatureSchemaResponse:
    n_features = _resolve_expected_features()
    if n_features == 30:
        feature_names = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
    else:
        feature_names = [f"feature_{i}" for i in range(n_features)]
    return FeatureSchemaResponse(n_features=n_features, feature_names=feature_names)


@app.get("/features/random", response_model=RandomFeaturesResponse)
async def random_features(
    seed: int | None = None, mode: str = "auto", n_features: int | None = None
) -> RandomFeaturesResponse:
    allowed_modes = {"auto", "creditcard", "normal"}
    if mode not in allowed_modes:
        raise HTTPException(status_code=422, detail=f"Invalid mode '{mode}'. Allowed: {sorted(allowed_modes)}")

    resolved_n = int(n_features) if n_features is not None else _resolve_expected_features()
    if resolved_n < 1:
        raise HTTPException(status_code=422, detail="n_features must be >= 1")

    try:
        result = generate_random_features(n_features=resolved_n, mode=mode, seed=seed)  # type: ignore[arg-type]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if len(result.features) != resolved_n:
        raise HTTPException(status_code=500, detail="Random feature generator produced invalid feature length")

    return RandomFeaturesResponse(
        n_features=resolved_n,
        mode=result.mode,
        seed=seed,
        features=result.features,
        time_s=result.time_s,
        amount=result.amount,
    )


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest) -> PredictResponse:
    endpoint = "/predict"
    method = "POST"

    with track_request(endpoint=endpoint, method=method):
        loaded = getattr(app.state, "loaded_model", None)
        if loaded is None:
            record_response(endpoint=endpoint, method=method, http_status=503)
            raise HTTPException(status_code=503, detail="Model not loaded. Set MODEL_PATH and restart.")

        model = loaded.model
        threshold = loaded.threshold

        if loaded.n_features is not None and len(req.features) != loaded.n_features:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid feature length: expected {loaded.n_features}, received {len(req.features)}",
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
            model_version=loaded.model_version,
        )
