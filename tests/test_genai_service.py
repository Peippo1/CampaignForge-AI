from pathlib import Path

from genai.schemas import CampaignBrief
from genai.service import CampaignBriefService
from genai.storage import CampaignStorage


def test_generate_and_save_campaign_brief(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key="key-a",
    )
    service = CampaignBriefService(storage=storage)
    manifest = service.generate_and_save(
        CampaignBrief(
            campaign_name="Demo Launch",
            product_name="CampaignForge AI",
            brief=(
                "Launch CampaignForge AI to modern marketing teams that need "
                "structured messaging and prompt-ready outputs."
            ),
            target_market="modern marketing teams",
            channels=["LinkedIn", "Email"],
        ),
        workspace_id="workspace-a",
        actor_user_id="user-a",
    )

    assert manifest.campaign_id.startswith("demo-launch-")
    assert manifest.workspace_id == "workspace-a"
    assert manifest.created_by == "user-a"
    assert manifest.output.angles
    assert len(manifest.output.angles[0].headlines) == 5
    assert (tmp_path / "generated" / "metadata" / "campaigns.sqlite3").exists()
    assert manifest.artifacts.manifest_path == f"campaign-record://{manifest.campaign_id}/manifest"
    assert manifest.artifacts.copy_output_path == f"campaign-record://{manifest.campaign_id}/copy"
    assert service.load_campaign(manifest.campaign_id, workspace_id="workspace-a") is not None


def test_workspace_scope_blocks_cross_workspace_reads(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key="key-a",
    )
    storage.create_workspace(
        workspace_id="workspace-b",
        name="Workspace B",
        owner_user_id="user-b",
        api_key="key-b",
    )
    service = CampaignBriefService(storage=storage)
    manifest = service.generate_and_save(
        CampaignBrief(
            campaign_name="Scoped Launch",
            product_name="CampaignForge AI",
            brief="Create a workspace-scoped campaign record with isolated access boundaries.",
        ),
        workspace_id="workspace-a",
        actor_user_id="user-a",
    )

    assert service.load_campaign(manifest.campaign_id, workspace_id="workspace-a") is not None
    assert service.load_campaign(manifest.campaign_id, workspace_id="workspace-b") is None
