from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import RedirectResponse, Response

from src.api.schemas import (
    AlertListResponse,
    AlertResponseItem,
    AuditEventListResponse,
    CaseListResponse,
    CaseResponseItem,
    CaseTimelineResponse,
    DatasetSamplesResponse,
    DatasetSamplesWithLabelResponse,
    FeatureSchemaResponse,
    PredictRequest,
    PredictResponse,
    RandomFeaturesResponse,
    ResolveCaseRequest,
    StreamPullResponse,
    UpdateAlertStatusRequest,
    UpdateCaseStatusRequest,
)
from src.data.samples import resolve_dataset_path, sample_dataset_rows
from src.features.random_features import generate_random_features
from src.models.loader import maybe_load_model_from_env
from src.monitoring.metrics import (
    record_alert_created,
    record_case_status,
    record_prediction,
    record_response,
    set_review_queue_size,
    track_request,
)
from src.repositories.case_lifecycle import VALID_CASE_STATUSES
from src.repositories.factory import build_case_repository_from_env
from src.security.audit import append_audit_event_from_request
from src.security.auth import ADMIN_ROLES, ANALYST_ROLES, READ_ROLES, AuthContext, require_roles, validate_auth_configuration
from src.security.rate_limit import RateLimitMiddleware
from src.services.case_service import CaseService
from src.services.decision_service import decide_risk_action
from src.services.reason_code_service import generate_reason_codes, summarize_reason_codes
from src.services.scoring_service import score_transaction, validate_feature_vector
from src.streaming.simulator import StreamConfig, StreamSimulator
from src.utils.ids import new_request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_configuration()

    # Load at startup so tests/containers can set MODEL_PATH before app boot.
    app.state.loaded_model = maybe_load_model_from_env()
    loaded = getattr(app.state, "loaded_model", None)

    stream_simulator = None
    if loaded is not None:
        repo_root = Path(__file__).resolve().parents[2]
        dataset_path = None
        if loaded.dataset_path:
            p = resolve_dataset_path(str(loaded.dataset_path), repo_root=repo_root)
            if p.exists():
                dataset_path = p

        feature_columns = list(loaded.feature_columns) if loaded.feature_columns else ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
        cfg = StreamConfig(
            base_fraud_rate=float(loaded.fraud_base_rate) if getattr(loaded, "fraud_base_rate", None) is not None else float(os.getenv("STREAM_BASE_FRAUD_RATE", "0.0017")),
            base_transactions_per_second=float(os.getenv("STREAM_BASE_TPS", "1.2")),
            burst_transactions_per_second=float(os.getenv("STREAM_BURST_TPS", "14.0")),
        )
        stream_simulator = StreamSimulator(
            dataset_path=dataset_path,
            feature_columns=feature_columns,
            seed=int(os.getenv("STREAM_SEED", "42")),
            config=cfg,
        )

    app.state.stream_simulator = stream_simulator
    app.state.case_service = CaseService(build_case_repository_from_env())
    set_review_queue_size(app.state.case_service.review_queue_size())

    yield

    app.state.loaded_model = None
    app.state.stream_simulator = None
    app.state.case_service = None


app = FastAPI(title="Fraud Detection API", version="2.0.0", lifespan=lifespan)

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
app.add_middleware(RateLimitMiddleware)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    # Browsers often hit `/` first. Redirect to Swagger UI for a better demo experience.
    return RedirectResponse(url="/docs")


def _resolve_expected_features() -> int:
    loaded = getattr(app.state, "loaded_model", None)
    n = loaded.n_features if loaded and loaded.n_features is not None else 30
    return int(n)


def _require_internal_token(x_internal_token: str | None) -> None:
    expected = os.getenv("INTERNAL_EVAL_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=404, detail="Internal evaluation endpoint disabled.")
    if not x_internal_token or x_internal_token.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid internal token.")


def _normalize_timestamp(raw: str | None) -> str:
    if raw is None:
        return datetime.now(UTC).isoformat()

    value = str(raw).strip()
    if not value:
        return datetime.now(UTC).isoformat()

    normalized = value.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid timestamp. Use ISO-8601 format.") from exc
    return dt.isoformat()


def _safe_amount(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="amount must be numeric.") from exc
    if out < 0.0:
        raise HTTPException(status_code=422, detail="amount must be >= 0.")
    if out in (float("inf"), float("-inf")) or out != out:
        raise HTTPException(status_code=422, detail="amount must be finite.")
    return out


def _extract_amount_from_features(features: list[float], feature_names: list[str] | None) -> float | None:
    if not features:
        return None

    if feature_names and "Amount" in feature_names:
        idx = feature_names.index("Amount")
        if idx < len(features):
            val = float(features[idx])
            if val >= 0.0:
                return val

    # Credit-card fallback convention: final column is Amount.
    val = float(features[-1])
    return val if val >= 0.0 else None


def _resolve_features(req: PredictRequest, loaded: Any) -> list[float]:
    if req.features is None and req.features_by_name is None:
        raise HTTPException(status_code=422, detail="Request must include either 'features' or 'features_by_name'.")

    if req.features is not None and req.features_by_name is not None:
        raise HTTPException(status_code=422, detail="Provide only one of 'features' or 'features_by_name'.")

    if req.features is not None:
        return [float(v) for v in req.features]

    if not loaded.feature_columns:
        raise HTTPException(status_code=500, detail="Model metadata missing feature_columns; cannot use features_by_name.")

    by_name = req.features_by_name or {}
    expected = list(loaded.feature_columns)
    expected_set = set(expected)

    missing = [k for k in expected if k not in by_name]
    extra = [k for k in by_name.keys() if k not in expected_set]
    if missing:
        raise HTTPException(status_code=422, detail=f"features_by_name missing keys: {missing[:8]}{'...' if len(missing)>8 else ''}")
    if extra:
        raise HTTPException(status_code=422, detail=f"features_by_name contains unexpected keys: {extra[:8]}{'...' if len(extra)>8 else ''}")

    try:
        return [float(by_name[name]) for name in expected]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="features_by_name values must be numeric.") from exc


def _parse_status_filter(status: str | None) -> set[str] | None:
    if status is None or not str(status).strip():
        return None

    tokens = {s.strip().upper() for s in str(status).split(",") if s.strip()}
    invalid = tokens - VALID_CASE_STATUSES
    if invalid:
        raise HTTPException(status_code=422, detail=f"Unsupported status filters: {sorted(invalid)}")
    return tokens


@app.get("/health")
async def health() -> dict:
    loaded = getattr(app.state, "loaded_model", None)
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    queue_size = case_service.review_queue_size() if case_service is not None else 0

    return {
        "status": "ok",
        "model_loaded": loaded is not None,
        "model_version": loaded.model_version if loaded else None,
        "expected_features": loaded.n_features if loaded else None,
        "threshold_review": loaded.threshold_review if loaded else None,
        "threshold_high": loaded.threshold_high if loaded else None,
        "threshold_policy": loaded.threshold_policy if loaded else None,
        "model_type": loaded.model_type if loaded else None,
        "feature_names": loaded.feature_columns if loaded and loaded.feature_columns else None,
        "selection_timestamp_utc": loaded.selection_timestamp_utc if loaded else None,
        "score_semantics": loaded.score_semantics if loaded else None,
        "fraud_base_rate": loaded.fraud_base_rate if loaded else None,
        "case_repository_mode": case_service.persistence_mode if case_service is not None else None,
        "review_queue_size": queue_size,
    }


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
async def predict(
    req: PredictRequest,
    request: Request,
    auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> PredictResponse:
    endpoint = "/predict"
    method = "POST"

    with track_request(endpoint=endpoint, method=method):
        loaded = getattr(app.state, "loaded_model", None)
        if loaded is None:
            record_response(endpoint=endpoint, method=method, http_status=503)
            raise HTTPException(status_code=503, detail="Model not loaded. Set MODEL_PATH and restart.")

        try:
            features = _resolve_features(req, loaded)
        except HTTPException as exc:
            record_response(endpoint=endpoint, method=method, http_status=exc.status_code)
            raise

        if loaded.n_features is not None and len(features) != loaded.n_features:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(
                status_code=422,
                detail=f"Invalid feature length: expected {loaded.n_features}, received {len(features)}",
            )

        try:
            validate_feature_vector(features)
        except ValueError as exc:
            record_response(endpoint=endpoint, method=method, http_status=422)
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            score = score_transaction(model=loaded.model, features=features)
        except ValueError as exc:
            code = 500 if "predict_proba" in str(exc) else 422
            record_response(endpoint=endpoint, method=method, http_status=code)
            raise HTTPException(status_code=code, detail=str(exc)) from exc

        threshold_review = float(loaded.threshold_review)
        threshold_high = float(loaded.threshold_high)

        transaction_timestamp = _normalize_timestamp(req.timestamp)
        amount = _safe_amount(req.amount)
        if amount is None:
            amount = _extract_amount_from_features(features, list(loaded.feature_columns) if loaded.feature_columns else None)

        channel = str(req.channel).strip() if req.channel is not None else None
        if channel == "":
            channel = None

        decision = decide_risk_action(
            score=float(score),
            threshold_review=threshold_review,
            threshold_high=threshold_high,
            amount=amount,
            channel=channel,
        )

        reason_codes = generate_reason_codes(
            score=float(score),
            risk_tier=decision.risk_tier,
            threshold_review=threshold_review,
            threshold_high=threshold_high,
            feature_vector=features,
            feature_names=list(loaded.feature_columns) if loaded.feature_columns else None,
            amount=amount,
            timestamp=transaction_timestamp,
            channel=channel,
            metadata=dict(req.metadata or {}),
        )
        reason_summary = summarize_reason_codes(reason_codes)

        request_id = new_request_id()
        case_service: CaseService | None = getattr(app.state, "case_service", None)
        alert_record: dict[str, Any] | None = None
        case_record: dict[str, Any] | None = None
        if case_service is not None:
            alert_record, case_record = case_service.create_from_prediction(
                request_id=request_id,
                transaction_id=req.transaction_id,
                transaction_timestamp=transaction_timestamp,
                features=features,
                amount=amount,
                channel=channel,
                risk_score=float(score),
                risk_tier=decision.risk_tier,
                decision_recommendation=decision.decision_recommendation,
                legacy_action=decision.action,
                reason_codes=reason_codes,
                model_version=loaded.model_version,
                model_type=loaded.model_type,
                score_semantics=loaded.score_semantics,
            )
            if case_record is not None:
                record_alert_created(tier=decision.risk_tier, case_status=str(case_record["case_status"]))
                record_case_status(str(case_record["case_status"]))
                append_audit_event_from_request(
                    request,
                    event_type="CASE_CREATED_FROM_PREDICTION",
                    status_code=200,
                    request_id=request_id,
                    case_id=str(case_record["case_id"]),
                    alert_id=str(alert_record["alert_id"]) if alert_record is not None else None,
                    actor=auth_ctx.actor,
                    role=auth_ctx.role,
                    details={
                        "risk_tier": decision.risk_tier,
                        "decision_recommendation": decision.decision_recommendation,
                    },
                )
            set_review_queue_size(case_service.review_queue_size())

        record_prediction(
            score=float(score),
            tier=decision.risk_tier,
            action=decision.action,
            decision_recommendation=decision.decision_recommendation,
        )
        record_response(endpoint=endpoint, method=method, http_status=200)

        return PredictResponse(
            request_id=request_id,
            transaction_id=req.transaction_id,
            timestamp=transaction_timestamp,
            risk_score=float(score),
            risk_tier=decision.risk_tier,
            action=decision.action,
            decision_recommendation=decision.decision_recommendation,
            decision_label=decision.decision_label,
            decision_explanation=decision.decision_explanation,
            reason_codes=reason_codes,
            reason_summary=reason_summary,
            fraud_label=decision.fraud_label,
            case_status=str(case_record["case_status"]) if case_record is not None else None,
            alert_id=str(alert_record["alert_id"]) if alert_record is not None else None,
            case_id=str(case_record["case_id"]) if case_record is not None else None,
            threshold_review=threshold_review,
            threshold_high=threshold_high,
            score_semantics=loaded.score_semantics,
            model_version=loaded.model_version,
            model_type=loaded.model_type,
            n_features=loaded.n_features,
            feature_names=list(loaded.feature_columns) if loaded.feature_columns else None,
            selection_timestamp_utc=loaded.selection_timestamp_utc,
        )


@app.get("/stream/pull", response_model=StreamPullResponse)
async def stream_pull(
    pace_ms: int = 1000,
    max_events: int = 75,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> StreamPullResponse:
    """
    Pull-style ingestion endpoint: returns already-scored transactions.

    This prevents the demo frontend from fetching dataset rows (and any potential labels) directly.
    """
    endpoint = "/stream/pull"
    method = "GET"

    with track_request(endpoint=endpoint, method=method):
        loaded = getattr(app.state, "loaded_model", None)
        sim = getattr(app.state, "stream_simulator", None)
        if loaded is None or sim is None:
            record_response(endpoint=endpoint, method=method, http_status=503)
            raise HTTPException(status_code=503, detail="Stream not available (model not loaded).")

        model = loaded.model
        if not hasattr(model, "predict_proba"):
            record_response(endpoint=endpoint, method=method, http_status=500)
            raise HTTPException(status_code=500, detail="Loaded model does not support predict_proba")

        events = sim.pull(pace_ms=int(pace_ms), max_events=int(max_events))
        if not events:
            record_response(endpoint=endpoint, method=method, http_status=500)
            raise HTTPException(status_code=500, detail="Stream simulator returned no events.")

        X = np.asarray([e["features"] for e in events], dtype=float)
        scores = model.predict_proba(X)[:, 1]

        threshold_review = float(loaded.threshold_review)
        threshold_high = float(loaded.threshold_high)

        percentiles = getattr(loaded, "score_percentiles", None)
        percentile_values = percentiles if isinstance(percentiles, list) and percentiles else None

        def score_to_percentile(s: float) -> float | None:
            if not percentile_values:
                return None
            lo = 0
            hi = len(percentile_values) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if s >= float(percentile_values[mid]):
                    lo = mid
                else:
                    hi = mid - 1
            return float(lo)

        case_service: CaseService | None = getattr(app.state, "case_service", None)
        enriched: list[dict[str, Any]] = []

        for e, s in zip(events, scores):
            score = float(s)
            amount = _safe_amount(float(e["amount"])) if e.get("amount") is not None else None
            event_timestamp = str(e.get("event_time_utc") or datetime.now(UTC).isoformat())
            transaction_id = str(e.get("event_id")) if e.get("event_id") is not None else None

            decision = decide_risk_action(
                score=score,
                threshold_review=threshold_review,
                threshold_high=threshold_high,
                amount=amount,
                channel=None,
            )
            reason_codes = generate_reason_codes(
                score=score,
                risk_tier=decision.risk_tier,
                threshold_review=threshold_review,
                threshold_high=threshold_high,
                feature_vector=[float(v) for v in e["features"]],
                feature_names=list(loaded.feature_columns) if loaded.feature_columns else None,
                amount=amount,
                timestamp=event_timestamp,
                channel=None,
                metadata=None,
            )

            request_id = f"stream:{transaction_id}" if transaction_id is not None else new_request_id()
            alert_record: dict[str, Any] | None = None
            case_record: dict[str, Any] | None = None
            if case_service is not None:
                alert_record, case_record = case_service.create_from_prediction(
                    request_id=request_id,
                    transaction_id=transaction_id,
                    transaction_timestamp=event_timestamp,
                    features=[float(v) for v in e["features"]],
                    amount=amount,
                    channel=None,
                    risk_score=score,
                    risk_tier=decision.risk_tier,
                    decision_recommendation=decision.decision_recommendation,
                    legacy_action=decision.action,
                    reason_codes=reason_codes,
                    model_version=loaded.model_version,
                    model_type=loaded.model_type,
                    score_semantics=loaded.score_semantics,
                )
                if case_record is not None:
                    record_alert_created(tier=decision.risk_tier, case_status=str(case_record["case_status"]))
                    record_case_status(str(case_record["case_status"]))

            record_prediction(
                score=score,
                tier=decision.risk_tier,
                action=decision.action,
                decision_recommendation=decision.decision_recommendation,
            )

            enriched.append(
                {
                    **e,
                    "transaction_id": transaction_id,
                    "risk_score": score,
                    "risk_percentile": score_to_percentile(score),
                    "risk_tier": decision.risk_tier,
                    "action": decision.action,
                    "decision_label": decision.decision_label,
                    "decision_explanation": decision.decision_explanation,
                    "decision_recommendation": decision.decision_recommendation,
                    "reason_codes": reason_codes,
                    "case_status": str(case_record["case_status"]) if case_record is not None else None,
                    "alert_id": str(alert_record["alert_id"]) if alert_record is not None else None,
                    "case_id": str(case_record["case_id"]) if case_record is not None else None,
                }
            )

        if case_service is not None:
            set_review_queue_size(case_service.review_queue_size())

        record_response(endpoint=endpoint, method=method, http_status=200)
        return StreamPullResponse(
            model_version=loaded.model_version,
            model_type=loaded.model_type,
            score_semantics=loaded.score_semantics,
            threshold_review=threshold_review,
            threshold_high=threshold_high,
            events=enriched,  # type: ignore[arg-type]
        )


@app.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    status: str | None = None,
    limit: int = 100,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> AlertListResponse:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 1000")

    statuses = _parse_status_filter(status)
    alerts = case_service.list_alerts(statuses=statuses, limit=int(limit))
    return AlertListResponse(total=len(alerts), alerts=alerts)  # type: ignore[arg-type]


@app.get("/alerts/{alert_id}", response_model=AlertResponseItem)
async def get_alert(
    alert_id: str,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> AlertResponseItem:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    alert = case_service.get_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")
    return AlertResponseItem(**alert)


@app.post("/alerts/{alert_id}/status", response_model=CaseResponseItem)
async def update_alert_status(
    alert_id: str,
    req: UpdateAlertStatusRequest,
    request: Request,
    auth_ctx: AuthContext = Depends(require_roles(*ANALYST_ROLES)),
) -> CaseResponseItem:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    actor = str(req.actor or "analyst")
    try:
        alert, case = case_service.update_alert_status(
            alert_id=alert_id,
            case_status=req.case_status,
            analyst_note=req.analyst_note,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if alert is None or case is None:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    record_case_status(str(case["case_status"]))
    set_review_queue_size(case_service.review_queue_size())
    append_audit_event_from_request(
        request,
        event_type="ALERT_STATUS_UPDATED",
        status_code=200,
        request_id=str(case.get("request_id")) if case.get("request_id") is not None else None,
        case_id=str(case["case_id"]),
        alert_id=str(alert["alert_id"]),
        actor=auth_ctx.actor,
        role=auth_ctx.role,
        details={"case_status": str(case["case_status"]), "analyst_note": req.analyst_note},
    )
    return CaseResponseItem(**case)


@app.get("/cases", response_model=CaseListResponse)
async def list_cases(
    status: str | None = None,
    limit: int = 100,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> CaseListResponse:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 1000")

    statuses = _parse_status_filter(status)
    cases = case_service.list_cases(statuses=statuses, limit=int(limit))
    return CaseListResponse(total=len(cases), cases=cases)  # type: ignore[arg-type]


@app.get("/cases/{case_id}", response_model=CaseResponseItem)
async def get_case(
    case_id: str,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> CaseResponseItem:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    case = case_service.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    return CaseResponseItem(**case)


@app.post("/cases/{case_id}/status", response_model=CaseResponseItem)
async def update_case_status(
    case_id: str,
    req: UpdateCaseStatusRequest,
    request: Request,
    auth_ctx: AuthContext = Depends(require_roles(*ANALYST_ROLES)),
) -> CaseResponseItem:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    actor = str(req.actor or "analyst")
    try:
        case = case_service.update_case_status(
            case_id=case_id,
            case_status=req.case_status,
            analyst_note=req.analyst_note,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if case is None:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    record_case_status(str(case["case_status"]))
    set_review_queue_size(case_service.review_queue_size())
    append_audit_event_from_request(
        request,
        event_type="CASE_STATUS_UPDATED",
        status_code=200,
        request_id=str(case.get("request_id")) if case.get("request_id") is not None else None,
        case_id=str(case["case_id"]),
        alert_id=str(case["alert_id"]),
        actor=auth_ctx.actor,
        role=auth_ctx.role,
        details={"case_status": str(case["case_status"]), "analyst_note": req.analyst_note},
    )
    return CaseResponseItem(**case)


@app.post("/cases/{case_id}/resolve", response_model=CaseResponseItem)
async def resolve_case(
    case_id: str,
    req: ResolveCaseRequest,
    request: Request,
    auth_ctx: AuthContext = Depends(require_roles(*ANALYST_ROLES)),
) -> CaseResponseItem:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    actor = str(req.actor or "analyst")
    try:
        case = case_service.resolve_case(
            case_id=case_id,
            resolution=req.resolution,
            analyst_note=req.analyst_note,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if case is None:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    record_case_status(str(case["case_status"]))
    set_review_queue_size(case_service.review_queue_size())
    append_audit_event_from_request(
        request,
        event_type="CASE_RESOLVED",
        status_code=200,
        request_id=str(case.get("request_id")) if case.get("request_id") is not None else None,
        case_id=str(case["case_id"]),
        alert_id=str(case["alert_id"]),
        actor=auth_ctx.actor,
        role=auth_ctx.role,
        details={"resolution": req.resolution, "analyst_note": req.analyst_note},
    )
    return CaseResponseItem(**case)


@app.get("/cases/{case_id}/timeline", response_model=CaseTimelineResponse)
async def case_timeline(
    case_id: str,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> CaseTimelineResponse:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    case = case_service.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    timeline = case_service.get_case_timeline(case_id)
    return CaseTimelineResponse(case_id=case_id, timeline=timeline)  # type: ignore[arg-type]


@app.get("/audit/events", response_model=AuditEventListResponse)
async def list_audit_events(
    request: Request,
    limit: int = 200,
    actor: str | None = None,
    event_type: str | None = None,
    auth_ctx: AuthContext = Depends(require_roles(*ADMIN_ROLES)),
) -> AuditEventListResponse:
    case_service: CaseService | None = getattr(app.state, "case_service", None)
    if case_service is None:
        raise HTTPException(status_code=503, detail="Case service not available.")

    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 1000")

    events = case_service.list_audit_events(limit=int(limit), actor=actor, event_type=event_type)
    append_audit_event_from_request(
        request,
        event_type="AUDIT_EVENTS_READ",
        status_code=200,
        actor=auth_ctx.actor,
        role=auth_ctx.role,
        details={
            "limit": int(limit),
            "returned": len(events),
            "filter_actor": actor,
            "filter_event_type": event_type,
        },
    )
    return AuditEventListResponse(total=len(events), events=events)  # type: ignore[arg-type]


@app.get("/dataset/samples", response_model=DatasetSamplesResponse)
async def dataset_samples(
    n: int = 25,
    strategy: str = "production",
    seed: int | None = 42,
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
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
            include_label=False,
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


@app.get("/internal/dataset/samples", response_model=DatasetSamplesWithLabelResponse, include_in_schema=False)
async def internal_dataset_samples(
    n: int = 25,
    strategy: str = "production",
    seed: int | None = 42,
    x_internal_token: str | None = Header(None),
    _auth_ctx: AuthContext = Depends(require_roles(*READ_ROLES)),
) -> DatasetSamplesWithLabelResponse:
    """
    Internal-only dataset sampling that includes ground truth labels.
    Must not be consumed by the frontend.
    """
    _require_internal_token(x_internal_token)

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
            include_label=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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

    return DatasetSamplesWithLabelResponse(
        n_features=len(loaded.feature_columns),
        feature_names=list(loaded.feature_columns),
        dataset_path=str(dataset_path),
        samples=samples,  # type: ignore[arg-type]
    )
