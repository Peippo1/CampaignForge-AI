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
        json={"kind": "strategy", "instructions": "Draft a clear campaign strategy."},
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


def test_generation_requires_editor_and_correct_stage():
    client = TestClient(create_app())
    campaign = client.post("/v1/campaigns", headers=HEADERS, json={"title": "Gated"}).json()
    path = f"/v1/campaigns/{campaign['campaign_id']}/runs"
    for role, kind in [("reviewer", "strategy"), ("editor", "copy")]:
        response = client.post(path, headers={**HEADERS, "X-CampaignForge-Role": role,
                               "Idempotency-Key": role},
                               json={"kind": kind, "instructions": "Create a clear campaign strategy."})
        assert response.status_code == 409


def test_brand_snapshot_is_scoped_and_used_by_worker():
    client = TestClient(create_app())
    kit = client.post("/v1/brand-kits", headers=HEADERS,
                      json={"name": "Specialist brand", "voice": "Precise",
                            "audiences": ["Independent bookshops"]}).json()
    campaign = client.post("/v1/campaigns", headers=HEADERS, json={"title": "Brand launch"}).json()
    path = f"/v1/campaigns/{campaign['campaign_id']}/runs"
    body = {"kind": "strategy", "instructions": "Create a clear campaign strategy.",
            "brand_kit_id": kit["brand_kit_id"]}
    foreign = client.post("/v1/brand-kits", headers={**HEADERS, "X-CampaignForge-Workspace": "foreign"},
                          json={"name": "Private", "voice": "Private"}).json()
    assert client.post(path, headers={**HEADERS, "Idempotency-Key": "foreign"},
                       json={**body, "brand_kit_id": foreign["brand_kit_id"]}).status_code == 404
    job = client.post(path, headers={**HEADERS, "Idempotency-Key": "brand"}, json=body).json()
    dispatch = {"job_id": job["job_id"], "workspace_id": "workspace-jobs"}
    for _ in range(2):
        assert client.post("/v1/internal/jobs/dispatch", json=dispatch).status_code == 204
    updated = client.get(f"/v1/campaigns/{campaign['campaign_id']}", headers=HEADERS).json()
    assert updated["strategy"]["audiences"] == ["Independent bookshops"]
    assert updated["revision"] == 1
