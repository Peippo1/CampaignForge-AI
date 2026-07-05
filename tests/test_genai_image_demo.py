from pathlib import Path

from genai.image_demo import resolve_default_angle_id
from genai.schemas import CampaignBrief
from genai.service import CampaignBriefService
from genai.storage import CampaignStorage


def test_resolve_default_angle_id_uses_first_saved_campaign_angle(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    campaign = CampaignBriefService(storage=storage).generate_and_save(
        CampaignBrief(
            campaign_name="Image Demo",
            product_name="CampaignForge AI",
            brief="Create a campaign with image prompts for the demo image generation step.",
        )
    )

    angle_id = resolve_default_angle_id(campaign.campaign_id, storage=storage)

    assert angle_id == campaign.output.angles[0].angle_id
