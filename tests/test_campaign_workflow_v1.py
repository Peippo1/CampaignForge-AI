import pytest

from backend.campaigns.workflow import (
    CampaignStage,
    CampaignWorkflow,
    InvalidTransitionError,
    Role,
    WorkflowActor,
)
from backend.campaigns.repository import SQLAlchemyCampaignRepository


def test_editor_submits_strategy_and_reviewer_approves_it():
    workflow = CampaignWorkflow()
    editor = WorkflowActor(user_id="editor-1", workspace_id="workspace-1", role=Role.EDITOR)
    reviewer = WorkflowActor(user_id="reviewer-1", workspace_id="workspace-1", role=Role.REVIEWER)

    campaign = workflow.create_campaign(editor, title="Autumn launch")
    campaign = workflow.submit_strategy(editor, campaign.campaign_id, {"summary": "A clear launch strategy."})

    assert campaign.stage is CampaignStage.STRATEGY_READY
    assert campaign.revision == 1
    assert campaign.revisions[-1].actor_user_id == editor.user_id
    assert campaign.revisions[-1].source == "manual"

    with pytest.raises(InvalidTransitionError, match="cannot approve their own"):
        workflow.approve_strategy(editor, campaign.campaign_id)

    campaign = workflow.approve_strategy(reviewer, campaign.campaign_id)

    assert campaign.stage is CampaignStage.STRATEGY_APPROVED
    assert campaign.approvals[-1].actor_user_id == reviewer.user_id


def test_campaign_requires_copy_and_asset_approval_before_final_approval():
    workflow = CampaignWorkflow()
    editor = WorkflowActor(user_id="editor-1", workspace_id="workspace-1", role=Role.EDITOR)
    reviewer = WorkflowActor(user_id="reviewer-1", workspace_id="workspace-1", role=Role.REVIEWER)

    campaign = workflow.create_campaign(editor, title="Autumn launch")
    workflow.submit_strategy(editor, campaign.campaign_id, {"summary": "Strategy"})
    workflow.approve_strategy(reviewer, campaign.campaign_id)
    workflow.submit_copy(editor, campaign.campaign_id, {"headlines": ["Make autumn count"]})
    workflow.approve_copy(reviewer, campaign.campaign_id)

    with pytest.raises(InvalidTransitionError, match="authorization"):
        workflow.complete_image_generation(campaign.campaign_id, ["asset-1"])

    workflow.authorize_image_generation(reviewer, campaign.campaign_id, count=1, estimated_cost_minor=8)
    campaign = workflow.complete_image_generation(campaign.campaign_id, ["asset-1"])

    with pytest.raises(InvalidTransitionError, match="review reason"):
        workflow.review_asset(reviewer, campaign.campaign_id, "asset-1", approved=False)

    with pytest.raises(InvalidTransitionError, match="approved"):
        workflow.final_approve(reviewer, campaign.campaign_id)

    workflow.review_asset(reviewer, campaign.campaign_id, "asset-1", approved=True)
    campaign = workflow.final_approve(reviewer, campaign.campaign_id)

    assert campaign.stage is CampaignStage.FINAL_APPROVED
    assert campaign.export_enabled is True


def test_workflow_state_survives_repository_recreation(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'hosted.sqlite3'}"
    editor = WorkflowActor(user_id="editor-1", workspace_id="workspace-1", role=Role.EDITOR)

    first = CampaignWorkflow(repository=SQLAlchemyCampaignRepository(database_url))
    campaign = first.create_campaign(editor, title="Persistent campaign")
    first.submit_strategy(editor, campaign.campaign_id, {"summary": "Persist me"})

    second = CampaignWorkflow(repository=SQLAlchemyCampaignRepository(database_url))
    restored = second.get_campaign(editor, campaign.campaign_id)

    assert restored.stage is CampaignStage.STRATEGY_READY
    assert restored.strategy == {"summary": "Persist me"}
    assert restored.revisions[0].revision == 1
