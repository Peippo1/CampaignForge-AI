from pathlib import Path

from genai.schemas import CampaignBrief, ImageGenerationRequest
from genai.service import CampaignBriefService, CampaignImageService
from genai.storage import CampaignStorage


def test_generate_and_save_campaign_images(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "data" / "generated")
    brief_service = CampaignBriefService(storage=storage)
    image_service = CampaignImageService(storage=storage)

    campaign = brief_service.generate_and_save(
        CampaignBrief(
            campaign_name="Image Demo",
            product_name="CampaignForge AI",
            brief=(
                "Create a campaign concept workflow for teams that need "
                "messaging and visual prompts."
            ),
            channels=["LinkedIn", "Email"],
        )
    )

    manifest = image_service.generate_and_save(
        ImageGenerationRequest(
            campaign_id=campaign.campaign_id,
            angle_id=campaign.output.angles[0].angle_id,
            style="Concept board",
            count=2,
        )
    )

    assert manifest.campaign_id == campaign.campaign_id
    assert len(manifest.assets) == 2
    assert manifest.assets[0].file_path.endswith(".svg")
    image_dir = tmp_path / "data" / "generated" / "assets" / "images" / campaign.campaign_id
    assert list(image_dir.glob("*.svg"))
    assert image_service.load_manifest(campaign.campaign_id) is not None
