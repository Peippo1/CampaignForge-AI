from pathlib import Path

import pytest

from genai.asset_store import LocalAssetStore
from genai.storage import CampaignStorage


def test_campaign_storage_can_use_separate_asset_store_root(tmp_path: Path):
    metadata_root = tmp_path / "metadata-store"
    asset_store = LocalAssetStore(root=tmp_path / "asset-store")
    storage = CampaignStorage(root=metadata_root, asset_store=asset_store)

    image_dir = storage.campaign_image_dir("campaign-123")
    export_path = storage.export_zip_path("campaign-123")

    assert image_dir == tmp_path / "asset-store" / "assets" / "images" / "campaign-123"
    assert export_path == tmp_path / "asset-store" / "assets" / "exports" / "campaign-123.zip"
    assert storage.relative_path(export_path) == "assets/exports/campaign-123.zip"
    assert storage.resolve_managed_path("assets/exports/campaign-123.zip") == export_path
    assert (metadata_root / "metadata" / "campaigns.sqlite3").exists()


def test_local_asset_store_deletes_campaign_images_and_referenced_exports(tmp_path: Path):
    asset_store = LocalAssetStore(root=tmp_path / "generated")
    image_dir = asset_store.image_output_dir("campaign-123")
    image_dir.mkdir(parents=True)
    image_path = image_dir / "concept.svg"
    image_path.write_text("<svg />", encoding="utf-8")
    export_path = asset_store.export_output_path("campaign-123")
    export_path.write_bytes(b"zip")

    asset_store.delete_campaign_images("campaign-123")
    asset_store.delete_reference(asset_store.reference_for_path(export_path))

    assert not image_dir.exists()
    assert not export_path.exists()


def test_local_asset_store_rejects_references_outside_root(tmp_path: Path):
    asset_store = LocalAssetStore(root=tmp_path / "generated")

    with pytest.raises(ValueError, match="outside the asset store root"):
        asset_store.resolve_reference("../outside.zip")
