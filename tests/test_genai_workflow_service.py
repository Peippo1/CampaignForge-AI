from pathlib import Path

from genai.schemas import (
    CampaignBrief,
    CampaignRegenerationRequest,
    ImageGenerationRequest,
    ImageReviewRequest,
)
from genai.service import CampaignBriefService, CampaignExportService, CampaignImageService
from genai.storage import CampaignStorage


def test_campaign_regeneration_and_export(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "data" / "generated")
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key="key-a",
    )
    brief_service = CampaignBriefService(storage=storage)
    image_service = CampaignImageService(storage=storage)
    export_service = CampaignExportService(storage=storage)

    campaign = brief_service.generate_and_save(
        CampaignBrief(
            campaign_name="Workflow Demo",
            product_name="CampaignForge AI",
            brief=(
                "Create a reusable campaign workflow with copy, prompts, "
                "concept images, and export support."
            ),
        ),
        workspace_id="workspace-a",
        actor_user_id="user-a",
    )

    regenerated = brief_service.regenerate(
        campaign.campaign_id,
        CampaignRegenerationRequest(scope="copy"),
        workspace_id="workspace-a",
    )
    assert regenerated.updated_at is not None

    image_manifest = image_service.generate_and_save(
        ImageGenerationRequest(
            campaign_id=campaign.campaign_id,
            angle_id=campaign.output.angles[0].angle_id,
            count=1,
        ),
        workspace_id="workspace-a",
    )
    reviewed = image_service.review_asset(
        campaign.campaign_id,
        ImageReviewRequest(image_id=image_manifest.assets[0].image_id, approval_status="approved"),
        workspace_id="workspace-a",
    )
    assert reviewed.assets[0].approval_status == "approved"

    export_path = export_service.export_campaign(campaign.campaign_id, workspace_id="workspace-a")
    assert export_path.exists()
    assert export_path.suffix == ".zip"
