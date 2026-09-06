from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import PurePosixPath
from typing import BinaryIO
from uuid import uuid4


MAX_ASSET_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "image/png",
    "image/jpeg",
}


class AssetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StoredAsset:
    asset_id: str
    object_name: str
    content_type: str
    size_bytes: int


def validate_asset(*, content_type: str, size_bytes: int) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise AssetValidationError("Unsupported asset type.")
    if size_bytes < 1 or size_bytes > MAX_ASSET_BYTES:
        raise AssetValidationError("Asset must be between 1 byte and 10 MB.")


class GCSAssetStore:
    """Private object storage with short-lived signed reads."""

    def __init__(self, bucket_name: str) -> None:
        from google.cloud import storage

        self.bucket = storage.Client().bucket(bucket_name)

    def upload(
        self,
        *,
        workspace_id: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        stream: BinaryIO,
    ) -> StoredAsset:
        validate_asset(content_type=content_type, size_bytes=size_bytes)
        asset_id = str(uuid4())
        safe_name = PurePosixPath(filename).name
        object_name = f"workspaces/{workspace_id}/assets/{asset_id}/{safe_name}"
        blob = self.bucket.blob(object_name)
        blob.upload_from_file(stream, content_type=content_type, size=size_bytes, rewind=True)
        return StoredAsset(asset_id, object_name, content_type, size_bytes)

    def signed_download_url(self, object_name: str, *, minutes: int = 10) -> str:
        if minutes < 1 or minutes > 15:
            raise ValueError("Signed download lifetime must be between 1 and 15 minutes.")
        return self.bucket.blob(object_name).generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=minutes),
            method="GET",
        )
