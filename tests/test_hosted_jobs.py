from fastapi.testclient import TestClient

from backend.api import create_app


HEADERS = {
    "X-CampaignForge-Workspace": "workspace-jobs",
    "X-CampaignForge-User": "editor-jobs",
    "X-CampaignForge-Role": "editor",
}


def test_agent_run_is_async_and_idempotent():
    client = TestClient(create_app())
    campaign = client.post("/v1/campaigns", headers=HEADERS, json={"title": "Low-cost launch"}).json()
    headers = {**HEADERS, "Idempotency-Key": "generate-strategy-1"}

    first = client.post(
        f"/v1/campaigns/{campaign['campaign_id']}/runs",
        headers=headers,
        json={"kind": "strategy", "instructions": "Create a concise strategy."},
    )
    repeated = client.post(
        f"/v1/campaigns/{campaign['campaign_id']}/runs",
        headers=headers,
        json={"kind": "strategy", "instructions": "Create a concise strategy."},
    )

    assert first.status_code == 202
    assert first.json()["job_id"] == repeated.json()["job_id"]
    assert first.json()["status"] == "queued"
    status = client.get(f"/v1/jobs/{first.json()['job_id']}", headers=HEADERS)
    assert status.status_code == 200
    assert status.json()["payload"]["campaign_id"] == campaign["campaign_id"]


def test_job_cannot_be_read_from_another_workspace():
    client = TestClient(create_app())
    campaign = client.post("/v1/campaigns", headers=HEADERS, json={"title": "Scoped"}).json()
    created = client.post(
        f"/v1/campaigns/{campaign['campaign_id']}/runs",
        headers={**HEADERS, "Idempotency-Key": "scoped-run"},
        json={"kind": "copy", "instructions": "Draft copy."},
    ).json()
    foreign_headers = {**HEADERS, "X-CampaignForge-Workspace": "workspace-other"}
    assert client.get(f"/v1/jobs/{created['job_id']}", headers=foreign_headers).status_code == 404


def test_development_worker_dispatches_without_model_spend():
    client = TestClient(create_app())
    campaign = client.post("/v1/campaigns", headers=HEADERS, json={"title": "Dispatch"}).json()
    created = client.post(
        f"/v1/campaigns/{campaign['campaign_id']}/runs",
        headers={**HEADERS, "Idempotency-Key": "dispatch-run"},
        json={"kind": "strategy", "instructions": "Create a clear launch strategy for a small marketing team."},
    ).json()
    dispatched = client.post(
        "/v1/internal/jobs/dispatch",
        json={"job_id": created["job_id"], "workspace_id": "workspace-jobs"},
    )
    assert dispatched.status_code == 204
    assert client.get(f"/v1/jobs/{created['job_id']}", headers=HEADERS).json()["status"] == "succeeded"
