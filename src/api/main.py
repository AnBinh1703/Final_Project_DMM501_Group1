from __future__ import annotations

from contextlib import asynccontextmanager
import math
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import RedirectResponse, Response

from src.api.schemas import (
    DatasetSamplesResponse,
    FeatureSchemaResponse,
    PredictRequest,
    PredictResponse,
    RandomFeaturesResponse,
)
from src.data.samples import resolve_dataset_path, sample_dataset_rows
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

_env_origins = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else []

_cors_kwargs: dict[str, object] = {
    "allow_credentials": False,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

if _cors_origins:
    # Explicit allowlist provided by environment.
    _cors_kwargs["allow_origins"] = _cors_origins
else:
    # Dev/demo-friendly default: allow any localhost port without opening CORS globally.
    _cors_kwargs["allow_origins"] = []
    _cors_kwargs["allow_origin_regex"] = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(CORSMiddleware, **_cors_kwargs)


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
        "threshold_review": loaded.threshold_review if loaded else None,
        "threshold_high": loaded.threshold_high if loaded else None,
        "model_type": loaded.model_type if loaded else None,
        "feature_names": loaded.feature_columns if loaded and loaded.feature_columns else None,
        "selection_timestamp_utc": loaded.selection_timestamp_utc if loaded else None,
        "score_semantics": loaded.score_semantics if loaded else None,
    }


def _resolve_expected_features() -> int:
    loaded = getattr(app.state, "loaded_model", None)
    n = loaded.n_features if loaded and loaded.n_features is not None else 30
    return int(n)


@app.get("/features/schema", response_model=FeatureSchemaResponse)
async def feature_schema() -> FeatureSchemaResponse:
    loaded = getattr(app.state, "loaded_model", None)
    if loaded and loaded.feature_columns:
        return FeatureSchemaResponse(n_features=len(loaded.feature_columns), feature_names=list(loaded.feature_columns))

    n_features = _resolve_expected_features()
    fallback = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"] if n_features == 30 else [f"feature_{i}" for i in range(n_features)]
    return FeatureSchemaResponse(n_features=n_features, feature_names=fallback)


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
        threshold_review = loaded.threshold_review
        threshold_high = loaded.threshold_high

        if req.features is None and req.features_by_name is None:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(status_code=422, detail="Request must include either 'features' or 'features_by_name'.")

        if req.features is not None and req.features_by_name is not None:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(status_code=422, detail="Provide only one of 'features' or 'features_by_name'.")

        if req.features is not None:
            features = req.features
        else:
            if not loaded.feature_columns:
                record_response(endpoint=endpoint, method=method, http_status=500)
                raise HTTPException(status_code=500, detail="Model metadata missing feature_columns; cannot use features_by_name.")
            missing = [k for k in loaded.feature_columns if k not in req.features_by_name]  # type: ignore[operator]
            extra = [k for k in req.features_by_name.keys() if k not in set(loaded.feature_columns)]  # type: ignore[union-attr]
            if missing:
                record_response(endpoint=endpoint, method=method, http_status=422)
                raise HTTPException(status_code=422, detail=f"features_by_name missing keys: {missing[:8]}{'...' if len(missing)>8 else ''}")
            if extra:
                record_response(endpoint=endpoint, method=method, http_status=422)
                raise HTTPException(status_code=422, detail=f"features_by_name contains unexpected keys: {extra[:8]}{'...' if len(extra)>8 else ''}")
            features = [float(req.features_by_name[name]) for name in loaded.feature_columns]  # type: ignore[index]

        if loaded.n_features is not None and len(features) != loaded.n_features:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid feature length: expected {loaded.n_features}, received {len(features)}",
            )

        if any((not isinstance(v, (int, float))) or (not math.isfinite(float(v))) for v in features):
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(status_code=422, detail="All features must be finite numeric values.")

        # Expect scikit-learn style predict_proba.
        if not hasattr(model, "predict_proba"):
            record_response(endpoint=endpoint, method=method, http_status=500)
            raise HTTPException(status_code=500, detail="Loaded model does not support predict_proba")

        X = preprocess_feature_vector(features)
        try:
            proba = float(model.predict_proba(X)[0][1])
        except ValueError as exc:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if proba >= threshold_high:
            risk_tier = "HIGH"
            action = "block"
            label = 1
        elif proba >= threshold_review:
            risk_tier = "REVIEW"
            action = "review"
            label = 0
        else:
            risk_tier = "LOW"
            action = "allow"
            label = 0

        record_prediction(score=proba, tier=risk_tier, action=action)
        record_response(endpoint=endpoint, method=method, http_status=200)

        return PredictResponse(
            request_id=new_request_id(),
            risk_score=proba,
            risk_tier=risk_tier,
            action=action,
            fraud_label=label,
            threshold_review=threshold_review,
            threshold_high=threshold_high,
            score_semantics=loaded.score_semantics,
            model_version=loaded.model_version,
            model_type=loaded.model_type,
            n_features=loaded.n_features,
            feature_names=list(loaded.feature_columns) if loaded.feature_columns else None,
            selection_timestamp_utc=loaded.selection_timestamp_utc,
        )


@app.get("/dataset/samples", response_model=DatasetSamplesResponse)
async def dataset_samples(
    n: int = 25,
    strategy: str = "mixed",
    seed: int | None = 42,
) -> DatasetSamplesResponse:
    loaded = getattr(app.state, "loaded_model", None)
    if loaded is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    if not loaded.dataset_path:
        raise HTTPException(status_code=404, detail="Model metadata did not record dataset_path.")
    if not loaded.feature_columns:
        raise HTTPException(status_code=500, detail="Model metadata missing feature_columns.")

    repo_root = Path(__file__).resolve().parents[2]
    dataset_path = resolve_dataset_path(loaded.dataset_path, repo_root=repo_root)
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_path}")

    n = int(n)
    if n < 1 or n > 500:
        raise HTTPException(status_code=422, detail="n must be between 1 and 500")

    try:
        samples = sample_dataset_rows(
            dataset_path=dataset_path,
            feature_columns=list(loaded.feature_columns),
            n=n,
            strategy=strategy,
            seed=seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Attach convenience fields for the common CreditCard dataset.
    try:
        time_idx = loaded.feature_columns.index("Time")
        amount_idx = loaded.feature_columns.index("Amount")
    except ValueError:
        time_idx = None
        amount_idx = None

    for s in samples:
        feats = s.get("features", [])
        if time_idx is not None and len(feats) > time_idx:
            s["time_s"] = float(feats[time_idx])
        if amount_idx is not None and len(feats) > amount_idx:
            s["amount"] = float(feats[amount_idx])

    return DatasetSamplesResponse(
        n_features=len(loaded.feature_columns),
        feature_names=list(loaded.feature_columns),
        dataset_path=str(dataset_path),
        samples=samples,  # type: ignore[arg-type]
    )
