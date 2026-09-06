from fastapi.testclient import TestClient

from backend.api import create_app


def headers(role: str, user: str = "user-1") -> dict[str, str]:
    return {
        "X-CampaignForge-Workspace": "workspace-brand",
        "X-CampaignForge-User": user,
        "X-CampaignForge-Role": role,
    }


def test_editor_creates_and_lists_workspace_brand_kit():
    client = TestClient(create_app())
    created = client.post(
        "/v1/brand-kits",
        headers=headers("editor"),
        json={
            "name": "CampaignForge",
            "voice": "Clear and credible",
            "audiences": ["Small marketing teams"],
            "required_phrases": ["CampaignForge AI"],
            "banned_terms": ["guaranteed"],
        },
    )
    assert created.status_code == 201
    assert created.json()["banned_terms"] == ["guaranteed"]
    assert client.get("/v1/brand-kits", headers=headers("reviewer", "reviewer-1")).json()[0]["name"] == "CampaignForge"


def test_reviewer_cannot_create_brand_kit():
    client = TestClient(create_app())
    response = client.post(
        "/v1/brand-kits",
        headers=headers("reviewer"),
        json={"name": "No", "voice": "No"},
    )
    assert response.status_code == 409
