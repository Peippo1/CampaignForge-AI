from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Sequence

from genai.storage import CampaignStorage


def run_cleanup(
    *,
    storage_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    storage = CampaignStorage(root=storage_root)
    deleted_campaign_ids = storage.cleanup_expired_campaigns(now=now)
    return {
        "status": "ok",
        "deleted_campaign_count": len(deleted_campaign_ids),
        "deleted_campaign_ids": deleted_campaign_ids,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean up expired CampaignForge campaign assets.")
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=None,
        help="Override CAMPAIGNFORGE_STORAGE_ROOT for scheduled cleanup runs.",
    )
    args = parser.parse_args(argv)
    print(json.dumps(run_cleanup(storage_root=args.storage_root), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
