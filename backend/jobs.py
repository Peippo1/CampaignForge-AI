from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, create_engine, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func


@dataclass(frozen=True)
class Job:
    job_id: str
    workspace_id: str
    kind: str
    status: str
    created_at: str
    payload: dict[str, Any]


class JobQueue(Protocol):
    def enqueue(self, *, workspace_id: str, kind: str, payload: dict[str, Any]) -> Job: ...

    def get(self, job_id: str, workspace_id: str) -> Job | None: ...

    def set_status(self, job_id: str, workspace_id: str, status: str) -> Job: ...


class InMemoryJobQueue:
    """Development queue. Jobs remain queued until a local worker handles them."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def enqueue(self, *, workspace_id: str, kind: str, payload: dict[str, Any]) -> Job:
        job = Job(
            job_id=str(uuid4()),
            workspace_id=workspace_id,
            kind=kind,
            status="queued",
            created_at=datetime.now(UTC).isoformat(),
            payload=dict(payload),
        )
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str, workspace_id: str) -> Job | None:
        job = self._jobs.get(job_id)
        return job if job and job.workspace_id == workspace_id else None

    def set_status(self, job_id: str, workspace_id: str, status: str) -> Job:
        job = self.get(job_id, workspace_id)
        if job is None:
            raise KeyError(job_id)
        updated = Job(**{**asdict(job), "status": status})
        self._jobs[job_id] = updated
        return updated


job_metadata = MetaData()
jobs = Table(
    "jobs_v1",
    job_metadata,
    Column("job_id", String(36), primary_key=True),
    Column("workspace_id", String(120), nullable=False, index=True),
    Column("kind", String(80), nullable=False),
    Column("status", String(24), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("payload", JSON, nullable=False),
)


class SQLAlchemyJobQueue:
    def __init__(self, database_url: str | Engine) -> None:
        self.engine = database_url if isinstance(database_url, Engine) else create_engine(database_url)
        job_metadata.create_all(self.engine)

    def enqueue(self, *, workspace_id: str, kind: str, payload: dict[str, Any]) -> Job:
        job = Job(
            job_id=str(uuid4()),
            workspace_id=workspace_id,
            kind=kind,
            status="queued",
            created_at=datetime.now(UTC).isoformat(),
            payload=dict(payload),
        )
        with self.engine.begin() as connection:
            values = asdict(job)
            values["created_at"] = datetime.fromisoformat(job.created_at)
            connection.execute(insert(jobs).values(**values))
        return job

    def get(self, job_id: str, workspace_id: str) -> Job | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(jobs).where(jobs.c.job_id == job_id, jobs.c.workspace_id == workspace_id)
            ).mappings().one_or_none()
        if row is None:
            return None
        return Job(
            job_id=row["job_id"],
            workspace_id=row["workspace_id"],
            kind=row["kind"],
            status=row["status"],
            created_at=row["created_at"].isoformat(),
            payload=row["payload"],
        )

    def set_status(self, job_id: str, workspace_id: str, status: str) -> Job:
        with self.engine.begin() as connection:
            result = connection.execute(
                update(jobs)
                .where(jobs.c.job_id == job_id, jobs.c.workspace_id == workspace_id)
                .values(status=status)
            )
            if result.rowcount != 1:
                raise KeyError(job_id)
        updated = self.get(job_id, workspace_id)
        if updated is None:
            raise KeyError(job_id)
        return updated


class CloudTasksJobQueue(SQLAlchemyJobQueue):
    """Persists job state in PostgreSQL, then queues authenticated worker delivery."""

    def __init__(
        self,
        *,
        database_url: str,
        project_id: str,
        region: str,
        queue: str,
        worker_url: str,
    ) -> None:
        super().__init__(database_url)
        self.project_id = project_id
        self.region = region
        self.queue = queue
        self.worker_url = worker_url

    def enqueue(self, *, workspace_id: str, kind: str, payload: dict[str, Any]) -> Job:
        job = super().enqueue(workspace_id=workspace_id, kind=kind, payload=payload)
        from google.cloud import tasks_v2

        client = tasks_v2.CloudTasksClient()
        parent = client.queue_path(self.project_id, self.region, self.queue)
        body = json.dumps(
            {"job_id": job.job_id, "workspace_id": job.workspace_id},
            separators=(",", ":"),
        ).encode()
        client.create_task(
            parent=parent,
            task={
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": self.worker_url,
                    "headers": {"Content-Type": "application/json"},
                    "body": body,
                    "oidc_token": {
                        "service_account_email": (
                            f"campaignforge-worker@{self.project_id}.iam.gserviceaccount.com"
                        )
                    },
                }
            },
        )
        return job
