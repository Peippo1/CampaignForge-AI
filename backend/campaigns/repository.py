from __future__ import annotations

from dataclasses import asdict
from typing import Any, Protocol

from sqlalchemy import JSON, Column, DateTime, MetaData, String, Table, create_engine, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.sql import func

from backend.campaigns.workflow import (
    Approval,
    Campaign,
    CampaignRevision,
    CampaignStage,
    GeneratedAsset,
    ImageAuthorization,
)


class CampaignRepository(Protocol):
    def get(self, campaign_id: str) -> Campaign | None: ...

    def save(self, campaign: Campaign) -> None: ...

    def list_for_workspace(self, workspace_id: str) -> list[Campaign]: ...


class InMemoryCampaignRepository:
    def __init__(self) -> None:
        self._campaigns: dict[str, Campaign] = {}

    def get(self, campaign_id: str) -> Campaign | None:
        return self._campaigns.get(campaign_id)

    def save(self, campaign: Campaign) -> None:
        self._campaigns[campaign.campaign_id] = campaign

    def list_for_workspace(self, workspace_id: str) -> list[Campaign]:
        return [campaign for campaign in self._campaigns.values() if campaign.workspace_id == workspace_id]


metadata = MetaData()
campaigns = Table(
    "campaigns_v1",
    metadata,
    Column("campaign_id", String(36), primary_key=True),
    Column("workspace_id", String(120), nullable=False, index=True),
    Column("payload", JSON, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
)


class SQLAlchemyCampaignRepository:
    """PostgreSQL-ready campaign adapter; SQLite is supported for local tests."""

    def __init__(self, database_url: str | Engine) -> None:
        self.engine = database_url if isinstance(database_url, Engine) else create_engine(database_url)
        metadata.create_all(self.engine)

    def get(self, campaign_id: str) -> Campaign | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(campaigns.c.payload).where(campaigns.c.campaign_id == campaign_id)
            ).scalar_one_or_none()
        return _campaign_from_payload(row) if row is not None else None

    def save(self, campaign: Campaign) -> None:
        payload = asdict(campaign)
        with self.engine.begin() as connection:
            exists = connection.execute(
                select(campaigns.c.campaign_id).where(campaigns.c.campaign_id == campaign.campaign_id)
            ).first()
            if exists:
                connection.execute(
                    update(campaigns)
                    .where(campaigns.c.campaign_id == campaign.campaign_id)
                    .values(workspace_id=campaign.workspace_id, payload=payload, updated_at=func.now())
                )
            else:
                connection.execute(
                    insert(campaigns).values(
                        campaign_id=campaign.campaign_id,
                        workspace_id=campaign.workspace_id,
                        payload=payload,
                    )
                )

    def list_for_workspace(self, workspace_id: str) -> list[Campaign]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(campaigns.c.payload)
                .where(campaigns.c.workspace_id == workspace_id)
                .order_by(campaigns.c.updated_at.desc())
            ).scalars()
            return [_campaign_from_payload(payload) for payload in rows]


def _campaign_from_payload(payload: dict[str, Any]) -> Campaign:
    authorization = payload.get("image_authorization")
    return Campaign(
        campaign_id=payload["campaign_id"],
        workspace_id=payload["workspace_id"],
        title=payload["title"],
        created_by=payload["created_by"],
        stage=CampaignStage(payload["stage"]),
        revision=int(payload.get("revision", 0)),
        strategy=payload.get("strategy"),
        copy=payload.get("copy"),
        approvals=tuple(
            Approval(
                stage=CampaignStage(item["stage"]),
                actor_user_id=item["actor_user_id"],
                created_at=item["created_at"],
            )
            for item in payload.get("approvals", [])
        ),
        image_authorization=ImageAuthorization(**authorization) if authorization else None,
        assets=tuple(GeneratedAsset(**item) for item in payload.get("assets", [])),
        revisions=tuple(
            CampaignRevision(
                revision=int(item["revision"]),
                stage=CampaignStage(item["stage"]),
                actor_user_id=item["actor_user_id"],
                created_at=item["created_at"],
                source=item["source"],
                model=item.get("model"),
                prompt_version=item.get("prompt_version"),
                run_id=item.get("run_id"),
            )
            for item in payload.get("revisions", [])
        ),
    )
