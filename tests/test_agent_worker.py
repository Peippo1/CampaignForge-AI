import asyncio

from backend.agents.campaign import MockCampaignAgentRunner
from backend.campaigns.workflow import CampaignWorkflow, Role, WorkflowActor
from backend.jobs import InMemoryJobQueue
from backend.worker import AgentJobProcessor


def test_worker_applies_agent_strategy_with_traceable_revision():
    workflow = CampaignWorkflow()
    jobs = InMemoryJobQueue()
    actor = WorkflowActor(user_id="editor-1", workspace_id="workspace-1", role=Role.EDITOR)
    campaign = workflow.create_campaign(actor, title="Autumn launch")
    job = jobs.enqueue(
        workspace_id=actor.workspace_id,
        kind="agent.strategy",
        payload={
            "campaign_id": campaign.campaign_id,
            "instructions": "Create a clear campaign strategy for a practical product launch.",
            "requested_by": actor.user_id,
        },
    )
    processor = AgentJobProcessor(
        workflow=workflow,
        jobs=jobs,
        runner=MockCampaignAgentRunner(),
        model="mock",
    )

    asyncio.run(processor.process(job_id=job.job_id, workspace_id=actor.workspace_id))

    updated = workflow.get_campaign(actor, campaign.campaign_id)
    assert jobs.get(job.job_id, actor.workspace_id).status == "succeeded"
    assert updated.revisions[-1].source == "agent"
    assert updated.revisions[-1].run_id == job.job_id
