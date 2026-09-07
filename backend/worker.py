from __future__ import annotations

from inspect import isawaitable
from typing import Any

from backend.agents.campaign import AgentRequest, BrandContext
from backend.campaigns.workflow import CampaignWorkflow, RevisionContext, Role, WorkflowActor
from backend.jobs import JobQueue
from genai.pydantic_compat import model_to_dict


class AgentJobProcessor:
    def __init__(self, *, workflow: CampaignWorkflow, jobs: JobQueue, runner: Any, model: str) -> None:
        self.workflow = workflow
        self.jobs = jobs
        self.runner = runner
        self.model = model

    async def process(self, *, job_id: str, workspace_id: str) -> None:
        job = self.jobs.get(job_id, workspace_id)
        if job is None:
            raise KeyError(job_id)
        if job.status == "succeeded":
            return
        self.jobs.set_status(job_id, workspace_id, "running")
        try:
            campaign_id = str(job.payload["campaign_id"])
            actor = WorkflowActor(
                user_id=str(job.payload["requested_by"]),
                workspace_id=workspace_id,
                role=Role.EDITOR,
            )
            campaign = self.workflow.validate_generation(actor, campaign_id, job.kind.removeprefix("agent."))
            brand = job.payload.get("brand") or {}
            request = AgentRequest(
                campaign_name=campaign.title,
                brief=str(job.payload["instructions"]),
                brand=BrandContext(
                    voice=brand.get("voice", "Clear, credible, and useful"),
                    audiences=brand.get("audiences", []),
                    product_facts=brand.get("product_facts", []),
                    required_terms=brand.get("required_phrases", []),
                    banned_terms=brand.get("banned_terms", []),
                    compliance_rules=brand.get("compliance_rules", []),
                ),
            )
            result = self.runner.run(request)
            if isawaitable(result):
                result = await result
            context = RevisionContext(
                source="agent",
                model=self.model,
                prompt_version="campaign-manager-v1",
                run_id=job_id,
            )
            if job.kind == "agent.strategy":
                self.workflow.submit_strategy(
                    actor,
                    campaign_id,
                    model_to_dict(result.strategy),
                    revision_context=context,
                )
            elif job.kind == "agent.copy":
                payload = {**model_to_dict(result.copy_draft), "creative": model_to_dict(result.creative)}
                self.workflow.submit_copy(actor, campaign_id, payload, revision_context=context)
            else:
                raise ValueError(f"Unsupported worker job kind: {job.kind}")
        except Exception:
            self.jobs.set_status(job_id, workspace_id, "failed")
            raise
        self.jobs.set_status(job_id, workspace_id, "succeeded")
