from __future__ import annotations

import argparse
import json
from pathlib import Path

from genai.pydantic_compat import model_validate
from genai.schemas import CampaignBrief
from genai.service import CampaignBriefService


def load_campaign_brief(path: Path) -> CampaignBrief:
    return model_validate(CampaignBrief, json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CampaignForge AI brief copilot demo.")
    parser.add_argument(
        "--input",
        default="data/demo/campaign_brief.json",
        help="Path to a JSON campaign brief file.",
    )
    args = parser.parse_args()

    brief_path = Path(args.input)
    brief = load_campaign_brief(brief_path)
    manifest = CampaignBriefService().generate_and_save(brief)
    print(f"Generated campaign brief output: {manifest.campaign_id}")
    print(f"Manifest: {manifest.artifacts.manifest_path}")
    print(f"Copy output: {manifest.artifacts.copy_output_path}")


if __name__ == "__main__":
    main()
