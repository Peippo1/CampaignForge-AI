from pathlib import Path

from genai.retention_cleanup import run_cleanup
from genai.schemas import CampaignBrief, ImageGenerationRequest
from genai.service import CampaignBriefService, CampaignExportService, CampaignImageService
from genai.storage import CampaignStorage


def _create_campaign(storage: CampaignStorage, campaign_name: str) -> str:
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key=f"key-{campaign_name}",
    )
    brief_service = CampaignBriefService(storage=storage)
    image_service = CampaignImageService(storage=storage)
    export_service = CampaignExportService(storage=storage)

    campaign = brief_service.generate_and_save(
        CampaignBrief(
            campaign_name=campaign_name,
            product_name="CampaignForge AI",
            brief="Create retained campaign output with managed image and export assets.",
        ),
        workspace_id="workspace-a",
        actor_user_id="user-a",
    )
    image_service.generate_and_save(
        ImageGenerationRequest(
            campaign_id=campaign.campaign_id,
            angle_id=campaign.output.angles[0].angle_id,
            count=1,
        ),
        workspace_id="workspace-a",
    )
    export_service.export_campaign(campaign.campaign_id, workspace_id="workspace-a")
    return campaign.campaign_id


def test_run_cleanup_removes_expired_campaign_records_and_assets(tmp_path: Path):
    root = tmp_path / "generated"
    expired_storage = CampaignStorage(root=root, retention_days=-1)
    expired_campaign_id = _create_campaign(expired_storage, "Expired Campaign")
    active_storage = CampaignStorage(root=root, retention_days=30)
    active_campaign_id = _create_campaign(active_storage, "Active Campaign")

    expired_image_dir = expired_storage.campaign_image_dir(expired_campaign_id)
    expired_export_path = expired_storage.export_zip_path(expired_campaign_id)
    assert expired_image_dir.exists()
    assert expired_export_path.exists()

    result = run_cleanup(storage_root=root)

    assert result == {
        "status": "ok",
        "deleted_campaign_count": 1,
        "deleted_campaign_ids": [expired_campaign_id],
    }
    assert CampaignStorage(root=root).load(expired_campaign_id) is None
    assert CampaignStorage(root=root).load(active_campaign_id) is not None
    assert not expired_image_dir.exists()
    assert not expired_export_path.exists()
