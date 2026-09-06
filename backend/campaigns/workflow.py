from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import RLock
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from backend.campaigns.repository import CampaignRepository


class Role(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    REVIEWER = "reviewer"


class CampaignStage(StrEnum):
    DRAFT = "draft"
    STRATEGY_READY = "strategy_ready"
    STRATEGY_APPROVED = "strategy_approved"
    COPY_READY = "copy_ready"
    COPY_APPROVED = "copy_approved"
    IMAGE_GENERATION_APPROVED = "image_generation_approved"
    ASSETS_READY = "assets_ready"
    FINAL_APPROVED = "final_approved"


class InvalidTransitionError(RuntimeError):
    """Raised when an actor attempts a disallowed workflow transition."""


@dataclass(frozen=True)
class WorkflowActor:
    user_id: str
    workspace_id: str
    role: Role


@dataclass(frozen=True)
class Approval:
    stage: CampaignStage
    actor_user_id: str
    created_at: str


@dataclass(frozen=True)
class ImageAuthorization:
    count: int
    estimated_cost_minor: int
    actor_user_id: str
    created_at: str


@dataclass(frozen=True)
class GeneratedAsset:
    asset_id: str
    approval_status: str = "pending"
    review_reason: str | None = None


@dataclass(frozen=True)
class CampaignRevision:
    revision: int
    stage: CampaignStage
    actor_user_id: str
    created_at: str
    source: str
    model: str | None = None
    prompt_version: str | None = None
    run_id: str | None = None


@dataclass(frozen=True)
class RevisionContext:
    source: str = "manual"
    model: str | None = None
    prompt_version: str | None = None
    run_id: str | None = None


@dataclass(frozen=True)
class Campaign:
    campaign_id: str
    workspace_id: str
    title: str
    created_by: str
    stage: CampaignStage = CampaignStage.DRAFT
    revision: int = 0
    strategy: dict[str, Any] | None = None
    copy: dict[str, Any] | None = None
    approvals: tuple[Approval, ...] = field(default_factory=tuple)
    image_authorization: ImageAuthorization | None = None
    assets: tuple[GeneratedAsset, ...] = field(default_factory=tuple)
    revisions: tuple[CampaignRevision, ...] = field(default_factory=tuple)

    @property
    def export_enabled(self) -> bool:
        return self.stage is CampaignStage.FINAL_APPROVED


class CampaignWorkflow:
    """Owns campaign transitions so every caller shares the same rules."""

    def __init__(self, repository: CampaignRepository | None = None) -> None:
        if repository is None:
            from backend.campaigns.repository import InMemoryCampaignRepository

            repository = InMemoryCampaignRepository()
        self._repository = repository
        self._lock = RLock()

    def create_campaign(self, actor: WorkflowActor, *, title: str) -> Campaign:
        if actor.role not in {Role.OWNER, Role.EDITOR}:
            raise InvalidTransitionError("Only an owner or editor can create a campaign.")
        campaign = Campaign(
            campaign_id=str(uuid4()),
            workspace_id=actor.workspace_id,
            title=title.strip(),
            created_by=actor.user_id,
        )
        with self._lock:
            self._repository.save(campaign)
        return campaign

    def submit_strategy(
        self,
        actor: WorkflowActor,
        campaign_id: str,
        strategy: dict[str, Any],
        *,
        revision_context: RevisionContext | None = None,
    ) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        if actor.role not in {Role.OWNER, Role.EDITOR}:
            raise InvalidTransitionError("Only an owner or editor can submit strategy.")
        if campaign.stage is not CampaignStage.DRAFT:
            raise InvalidTransitionError("Strategy can only be submitted from draft.")
        next_revision = campaign.revision + 1
        updated = replace(
            campaign,
            stage=CampaignStage.STRATEGY_READY,
            revision=next_revision,
            strategy=dict(strategy),
            revisions=(
                *campaign.revisions,
                self._revision(
                    next_revision,
                    CampaignStage.STRATEGY_READY,
                    actor,
                    revision_context or RevisionContext(),
                ),
            ),
        )
        return self._save(updated)

    def approve_strategy(self, actor: WorkflowActor, campaign_id: str) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        if actor.role not in {Role.OWNER, Role.REVIEWER}:
            if actor.user_id == campaign.created_by:
                raise InvalidTransitionError("An editor cannot approve their own campaign stage.")
            raise InvalidTransitionError("Only an owner or reviewer can approve strategy.")
        if campaign.stage is not CampaignStage.STRATEGY_READY:
            raise InvalidTransitionError("Strategy must be ready before it can be approved.")
        approval = Approval(
            stage=CampaignStage.STRATEGY_READY,
            actor_user_id=actor.user_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        updated = replace(
            campaign,
            stage=CampaignStage.STRATEGY_APPROVED,
            approvals=(*campaign.approvals, approval),
        )
        return self._save(updated)

    def submit_copy(
        self,
        actor: WorkflowActor,
        campaign_id: str,
        copy: dict[str, Any],
        *,
        revision_context: RevisionContext | None = None,
    ) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        self._require_editor(actor, "submit copy")
        if campaign.stage is not CampaignStage.STRATEGY_APPROVED:
            raise InvalidTransitionError("Strategy must be approved before copy can be submitted.")
        next_revision = campaign.revision + 1
        return self._save(
            replace(
                campaign,
                stage=CampaignStage.COPY_READY,
                revision=next_revision,
                copy=dict(copy),
                revisions=(
                    *campaign.revisions,
                    self._revision(
                        next_revision,
                        CampaignStage.COPY_READY,
                        actor,
                        revision_context or RevisionContext(),
                    ),
                ),
            )
        )

    def approve_copy(self, actor: WorkflowActor, campaign_id: str) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        self._require_reviewer(actor, campaign, "copy")
        if campaign.stage is not CampaignStage.COPY_READY:
            raise InvalidTransitionError("Copy must be ready before it can be approved.")
        return self._save(
            replace(
                campaign,
                stage=CampaignStage.COPY_APPROVED,
                approvals=(*campaign.approvals, self._approval(CampaignStage.COPY_READY, actor)),
            )
        )

    def authorize_image_generation(
        self,
        actor: WorkflowActor,
        campaign_id: str,
        *,
        count: int,
        estimated_cost_minor: int,
    ) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        self._require_reviewer(actor, campaign, "image generation")
        if campaign.stage is not CampaignStage.COPY_APPROVED:
            raise InvalidTransitionError("Copy must be approved before image generation.")
        if count < 1 or count > 4:
            raise ValueError("Image count must be between 1 and 4.")
        if estimated_cost_minor < 0:
            raise ValueError("Estimated cost cannot be negative.")
        authorization = ImageAuthorization(
            count=count,
            estimated_cost_minor=estimated_cost_minor,
            actor_user_id=actor.user_id,
            created_at=datetime.now(UTC).isoformat(),
        )
        return self._save(
            replace(
                campaign,
                stage=CampaignStage.IMAGE_GENERATION_APPROVED,
                image_authorization=authorization,
            )
        )

    def complete_image_generation(self, campaign_id: str, asset_ids: list[str]) -> Campaign:
        with self._lock:
            campaign = self._repository.get(campaign_id)
        if campaign is None:
            raise KeyError(campaign_id)
        if campaign.stage is not CampaignStage.IMAGE_GENERATION_APPROVED:
            raise InvalidTransitionError("Image generation requires authorization.")
        if not asset_ids or len(asset_ids) > campaign.image_authorization.count:
            raise InvalidTransitionError("Generated asset count exceeds the approved authorization.")
        assets = tuple(GeneratedAsset(asset_id=asset_id) for asset_id in asset_ids)
        return self._save(replace(campaign, stage=CampaignStage.ASSETS_READY, assets=assets))

    def review_asset(
        self,
        actor: WorkflowActor,
        campaign_id: str,
        asset_id: str,
        *,
        approved: bool,
        reason: str | None = None,
    ) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        self._require_reviewer(actor, campaign, "asset")
        if campaign.stage is not CampaignStage.ASSETS_READY:
            raise InvalidTransitionError("Assets must be ready before review.")
        if asset_id not in {asset.asset_id for asset in campaign.assets}:
            raise KeyError(asset_id)
        if not approved and not (reason or "").strip():
            raise InvalidTransitionError("Rejected assets require a review reason.")
        status = "approved" if approved else "rejected"
        assets = tuple(
            replace(asset, approval_status=status, review_reason=(reason or "").strip() or None)
            if asset.asset_id == asset_id
            else asset
            for asset in campaign.assets
        )
        return self._save(replace(campaign, assets=assets))

    def final_approve(self, actor: WorkflowActor, campaign_id: str) -> Campaign:
        campaign = self._get_for_actor(actor, campaign_id)
        self._require_reviewer(actor, campaign, "campaign")
        if campaign.stage is not CampaignStage.ASSETS_READY:
            raise InvalidTransitionError("Campaign assets must be ready before final approval.")
        if not campaign.assets or any(asset.approval_status != "approved" for asset in campaign.assets):
            raise InvalidTransitionError("All campaign assets must be approved before final approval.")
        return self._save(
            replace(
                campaign,
                stage=CampaignStage.FINAL_APPROVED,
                approvals=(*campaign.approvals, self._approval(CampaignStage.ASSETS_READY, actor)),
            )
        )

    def get_campaign(self, actor: WorkflowActor, campaign_id: str) -> Campaign:
        return self._get_for_actor(actor, campaign_id)

    def list_campaigns(self, actor: WorkflowActor) -> list[Campaign]:
        with self._lock:
            return self._repository.list_for_workspace(actor.workspace_id)

    def _get_for_actor(self, actor: WorkflowActor, campaign_id: str) -> Campaign:
        with self._lock:
            campaign = self._repository.get(campaign_id)
        if campaign is None:
            raise KeyError(campaign_id)
        if campaign.workspace_id != actor.workspace_id:
            raise KeyError(campaign_id)
        return campaign

    def _save(self, campaign: Campaign) -> Campaign:
        with self._lock:
            self._repository.save(campaign)
        return campaign

    @staticmethod
    def _require_editor(actor: WorkflowActor, action: str) -> None:
        if actor.role not in {Role.OWNER, Role.EDITOR}:
            raise InvalidTransitionError(f"Only an owner or editor can {action}.")

    @staticmethod
    def _require_reviewer(actor: WorkflowActor, campaign: Campaign, stage_name: str) -> None:
        if actor.role not in {Role.OWNER, Role.REVIEWER}:
            if actor.user_id == campaign.created_by:
                raise InvalidTransitionError(f"An editor cannot approve their own {stage_name}.")
            raise InvalidTransitionError(f"Only an owner or reviewer can approve {stage_name}.")

    @staticmethod
    def _approval(stage: CampaignStage, actor: WorkflowActor) -> Approval:
        return Approval(
            stage=stage,
            actor_user_id=actor.user_id,
            created_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def _revision(
        revision: int,
        stage: CampaignStage,
        actor: WorkflowActor,
        context: RevisionContext,
    ) -> CampaignRevision:
        return CampaignRevision(
            revision=revision,
            stage=stage,
            actor_user_id=actor.user_id,
            created_at=datetime.now(UTC).isoformat(),
            source=context.source,
            model=context.model,
            prompt_version=context.prompt_version,
            run_id=context.run_id,
        )
