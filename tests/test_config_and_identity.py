import pytest

from backend.campaigns.workflow import Role
from backend.config import Settings
from backend.identity import InMemoryMembershipDirectory, Membership
from backend.idempotency import SQLAlchemyIdempotencyStore
from backend.jobs import SQLAlchemyJobQueue


def test_production_configuration_rejects_sqlite(monkeypatch):
    values = {
        "CAMPAIGNFORGE_ENV": "production",
        "DATABASE_URL": "sqlite:///unsafe.db",
        "FIREBASE_PROJECT_ID": "firebase-project",
        "GCP_PROJECT_ID": "gcp-project",
        "GCS_ASSET_BUCKET": "private-assets",
        "CLOUD_TASKS_QUEUE": "agent-runs",
        "CLOUD_TASKS_WORKER_URL": "https://worker.example.test/tasks",
        "CAMPAIGNFORGE_ALLOWED_ORIGINS": "https://app.example.test",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings.from_env()


def test_membership_directory_is_workspace_scoped():
    directory = InMemoryMembershipDirectory(
        [Membership(workspace_id="one", user_id="user-1", role=Role.REVIEWER)]
    )
    assert directory.resolve("user-1", "one").role is Role.REVIEWER
    assert directory.resolve("user-1", "two") is None


def test_sql_job_queue_persists_and_scopes_jobs(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'jobs.db'}"
    created = SQLAlchemyJobQueue(database_url).enqueue(
        workspace_id="one", kind="agent.strategy", payload={"campaign_id": "campaign-1"}
    )
    recreated = SQLAlchemyJobQueue(database_url)
    assert recreated.get(created.job_id, "one").payload["campaign_id"] == "campaign-1"
    assert recreated.get(created.job_id, "two") is None


def test_idempotency_result_survives_store_recreation(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'idempotency.db'}"
    SQLAlchemyIdempotencyStore(database_url).put("one", "campaign:create", "request-1", {"id": "c1"})
    restored = SQLAlchemyIdempotencyStore(database_url).get("one", "campaign:create", "request-1")
    assert restored == {"id": "c1"}
