from __future__ import annotations

from pathlib import Path
import shutil
from typing import Protocol


class AssetStore(Protocol):
    def image_output_dir(self, campaign_id: str) -> Path:
        ...

    def export_output_path(self, campaign_id: str) -> Path:
        ...

    def reference_for_path(self, path: Path) -> str:
        ...

    def resolve_reference(self, reference: str) -> Path:
        ...

    def delete_campaign_images(self, campaign_id: str) -> None:
        ...

    def delete_reference(self, reference: str) -> None:
        ...


class LocalAssetStore:
    """Filesystem-backed asset store used by local demos and starter deployments."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()
        self.asset_root = self.root / "assets"
        self.image_root = self.asset_root / "images"
        self.export_root = self.asset_root / "exports"
        for directory in (self.root, self.asset_root, self.image_root, self.export_root):
            directory.mkdir(parents=True, exist_ok=True)

    def image_output_dir(self, campaign_id: str) -> Path:
        return self.image_root / campaign_id

    def export_output_path(self, campaign_id: str) -> Path:
        return self.export_root / f"{campaign_id}.zip"

    def reference_for_path(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root))

    def resolve_reference(self, reference: str) -> Path:
        resolved = (self.root / reference).resolve()
        if self.root not in resolved.parents and resolved != self.root:
            raise ValueError("Asset reference resolves outside the asset store root")
        return resolved

    def delete_campaign_images(self, campaign_id: str) -> None:
        image_dir = self.image_output_dir(campaign_id)
        if image_dir.exists():
            shutil.rmtree(image_dir)

    def delete_reference(self, reference: str) -> None:
        asset_path = self.resolve_reference(reference)
        if asset_path.exists():
            asset_path.unlink()
