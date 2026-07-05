from __future__ import annotations

import argparse

from genai.schemas import ImageGenerationRequest
from genai.service import CampaignImageService
from genai.storage import CampaignStorage


def resolve_default_angle_id(campaign_id: str, storage: CampaignStorage | None = None) -> str:
    campaign = (storage or CampaignStorage()).load(campaign_id)
    if campaign is None:
        raise ValueError("Campaign output not found")
    if not campaign.output.angles:
        raise ValueError("Campaign output has no image-ready angles")
    return campaign.output.angles[0].angle_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CampaignForge AI image generation demo.")
    parser.add_argument("--campaign-id", required=True, help="Campaign manifest id to use for image generation.")
    parser.add_argument("--angle-id", default=None, help="Campaign angle id to use for image generation.")
    parser.add_argument("--style", default="Campaign concept board", help="Style direction for the generated concepts.")
    parser.add_argument("--count", type=int, default=2, help="Number of concepts to generate.")
    args = parser.parse_args()
    angle_id = args.angle_id or resolve_default_angle_id(args.campaign_id)

    manifest = CampaignImageService().generate_and_save(
        ImageGenerationRequest(
            campaign_id=args.campaign_id,
            angle_id=angle_id,
            style=args.style,
            count=args.count,
        )
    )
    print(f"Generated image concepts for: {manifest.campaign_id}")
    print(f"Saved {len(manifest.assets)} assets in data/generated/assets/images/{manifest.campaign_id}/")


if __name__ == "__main__":
    main()
