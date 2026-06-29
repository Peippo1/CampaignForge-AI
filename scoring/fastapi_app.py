from pathlib import Path
from typing import List, Optional
import os

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse

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
campaign_storage = CampaignStorage()
campaign_brief_service = CampaignBriefService(storage=campaign_storage)
campaign_image_service = CampaignImageService(storage=campaign_storage)
campaign_export_service = CampaignExportService(storage=campaign_storage)


def _docs_enabled() -> bool:
    return os.getenv("FASTAPI_EXPOSE_DOCS", "").lower() in {"1", "true", "yes"}


app = FastAPI(
    title="CampaignForge AI API",
    docs_url="/docs" if _docs_enabled() else None,
    redoc_url="/redoc" if _docs_enabled() else None,
    openapi_url="/openapi.json" if _docs_enabled() else None,
)


def _init_tracing() -> Optional[str]:
    """
    Initialize OpenTelemetry tracing if explicitly enabled.
    Safe no-op when OTEL_ENABLED is not set.
    """
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


_init_tracing()


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
    """Simple health endpoint for liveness probes."""
    response.headers["Cache-Control"] = "no-store"
    return {"status": "ok"}


@app.get("/customers")
def list_customers(limit: int = Query(default=10, ge=1, le=100)) -> List[dict]:
    """
    Return a lightweight customer listing for UI smoke tests.
    Falls back to a few synthetic rows if the local data file is missing.
    """
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
    return rows.to_dict(orient="records")


@app.post("/genai/brief", response_model=CampaignManifest)
def generate_campaign_brief(brief: CampaignBrief) -> CampaignManifest:
    """Generate and persist a structured campaign brief output."""
    return campaign_brief_service.generate_and_save(brief)


@app.get("/genai/campaigns/{campaign_id}", response_model=CampaignManifest)
def get_campaign_output(campaign_id: str) -> CampaignManifest:
    manifest = campaign_brief_service.load_campaign(campaign_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Campaign output not found")
    return manifest


@app.get("/genai/campaigns", response_model=List[CampaignManifest])
def list_campaign_outputs(limit: int = Query(default=10, ge=1, le=50)) -> List[CampaignManifest]:
    return campaign_brief_service.list_campaigns()[:limit]


@app.post("/genai/images", response_model=ImageGenerationManifest)
def generate_campaign_images(request: ImageGenerationRequest) -> ImageGenerationManifest:
    try:
        return campaign_image_service.generate_and_save(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/genai/campaigns/{campaign_id}/regenerate", response_model=CampaignManifest)
def regenerate_campaign_output(campaign_id: str, request: CampaignRegenerationRequest) -> CampaignManifest:
    try:
        return campaign_brief_service.regenerate(campaign_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/genai/campaigns/{campaign_id}/images", response_model=ImageGenerationManifest)
def get_campaign_images(campaign_id: str) -> ImageGenerationManifest:
    manifest = campaign_image_service.load_manifest(campaign_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Campaign image output not found")
    return manifest


@app.post("/genai/campaigns/{campaign_id}/images/review", response_model=ImageGenerationManifest)
def review_campaign_image(campaign_id: str, request: ImageReviewRequest) -> ImageGenerationManifest:
    try:
        return campaign_image_service.review_asset(campaign_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/genai/assets/{campaign_id}/{filename}")
def get_campaign_image_asset(campaign_id: str, filename: str) -> FileResponse:
    asset_path = (campaign_storage.campaign_image_dir(campaign_id) / filename).resolve()
    campaign_dir = campaign_storage.campaign_image_dir(campaign_id).resolve()
    if campaign_dir not in asset_path.parents or not asset_path.exists():
        raise HTTPException(status_code=404, detail="Image asset not found")
    media_type = "image/png" if asset_path.suffix.lower() == ".png" else "image/svg+xml"
    return FileResponse(asset_path, media_type=media_type)


@app.get("/genai/campaigns/{campaign_id}/export")
def export_campaign_bundle(campaign_id: str) -> FileResponse:
    try:
        export_path = campaign_export_service.export_campaign(campaign_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(export_path, media_type="application/zip", filename=export_path.name)
