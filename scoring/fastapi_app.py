from pathlib import Path
from typing import List, Optional
import os

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse

from genai.auth import AuthManager, AuthenticationError, UsageLimitExceededError, WorkspacePrincipal
from genai.schemas import (
    CampaignBrief,
    CampaignManifest,
    CampaignRegenerationRequest,
    ImageGenerationManifest,
    ImageGenerationRequest,
    ImageReviewRequest,
)
from genai.service import CampaignBriefService, CampaignExportService, CampaignImageService
from genai.storage import CampaignStorage

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "clean_marketing.csv"


def _docs_enabled() -> bool:
    return os.getenv("FASTAPI_EXPOSE_DOCS", "").lower() in {"1", "true", "yes"}


def _init_tracing(app: FastAPI) -> Optional[str]:
    if os.getenv("OTEL_ENABLED", "").lower() not in {"1", "true", "yes"}:
        return None

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    service_name = os.getenv("OTEL_SERVICE_NAME", "campaignforge-ai-fastapi")

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    return endpoint


def create_app(
    *,
    storage: CampaignStorage | None = None,
    auth_manager: AuthManager | None = None,
) -> FastAPI:
    campaign_storage = storage or CampaignStorage()
    auth = auth_manager or AuthManager(campaign_storage)
    campaign_brief_service = CampaignBriefService(storage=campaign_storage)
    campaign_image_service = CampaignImageService(storage=campaign_storage)
    campaign_export_service = CampaignExportService(storage=campaign_storage)

    app = FastAPI(
        title="CampaignForge AI API",
        docs_url="/docs" if _docs_enabled() else None,
        redoc_url="/redoc" if _docs_enabled() else None,
        openapi_url="/openapi.json" if _docs_enabled() else None,
    )

    _init_tracing(app)

    async def require_principal(
        x_campaignforge_api_key: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ) -> WorkspacePrincipal:
        api_key = x_campaignforge_api_key
        if not api_key and authorization and authorization.lower().startswith("bearer "):
            api_key = authorization.split(" ", 1)[1]
        try:
            return auth.authenticate_api_key(api_key)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    def _record_success(principal: WorkspacePrincipal, action: str, campaign_id: str | None = None) -> None:
        campaign_storage.record_audit_event(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
            action=action,
            campaign_id=campaign_id,
            status="success",
        )

    def _record_failure(principal: WorkspacePrincipal, action: str, campaign_id: str | None = None) -> None:
        campaign_storage.record_audit_event(
            workspace_id=principal.workspace_id,
            user_id=principal.user_id,
            action=action,
            campaign_id=campaign_id,
            status="failure",
        )

    def _enforce_usage(principal: WorkspacePrincipal, action: str) -> None:
        try:
            auth.enforce_usage_limit(principal, action)
        except UsageLimitExceededError as exc:
            _record_failure(principal, action)
            raise HTTPException(status_code=429, detail=str(exc)) from exc

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health")
    def health_check(response: Response) -> dict:
        response.headers["Cache-Control"] = "no-store"
        return {"status": "ok"}

    @app.get("/customers")
    def list_customers(
        limit: int = Query(default=10, ge=1, le=100),
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> List[dict]:
        if DATA_PATH.exists():
            df = pd.read_csv(DATA_PATH).reset_index(drop=True)
            df.insert(0, "customer_id", df.index + 1)
            rows = df.head(limit)
        else:
            rows = pd.DataFrame(
                [
                    {"customer_id": 1, "Income": 58000, "Recency": 10},
                    {"customer_id": 2, "Income": 42000, "Recency": 24},
                ]
            )
        _record_success(principal, "customers:list")
        return rows.to_dict(orient="records")

    @app.post("/genai/brief", response_model=CampaignManifest)
    def generate_campaign_brief(
        brief: CampaignBrief,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> CampaignManifest:
        action = "campaign:create"
        _enforce_usage(principal, action)
        manifest = campaign_brief_service.generate_and_save(
            brief,
            workspace_id=principal.workspace_id,
            actor_user_id=principal.user_id,
        )
        _record_success(principal, action, manifest.campaign_id)
        return manifest

    @app.get("/genai/campaigns/{campaign_id}", response_model=CampaignManifest)
    def get_campaign_output(
        campaign_id: str,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> CampaignManifest:
        manifest = campaign_brief_service.load_campaign(campaign_id, workspace_id=principal.workspace_id)
        if manifest is None:
            _record_failure(principal, "campaign:get", campaign_id)
            raise HTTPException(status_code=404, detail="Campaign output not found")
        _record_success(principal, "campaign:get", campaign_id)
        return manifest

    @app.get("/genai/campaigns", response_model=List[CampaignManifest])
    def list_campaign_outputs(
        limit: int = Query(default=10, ge=1, le=50),
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> List[CampaignManifest]:
        payload = campaign_brief_service.list_campaigns(workspace_id=principal.workspace_id)[:limit]
        _record_success(principal, "campaign:list")
        return payload

    @app.post("/genai/images", response_model=ImageGenerationManifest)
    def generate_campaign_images(
        request: ImageGenerationRequest,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> ImageGenerationManifest:
        action = "image:create"
        _enforce_usage(principal, action)
        try:
            manifest = campaign_image_service.generate_and_save(request, workspace_id=principal.workspace_id)
        except ValueError as exc:
            _record_failure(principal, action, request.campaign_id)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        _record_success(principal, action, request.campaign_id)
        return manifest

    @app.post("/genai/campaigns/{campaign_id}/regenerate", response_model=CampaignManifest)
    def regenerate_campaign_output(
        campaign_id: str,
        request: CampaignRegenerationRequest,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> CampaignManifest:
        action = "campaign:regenerate"
        _enforce_usage(principal, action)
        try:
            manifest = campaign_brief_service.regenerate(
                campaign_id,
                request,
                workspace_id=principal.workspace_id,
            )
        except ValueError as exc:
            _record_failure(principal, action, campaign_id)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        _record_success(principal, action, campaign_id)
        return manifest

    @app.get("/genai/campaigns/{campaign_id}/images", response_model=ImageGenerationManifest)
    def get_campaign_images(
        campaign_id: str,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> ImageGenerationManifest:
        manifest = campaign_image_service.load_manifest(campaign_id, workspace_id=principal.workspace_id)
        if manifest is None:
            _record_failure(principal, "image:get", campaign_id)
            raise HTTPException(status_code=404, detail="Campaign image output not found")
        _record_success(principal, "image:get", campaign_id)
        return manifest

    @app.post("/genai/campaigns/{campaign_id}/images/review", response_model=ImageGenerationManifest)
    def review_campaign_image(
        campaign_id: str,
        request: ImageReviewRequest,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> ImageGenerationManifest:
        action = "image:review"
        _enforce_usage(principal, action)
        try:
            manifest = campaign_image_service.review_asset(
                campaign_id,
                request,
                workspace_id=principal.workspace_id,
            )
        except ValueError as exc:
            _record_failure(principal, action, campaign_id)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        _record_success(principal, action, campaign_id)
        return manifest

    @app.get("/genai/assets/{campaign_id}/{filename}")
    def get_campaign_image_asset(
        campaign_id: str,
        filename: str,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> FileResponse:
        manifest = campaign_image_service.load_manifest(campaign_id, workspace_id=principal.workspace_id)
        if manifest is None:
            _record_failure(principal, "image:asset:get", campaign_id)
            raise HTTPException(status_code=404, detail="Image asset not found")
        asset_path = (campaign_storage.campaign_image_dir(campaign_id) / filename).resolve()
        campaign_dir = campaign_storage.campaign_image_dir(campaign_id).resolve()
        if campaign_dir not in asset_path.parents or not asset_path.exists():
            _record_failure(principal, "image:asset:get", campaign_id)
            raise HTTPException(status_code=404, detail="Image asset not found")
        _record_success(principal, "image:asset:get", campaign_id)
        media_type = "image/png" if asset_path.suffix.lower() == ".png" else "image/svg+xml"
        return FileResponse(asset_path, media_type=media_type)

    @app.get("/genai/campaigns/{campaign_id}/export")
    def export_campaign_bundle(
        campaign_id: str,
        principal: WorkspacePrincipal = Depends(require_principal),
    ) -> FileResponse:
        action = "campaign:export"
        _enforce_usage(principal, action)
        try:
            export_path = campaign_export_service.export_campaign(
                campaign_id,
                workspace_id=principal.workspace_id,
            )
        except ValueError as exc:
            _record_failure(principal, action, campaign_id)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        _record_success(principal, action, campaign_id)
        return FileResponse(export_path, media_type="application/zip", filename=export_path.name)

    app.state.campaign_storage = campaign_storage
    app.state.auth_manager = auth
    return app


app = create_app()
