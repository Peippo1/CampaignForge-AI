from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from genai.pydantic_compat import model_to_dict, model_to_json, model_validate
from genai.schemas import CampaignBrief, CampaignManifest, CampaignOutput, ImageGenerationManifest, SavedArtifact


def _default_generated_root() -> Path:
    configured = os.getenv("CAMPAIGNFORGE_STORAGE_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "data" / "generated"


DEFAULT_GENERATED_ROOT = _default_generated_root()
DEFAULT_RETENTION_DAYS = int(os.getenv("CAMPAIGNFORGE_RETENTION_DAYS", "30"))


class CampaignStorage:
    def __init__(self, root: Path | None = None, retention_days: int | None = None):
        self.root = (root or DEFAULT_GENERATED_ROOT).resolve()
        self.retention_days = retention_days or DEFAULT_RETENTION_DAYS
        self.metadata_dir = self.root / "metadata"
        self.asset_root = self.root / "assets"
        self.image_root = self.asset_root / "images"
        self.export_dir = self.asset_root / "exports"
        self.database_path = self.metadata_dir / "campaigns.sqlite3"
        for directory in (self.root, self.metadata_dir, self.asset_root, self.image_root, self.export_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    brief_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    export_zip_path TEXT,
                    retention_expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS image_manifests (
                    campaign_id TEXT PRIMARY KEY,
                    angle_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    provider TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    style TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    assets_json TEXT NOT NULL,
                    FOREIGN KEY(campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
                )
                """
            )
            connection.commit()

    def _retention_expires_at(self, created_at: str) -> str:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        expires = created + timedelta(days=self.retention_days)
        return expires.astimezone(UTC).isoformat()

    def _campaign_storage_uri(self, campaign_id: str, document: str) -> str:
        return f"campaign-record://{campaign_id}/{document}"

    def _campaign_from_row(self, row: sqlite3.Row) -> CampaignManifest:
        campaign_id = row["campaign_id"]
        return CampaignManifest(
            campaign_id=campaign_id,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            provider=row["provider"],
            mode=row["mode"],
            brief=model_validate(CampaignBrief, json.loads(row["brief_json"])),
            output=model_validate(CampaignOutput, json.loads(row["output_json"])),
            artifacts=SavedArtifact(
                manifest_path=self._campaign_storage_uri(campaign_id, "manifest"),
                copy_output_path=self._campaign_storage_uri(campaign_id, "copy"),
                brief_path=self._campaign_storage_uri(campaign_id, "brief"),
                prompts_path=self._campaign_storage_uri(campaign_id, "prompts"),
                export_zip_path=row["export_zip_path"],
            ),
        )

    def _image_manifest_from_row(self, row: sqlite3.Row) -> ImageGenerationManifest:
        return model_validate(
            ImageGenerationManifest,
            {
                "campaign_id": row["campaign_id"],
                "angle_id": row["angle_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "provider": row["provider"],
                "mode": row["mode"],
                "style": row["style"],
                "prompt": row["prompt"],
                "assets": json.loads(row["assets_json"]),
            }
        )

    def save(self, campaign_id: str, provider: str, mode: str, brief, output: CampaignOutput) -> CampaignManifest:
        created_at = datetime.now(UTC).isoformat()
        manifest = CampaignManifest(
            campaign_id=campaign_id,
            created_at=created_at,
            updated_at=created_at,
            provider=provider,
            mode=mode,
            brief=brief,
            output=output,
            artifacts=SavedArtifact(
                manifest_path=self._campaign_storage_uri(campaign_id, "manifest"),
                copy_output_path=self._campaign_storage_uri(campaign_id, "copy"),
                brief_path=self._campaign_storage_uri(campaign_id, "brief"),
                prompts_path=self._campaign_storage_uri(campaign_id, "prompts"),
            ),
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO campaigns (
                    campaign_id, created_at, updated_at, provider, mode,
                    brief_json, output_json, export_zip_path, retention_expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    created_at,
                    created_at,
                    provider,
                    mode,
                    model_to_json(brief),
                    model_to_json(output),
                    None,
                    self._retention_expires_at(created_at),
                ),
            )
            connection.commit()
        return manifest

    def load(self, campaign_id: str) -> CampaignManifest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
        if row is None:
            return None
        return self._campaign_from_row(row)

    def list_campaigns(self) -> list[CampaignManifest]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM campaigns ORDER BY created_at DESC"
            ).fetchall()
        return [self._campaign_from_row(row) for row in rows]

    def campaign_image_dir(self, campaign_id: str) -> Path:
        return self.image_root / campaign_id

    def save_image_manifest(self, manifest: ImageGenerationManifest) -> ImageGenerationManifest:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO image_manifests (
                    campaign_id, angle_id, created_at, updated_at,
                    provider, mode, style, prompt, assets_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    manifest.campaign_id,
                    manifest.angle_id,
                    manifest.created_at,
                    manifest.updated_at,
                    manifest.provider,
                    manifest.mode,
                    manifest.style,
                    manifest.prompt,
                    json.dumps([model_to_dict(asset) for asset in manifest.assets]),
                ),
            )
            connection.commit()
        return manifest

    def load_image_manifest(self, campaign_id: str) -> ImageGenerationManifest | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM image_manifests WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
        if row is None:
            return None
        return self._image_manifest_from_row(row)

    def overwrite_campaign(self, manifest: CampaignManifest) -> CampaignManifest:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE campaigns
                SET updated_at = ?, provider = ?, mode = ?, brief_json = ?, output_json = ?, export_zip_path = ?
                WHERE campaign_id = ?
                """,
                (
                    manifest.updated_at,
                    manifest.provider,
                    manifest.mode,
                    model_to_json(manifest.brief),
                    model_to_json(manifest.output),
                    manifest.artifacts.export_zip_path,
                    manifest.campaign_id,
                ),
            )
            connection.commit()
        return manifest

    def export_zip_path(self, campaign_id: str) -> Path:
        return self.export_dir / f"{campaign_id}.zip"

    def relative_path(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root))

    def resolve_managed_path(self, relative_path: str) -> Path:
        return (self.root / relative_path).resolve()

    def persist_export_path(self, campaign_id: str, export_zip_path: Path) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE campaigns SET export_zip_path = ?, updated_at = ? WHERE campaign_id = ?",
                (
                    self.relative_path(export_zip_path),
                    datetime.now(UTC).isoformat(),
                    campaign_id,
                ),
            )
            connection.commit()

    def cleanup_expired_campaigns(self, now: datetime | None = None) -> list[str]:
        cutoff = (now or datetime.now(UTC)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT campaign_id, export_zip_path FROM campaigns WHERE retention_expires_at <= ?",
                (cutoff,),
            ).fetchall()
            expired_ids = [row["campaign_id"] for row in rows]
            for row in rows:
                image_dir = self.campaign_image_dir(row["campaign_id"])
                if image_dir.exists():
                    shutil.rmtree(image_dir)
                export_zip_path = row["export_zip_path"]
                if export_zip_path:
                    resolved_export = self.resolve_managed_path(export_zip_path)
                    if resolved_export.exists():
                        resolved_export.unlink()
            if expired_ids:
                connection.executemany(
                    "DELETE FROM image_manifests WHERE campaign_id = ?",
                    [(campaign_id,) for campaign_id in expired_ids],
                )
                connection.executemany(
                    "DELETE FROM campaigns WHERE campaign_id = ?",
                    [(campaign_id,) for campaign_id in expired_ids],
                )
                connection.commit()
        return expired_ids

    def campaign_prompt_payload(self, manifest: CampaignManifest) -> dict[str, Any]:
        return {
            "campaign_id": manifest.campaign_id,
            "angles": [
                {
                    "angle_id": angle.angle_id,
                    "title": angle.title,
                    "image_prompts": angle.image_prompts,
                }
                for angle in manifest.output.angles
            ],
        }
