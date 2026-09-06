from fastapi.testclient import TestClient

from backend.api import create_app
from backend.brand_kits import BrandKitService
from backend.campaigns.workflow import Role, WorkflowActor
from backend.campaigns.workflow import CampaignWorkflow
from backend.idempotency import InMemoryIdempotencyStore
from backend.jobs import InMemoryJobQueue


def _headers(role: str, user_id: str) -> dict[str, str]:
    return {
        "X-CampaignForge-Workspace": "workspace-1",
        "X-CampaignForge-User": user_id,
        "X-CampaignForge-Role": role,
        "Idempotency-Key": f"{role}-{user_id}",
    }


def test_v1_campaign_approval_uses_the_shared_workflow():
    client = TestClient(create_app())
    editor_headers = _headers("editor", "editor-1")
    reviewer_headers = _headers("reviewer", "reviewer-1")

    created = client.post("/v1/campaigns", headers=editor_headers, json={"title": "Autumn launch"})
    assert created.status_code == 201
    campaign_id = created.json()["campaign_id"]

    submitted = client.post(
        f"/v1/campaigns/{campaign_id}/strategy",
        headers=editor_headers,
        json={"content": {"summary": "A launch strategy"}},
    )
    assert submitted.status_code == 200
    assert submitted.json()["stage"] == "strategy_ready"

    forbidden = client.post(
        f"/v1/campaigns/{campaign_id}/approvals/strategy",
        headers=editor_headers,
    )
    assert forbidden.status_code == 409
    assert forbidden.json()["error"]["code"] == "invalid_transition"

    approved = client.post(
        f"/v1/campaigns/{campaign_id}/approvals/strategy",
        headers=reviewer_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["stage"] == "strategy_approved"

    copy = client.post(
        f"/v1/campaigns/{campaign_id}/copy",
        headers=editor_headers,
        json={"content": {"headline": "Autumn, made memorable"}},
    )
    assert copy.json()["stage"] == "copy_ready"
    assert client.post(
        f"/v1/campaigns/{campaign_id}/approvals/copy", headers=reviewer_headers
    ).json()["stage"] == "copy_approved"

    image_auth = client.post(
        f"/v1/campaigns/{campaign_id}/image-authorizations",
        headers=reviewer_headers,
        json={"count": 1, "estimated_cost_minor": 4},
    )
    assert image_auth.json()["image_authorization"]["count"] == 1

    completed = client.post(
        f"/v1/internal/campaigns/{campaign_id}/assets",
        headers=reviewer_headers,
        json={"asset_ids": ["asset-1"]},
    )
    assert completed.json()["stage"] == "assets_ready"
    reviewed = client.post(
        f"/v1/campaigns/{campaign_id}/assets/asset-1/review",
        headers=reviewer_headers,
        json={"approved": True},
    )
    assert reviewed.json()["assets"][0]["approval_status"] == "approved"
    final = client.post(
        f"/v1/campaigns/{campaign_id}/approvals/final", headers=reviewer_headers
    )
    assert final.json()["export_enabled"] is True


class RecordingIdentityResolver:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def resolve(self, token: str, workspace_id: str) -> WorkflowActor:
        self.calls.append(("id", token, workspace_id))
        return WorkflowActor(user_id="firebase-user", workspace_id=workspace_id, role=Role.OWNER)

    def resolve_session_cookie(self, token: str, workspace_id: str) -> WorkflowActor:
        self.calls.append(("session", token, workspace_id))
        return WorkflowActor(user_id="firebase-user", workspace_id=workspace_id, role=Role.OWNER)


def test_v1_accepts_a_verified_firebase_session_cookie(monkeypatch):
    monkeypatch.setenv("CAMPAIGNFORGE_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused-for-injected-services")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "firebase-project")
    monkeypatch.setenv("GCP_PROJECT_ID", "gcp-project")
    monkeypatch.setenv("GCS_ASSET_BUCKET", "private-assets")
    monkeypatch.setenv("CLOUD_TASKS_QUEUE", "agent-runs")
    monkeypatch.setenv("CLOUD_TASKS_WORKER_URL", "https://worker.example.test/tasks")
    monkeypatch.setenv("CAMPAIGNFORGE_ALLOWED_ORIGINS", "https://app.example.test")
    resolver = RecordingIdentityResolver()
    client = TestClient(
        create_app(
            workflow=CampaignWorkflow(),
            identity_resolver=resolver,
            job_queue=InMemoryJobQueue(),
            idempotency_store=InMemoryIdempotencyStore(),
            brand_kit_service=BrandKitService(),
        )
    )

    response = client.get(
        "/v1/campaigns",
        headers={
            "Authorization": "Bearer signed-session-cookie",
            "X-CampaignForge-Workspace": "workspace-1",
            "X-CampaignForge-Token-Type": "session-cookie",
        },
    )

    assert response.status_code == 200
    assert resolver.calls == [("session", "signed-session-cookie", "workspace-1")]
