from pathlib import Path

from fastapi.testclient import TestClient

from genai.auth import AuthManager
from genai.storage import CampaignStorage
from scoring.fastapi_app import create_app


def build_client(tmp_path: Path) -> tuple[TestClient, CampaignStorage]:
    storage = CampaignStorage(root=tmp_path / "generated")
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key="key-a",
        request_limit_per_hour=20,
    )
    storage.create_workspace(
        workspace_id="workspace-b",
        name="Workspace B",
        owner_user_id="user-b",
        api_key="key-b",
        request_limit_per_hour=20,
    )
    auth_manager = AuthManager(storage)
    auth_manager.auth_mode = "workspace_api_key"
    auth_manager.dashboard_auth_mode = "password"
    client = TestClient(create_app(storage=storage, auth_manager=auth_manager))
    return client, storage


def auth_headers(api_key: str) -> dict[str, str]:
    return {"X-CampaignForge-API-Key": api_key}


def test_health_endpoint(tmp_path: Path):
    client, _ = build_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-content-type-options"] == "nosniff"


def test_read_customers_requires_auth(tmp_path: Path):
    client, _ = build_client(tmp_path)
    response = client.get("/customers")
    assert response.status_code == 401


def test_read_customers_with_auth(tmp_path: Path):
    client, _ = build_client(tmp_path)
    response = client.get("/customers", headers=auth_headers("key-a"))
    assert response.status_code == 200
    assert "customer_id" in response.json()[0]


def test_customers_limit_is_bounded(tmp_path: Path):
    client, _ = build_client(tmp_path)
    response = client.get("/customers", params={"limit": 101}, headers=auth_headers("key-a"))
    assert response.status_code == 422


def test_generate_campaign_brief_is_workspace_scoped(tmp_path: Path):
    client, _ = build_client(tmp_path)
    response = client.post(
        "/genai/brief",
        headers=auth_headers("key-a"),
        json={
            "campaign_name": "API Launch",
            "product_name": "CampaignForge AI",
            "brief": (
                "Launch CampaignForge AI to teams that need reusable campaign "
                "messaging and prompt-ready planning outputs."
            ),
            "target_market": "startup marketing teams",
            "channels": ["LinkedIn", "Email"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"].startswith("api-launch-")
    assert payload["workspace_id"] == "workspace-a"
    assert payload["output"]["angles"]


def test_workspace_cannot_read_other_workspace_campaign(tmp_path: Path):
    client, _ = build_client(tmp_path)
    create_response = client.post(
        "/genai/brief",
        headers=auth_headers("key-a"),
        json={
            "campaign_name": "Private Launch",
            "product_name": "CampaignForge AI",
            "brief": "Create a private campaign for one workspace only with clear separation.",
        },
    )
    campaign_id = create_response.json()["campaign_id"]

    response = client.get(f"/genai/campaigns/{campaign_id}", headers=auth_headers("key-b"))
    assert response.status_code == 404


def test_list_campaigns_endpoint_is_workspace_scoped(tmp_path: Path):
    client, _ = build_client(tmp_path)
    client.post(
        "/genai/brief",
        headers=auth_headers("key-a"),
        json={
            "campaign_name": "Workspace A Launch",
            "product_name": "CampaignForge AI",
            "brief": "Create a campaign for workspace A with clear output separation.",
        },
    )
    client.post(
        "/genai/brief",
        headers=auth_headers("key-b"),
        json={
            "campaign_name": "Workspace B Launch",
            "product_name": "CampaignForge AI",
            "brief": "Create a campaign for workspace B with clear output separation.",
        },
    )

    response = client.get("/genai/campaigns", headers=auth_headers("key-a"))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["workspace_id"] == "workspace-a"


def test_generate_campaign_images(tmp_path: Path):
    client, _ = build_client(tmp_path)
    campaign_response = client.post(
        "/genai/brief",
        headers=auth_headers("key-a"),
        json={
            "campaign_name": "Image API Launch",
            "product_name": "CampaignForge AI",
            "brief": (
                "Generate campaign angles and image prompts for a polished "
                "product launch demo."
            ),
        },
    )
    campaign_id = campaign_response.json()["campaign_id"]
    angle_id = campaign_response.json()["output"]["angles"][0]["angle_id"]

    response = client.post(
        "/genai/images",
        headers=auth_headers("key-a"),
        json={
            "campaign_id": campaign_id,
            "angle_id": angle_id,
            "style": "Campaign concept board",
            "count": 2,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == campaign_id
    assert len(payload["assets"]) == 2

    read_response = client.get(f"/genai/campaigns/{campaign_id}/images", headers=auth_headers("key-a"))
    assert read_response.status_code == 200
    filename = payload["assets"][0]["file_path"].split("/")[-1]

    asset_response = client.get(f"/genai/assets/{campaign_id}/{filename}", headers=auth_headers("key-a"))
    assert asset_response.status_code == 200
    assert asset_response.headers["content-type"].startswith("image/")


def test_get_campaign_images_returns_404_when_missing(tmp_path: Path):
    client, _ = build_client(tmp_path)
    response = client.get("/genai/campaigns/does-not-exist/images", headers=auth_headers("key-a"))
    assert response.status_code == 404


def test_review_and_export_campaign_workflow(tmp_path: Path):
    client, _ = build_client(tmp_path)
    campaign_response = client.post(
        "/genai/brief",
        headers=auth_headers("key-a"),
        json={
            "campaign_name": "Workflow API Launch",
            "product_name": "CampaignForge AI",
            "brief": (
                "Create a workflow-ready campaign with approval and export "
                "support."
            ),
        },
    )
    campaign_id = campaign_response.json()["campaign_id"]
    angle_id = campaign_response.json()["output"]["angles"][0]["angle_id"]

    regenerate_response = client.post(
        f"/genai/campaigns/{campaign_id}/regenerate",
        headers=auth_headers("key-a"),
        json={"scope": "copy"},
    )
    assert regenerate_response.status_code == 200

    image_response = client.post(
        "/genai/images",
        headers=auth_headers("key-a"),
        json={
            "campaign_id": campaign_id,
            "angle_id": angle_id,
            "count": 1,
        },
    )
    image_id = image_response.json()["assets"][0]["image_id"]

    review_response = client.post(
        f"/genai/campaigns/{campaign_id}/images/review",
        headers=auth_headers("key-a"),
        json={"image_id": image_id, "approval_status": "approved"},
    )
    assert review_response.status_code == 200
    assert review_response.json()["assets"][0]["approval_status"] == "approved"

    export_response = client.get(f"/genai/campaigns/{campaign_id}/export", headers=auth_headers("key-a"))
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/zip")


def test_usage_limit_returns_429(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    storage.create_workspace(
        workspace_id="limited-workspace",
        name="Limited Workspace",
        owner_user_id="user-limit",
        api_key="limit-key",
        request_limit_per_hour=1,
    )
    auth_manager = AuthManager(storage)
    auth_manager.auth_mode = "workspace_api_key"
    client = TestClient(create_app(storage=storage, auth_manager=auth_manager))

    first = client.post(
        "/genai/brief",
        headers=auth_headers("limit-key"),
        json={
            "campaign_name": "First Launch",
            "product_name": "CampaignForge AI",
            "brief": "Create a first campaign inside the hourly usage cap.",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/genai/brief",
        headers=auth_headers("limit-key"),
        json={
            "campaign_name": "Second Launch",
            "product_name": "CampaignForge AI",
            "brief": "Create a second campaign inside the same hour to trigger the cap.",
        },
    )
    assert second.status_code == 429
