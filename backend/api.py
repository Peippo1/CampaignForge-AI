from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.campaigns.workflow import (
    Campaign,
    CampaignWorkflow,
    InvalidTransitionError,
    Role,
    WorkflowActor,
)
from backend.campaigns.repository import SQLAlchemyCampaignRepository
from backend.brand_kits import BrandKit, BrandKitService, SQLAlchemyBrandKitRepository
from backend.config import Settings
from backend.identity import FirebaseIdentityResolver, IdentityError, SQLAlchemyMembershipDirectory
from backend.idempotency import IdempotencyStore, InMemoryIdempotencyStore, SQLAlchemyIdempotencyStore
from backend.jobs import CloudTasksJobQueue, InMemoryJobQueue, JobQueue
from backend.worker import AgentJobProcessor


class CampaignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ContentSubmission(BaseModel):
    content: dict[str, Any]


class ImageAuthorizationRequest(BaseModel):
    count: int = Field(ge=1, le=4)
    estimated_cost_minor: int = Field(ge=0)


class GeneratedAssetsRequest(BaseModel):
    asset_ids: list[str]


class AssetReviewRequest(BaseModel):
    approved: bool
    reason: str | None = Field(default=None, max_length=1_000)


class AgentRunRequest(BaseModel):
    kind: str = Field(pattern="^(strategy|copy)$")
    instructions: str = Field(min_length=1, max_length=4_000)


class BrandKitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    voice: str = Field(min_length=1, max_length=4_000)
    audiences: list[str] = Field(default_factory=list)
    product_facts: list[str] = Field(default_factory=list)
    required_phrases: list[str] = Field(default_factory=list)
    banned_terms: list[str] = Field(default_factory=list)
    compliance_rules: list[str] = Field(default_factory=list)


class JobDispatch(BaseModel):
    job_id: str
    workspace_id: str


def _campaign_payload(campaign: Campaign) -> dict[str, Any]:
    payload = asdict(campaign)
    payload["export_enabled"] = campaign.export_enabled
    return payload


def _brand_payload(brand_kit: BrandKit) -> dict[str, Any]:
    return asdict(brand_kit)


def create_app(  # noqa: C901 - endpoint registration is intentionally centralized for the v1 slice
    *,
    workflow: CampaignWorkflow | None = None,
    identity_resolver=None,
    job_queue: JobQueue | None = None,
    idempotency_store: IdempotencyStore | None = None,
    brand_kit_service: BrandKitService | None = None,
) -> FastAPI:
    settings = Settings.from_env()
    if workflow is None and settings.database_url:
        workflow = CampaignWorkflow(repository=SQLAlchemyCampaignRepository(settings.database_url))
    campaign_workflow = workflow or CampaignWorkflow()
    if brand_kit_service is None and settings.database_url:
        brand_kit_service = BrandKitService(SQLAlchemyBrandKitRepository(settings.database_url))
    brands = brand_kit_service or BrandKitService()
    allow_development_headers = settings.environment == "development"
    if identity_resolver is None and settings.environment != "development" and settings.database_url:
        directory = SQLAlchemyMembershipDirectory(settings.database_url or "")
        identity_resolver = FirebaseIdentityResolver(directory, project_id=settings.firebase_project_id or "")
    if job_queue is None and settings.environment == "production":
        job_queue = CloudTasksJobQueue(
            database_url=settings.database_url or "",
            project_id=settings.gcp_project_id or "",
            region=settings.gcp_region,
            queue=settings.tasks_queue or "",
            worker_url=settings.tasks_worker_url or "",
        )
    jobs = job_queue or InMemoryJobQueue()
    if idempotency_store is None and settings.database_url:
        idempotency_store = SQLAlchemyIdempotencyStore(settings.database_url)
    idempotency = idempotency_store or InMemoryIdempotencyStore()

    expose_docs = settings.environment != "production"
    app = FastAPI(
        title="CampaignForge AI",
        version="1.0.0",
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-CampaignForge-Workspace"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition_handler(_request: Request, exc: InvalidTransitionError):
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "invalid_transition", "message": str(exc), "retryable": False}},
        )

    @app.exception_handler(KeyError)
    async def missing_resource_handler(_request: Request, _exc: KeyError):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": "Resource not found.", "retryable": False}},
        )

    async def actor_from_request(
        authorization: str | None = Header(default=None),
        workspace_id: str | None = Header(default=None, alias="X-CampaignForge-Workspace"),
        user_id: str | None = Header(default=None, alias="X-CampaignForge-User"),
        role: str | None = Header(default=None, alias="X-CampaignForge-Role"),
    ) -> WorkflowActor:
        if allow_development_headers and workspace_id and user_id and role:
            try:
                return WorkflowActor(user_id=user_id, workspace_id=workspace_id, role=Role(role))
            except ValueError as exc:
                raise HTTPException(status_code=401, detail="Invalid development role.") from exc
        if authorization and authorization.lower().startswith("bearer ") and workspace_id and identity_resolver:
            try:
                return identity_resolver.resolve(authorization.split(" ", 1)[1], workspace_id)
            except IdentityError as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc
        raise HTTPException(status_code=401, detail="Authentication required.")

    async def verify_task_request(
        authorization: str | None = Header(default=None),
        queue_name: str | None = Header(default=None, alias="X-CloudTasks-QueueName"),
    ) -> None:
        if settings.environment != "production":
            return
        if queue_name != settings.tasks_queue or not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Authenticated task delivery required.")
        try:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import id_token

            claims = id_token.verify_oauth2_token(
                authorization.split(" ", 1)[1],
                GoogleAuthRequest(),
                audience=settings.tasks_worker_url,
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid task identity.") from exc
        expected_email = f"campaignforge-worker@{settings.gcp_project_id}.iam.gserviceaccount.com"
        if claims.get("email") != expected_email or claims.get("email_verified") is not True:
            raise HTTPException(status_code=403, detail="Task identity is not authorized.")

    @app.get("/health")
    async def health(response: Response) -> dict[str, str]:
        response.headers["Cache-Control"] = "no-store"
        return {"status": "ok"}

    @app.post("/v1/campaigns", status_code=201)
    async def create_campaign(
        body: CampaignCreate,
        actor: WorkflowActor = Depends(actor_from_request),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        cached = idempotency.get(actor.workspace_id, "campaign:create", idempotency_key or "")
        if idempotency_key and cached is not None:
            return cached
        payload = _campaign_payload(campaign_workflow.create_campaign(actor, title=body.title))
        if idempotency_key:
            idempotency.put(actor.workspace_id, "campaign:create", idempotency_key, payload)
        return payload

    @app.get("/v1/campaigns/{campaign_id}")
    async def get_campaign(
        campaign_id: str,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(campaign_workflow.get_campaign(actor, campaign_id))

    @app.post("/v1/brand-kits", status_code=201)
    async def create_brand_kit(
        body: BrandKitCreate,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        values = body.model_dump() if hasattr(body, "model_dump") else body.dict()
        return _brand_payload(brands.create(actor, **values))

    @app.get("/v1/brand-kits")
    async def list_brand_kits(actor: WorkflowActor = Depends(actor_from_request)) -> list[dict[str, Any]]:
        return [_brand_payload(item) for item in brands.list(actor)]

    @app.get("/v1/brand-kits/{brand_kit_id}")
    async def get_brand_kit(
        brand_kit_id: str,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _brand_payload(brands.get(actor, brand_kit_id))

    @app.get("/v1/campaigns")
    async def list_campaigns(actor: WorkflowActor = Depends(actor_from_request)) -> list[dict[str, Any]]:
        return [_campaign_payload(item) for item in campaign_workflow.list_campaigns(actor)]

    @app.post("/v1/campaigns/{campaign_id}/strategy")
    async def submit_strategy(
        campaign_id: str,
        body: ContentSubmission,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(campaign_workflow.submit_strategy(actor, campaign_id, body.content))

    @app.post("/v1/campaigns/{campaign_id}/approvals/strategy")
    async def approve_strategy(
        campaign_id: str,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(campaign_workflow.approve_strategy(actor, campaign_id))

    @app.post("/v1/campaigns/{campaign_id}/copy")
    async def submit_copy(
        campaign_id: str,
        body: ContentSubmission,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(campaign_workflow.submit_copy(actor, campaign_id, body.content))

    @app.post("/v1/campaigns/{campaign_id}/approvals/copy")
    async def approve_copy(
        campaign_id: str,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(campaign_workflow.approve_copy(actor, campaign_id))

    @app.post("/v1/campaigns/{campaign_id}/image-authorizations")
    async def authorize_images(
        campaign_id: str,
        body: ImageAuthorizationRequest,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        if body.count > settings.image_max_per_run:
            raise HTTPException(status_code=422, detail="Image count exceeds the workspace safety limit.")
        return _campaign_payload(
            campaign_workflow.authorize_image_generation(
                actor,
                campaign_id,
                count=body.count,
                estimated_cost_minor=body.estimated_cost_minor,
            )
        )

    @app.post("/v1/internal/campaigns/{campaign_id}/assets")
    async def complete_images(
        campaign_id: str,
        body: GeneratedAssetsRequest,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        if not body.asset_ids or len(body.asset_ids) > settings.image_max_per_run:
            raise HTTPException(status_code=422, detail="Generated asset count exceeds the workspace safety limit.")
        campaign_workflow.get_campaign(actor, campaign_id)
        return _campaign_payload(campaign_workflow.complete_image_generation(campaign_id, body.asset_ids))

    @app.post("/v1/campaigns/{campaign_id}/assets/{asset_id}/review")
    async def review_asset(
        campaign_id: str,
        asset_id: str,
        body: AssetReviewRequest,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(
            campaign_workflow.review_asset(
                actor,
                campaign_id,
                asset_id,
                approved=body.approved,
                reason=body.reason,
            )
        )

    @app.post("/v1/campaigns/{campaign_id}/approvals/final")
    async def final_approval(
        campaign_id: str,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        return _campaign_payload(campaign_workflow.final_approve(actor, campaign_id))

    @app.post("/v1/campaigns/{campaign_id}/runs", status_code=202)
    async def create_agent_run(
        campaign_id: str,
        body: AgentRunRequest,
        actor: WorkflowActor = Depends(actor_from_request),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        campaign_workflow.get_campaign(actor, campaign_id)
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="Idempotency-Key is required for generation requests.")
        operation = f"campaign:{campaign_id}:run"
        cached = idempotency.get(actor.workspace_id, operation, idempotency_key)
        if cached is not None:
            return cached
        job = jobs.enqueue(
            workspace_id=actor.workspace_id,
            kind=f"agent.{body.kind}",
            payload={
                "campaign_id": campaign_id,
                "instructions": body.instructions,
                "requested_by": actor.user_id,
                "model": settings.text_model,
            },
        )
        payload = asdict(job)
        idempotency.put(actor.workspace_id, operation, idempotency_key, payload)
        return payload

    @app.get("/v1/jobs/{job_id}")
    async def get_job(
        job_id: str,
        actor: WorkflowActor = Depends(actor_from_request),
    ) -> dict[str, Any]:
        job = jobs.get(job_id, actor.workspace_id)
        if job is None:
            raise KeyError(job_id)
        return asdict(job)

    @app.post("/v1/internal/jobs/dispatch", status_code=204)
    async def dispatch_job(
        body: JobDispatch,
        _verified: None = Depends(verify_task_request),
    ) -> Response:
        if settings.environment == "production":
            from backend.agents.campaign import OpenAICampaignAgentRunner

            runner = OpenAICampaignAgentRunner(model=settings.text_model)
        else:
            from backend.agents.campaign import MockCampaignAgentRunner

            runner = MockCampaignAgentRunner()
        processor = AgentJobProcessor(
            workflow=campaign_workflow,
            jobs=jobs,
            runner=runner,
            model=settings.text_model if settings.environment == "production" else "mock",
        )
        await processor.process(job_id=body.job_id, workspace_id=body.workspace_id)
        return Response(status_code=204)

    app.state.campaign_workflow = campaign_workflow
    app.state.job_queue = jobs
    app.state.idempotency_store = idempotency
    app.state.brand_kit_service = brands
    return app


app = create_app()
