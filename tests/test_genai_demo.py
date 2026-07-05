import json
from pathlib import Path

from genai.demo import load_campaign_brief


def test_load_campaign_brief_uses_pydantic_compatible_validation(tmp_path: Path):
    brief_path = tmp_path / "campaign_brief.json"
    brief_path.write_text(
        json.dumps(
            {
                "campaign_name": "Demo Launch",
                "product_name": "CampaignForge AI",
                "brief": "Create a campaign planning workflow from a short brief.",
                "target_market": "small marketing teams",
                "channels": ["LinkedIn", "Email"],
            }
        ),
        encoding="utf-8",
    )

    brief = load_campaign_brief(brief_path)

    assert brief.campaign_name == "Demo Launch"
    assert brief.channels == ["LinkedIn", "Email"]
