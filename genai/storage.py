from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
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

    def _ensure_column(self, connection: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table_name})")}
        if column_name not in columns:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL DEFAULT 'local-demo',
                    created_by TEXT,
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
            self._ensure_column(connection, "campaigns", "workspace_id", "workspace_id TEXT NOT NULL DEFAULT 'local-demo'")
            self._ensure_column(connection, "campaigns", "created_by", "created_by TEXT")
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workspaces (
                    workspace_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    request_limit_per_hour INTEGER NOT NULL DEFAULT 60,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_api_keys (
                    key_hash TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    campaign_id TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id) ON DELETE CASCADE
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

    def _hash_api_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def _campaign_from_row(self, row: sqlite3.Row) -> CampaignManifest:
        campaign_id = row["campaign_id"]
        return CampaignManifest(
            campaign_id=campaign_id,
            workspace_id=row["workspace_id"],
            created_by=row["created_by"],
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
            },
        )

    def create_workspace(
        self,
        *,
        workspace_id: str,
        name: str,
        owner_user_id: str,
        api_key: str,
        request_limit_per_hour: int = 60,
        role: str = "admin",
    ) -> None:
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO workspaces (
                    workspace_id, name, owner_user_id, request_limit_per_hour, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (workspace_id, name, owner_user_id, request_limit_per_hour, created_at),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO workspace_api_keys (
                    key_hash, workspace_id, user_id, role, active, created_at
                ) VALUES (?, ?, ?, ?, 1, ?)
                """,
                (self._hash_api_key(api_key), workspace_id, owner_user_id, role, created_at),
            )
            connection.commit()

    def resolve_api_key(self, api_key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT keys.workspace_id, keys.user_id, keys.role, workspaces.request_limit_per_hour
                FROM workspace_api_keys AS keys
                JOIN workspaces ON workspaces.workspace_id = keys.workspace_id
                WHERE keys.key_hash = ? AND keys.active = 1
                """,
                (self._hash_api_key(api_key),),
            ).fetchone()
        if row is None:
            return None
        return {
            "workspace_id": row["workspace_id"],
            "user_id": row["user_id"],
            "role": row["role"],
            "request_limit_per_hour": row["request_limit_per_hour"],
        }

    def save(
        self,
        campaign_id: str,
        provider: str,
        mode: str,
        brief,
        output: CampaignOutput,
        *,
        workspace_id: str,
        actor_user_id: str,
    ) -> CampaignManifest:
        created_at = datetime.now(UTC).isoformat()
        manifest = CampaignManifest(
            campaign_id=campaign_id,
            workspace_id=workspace_id,
            created_by=actor_user_id,
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
                    campaign_id, workspace_id, created_by, created_at, updated_at, provider, mode,
                    brief_json, output_json, export_zip_path, retention_expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    workspace_id,
                    actor_user_id,
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

    def load(self, campaign_id: str, *, workspace_id: str | None = None) -> CampaignManifest | None:
        query = "SELECT * FROM campaigns WHERE campaign_id = ?"
        params: list[Any] = [campaign_id]
        if workspace_id is not None:
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return self._campaign_from_row(row)

    def list_campaigns(self, *, workspace_id: str | None = None) -> list[CampaignManifest]:
        query = "SELECT * FROM campaigns"
        params: list[Any] = []
        if workspace_id is not None:
            query += " WHERE workspace_id = ?"
            params.append(workspace_id)
        query += " ORDER BY created_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
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

    def load_image_manifest(self, campaign_id: str, *, workspace_id: str | None = None) -> ImageGenerationManifest | None:
        query = """
            SELECT image_manifests.*
            FROM image_manifests
            JOIN campaigns ON campaigns.campaign_id = image_manifests.campaign_id
            WHERE image_manifests.campaign_id = ?
        """
        params: list[Any] = [campaign_id]
        if workspace_id is not None:
            query += " AND campaigns.workspace_id = ?"
            params.append(workspace_id)
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        if row is None:
            return None
        return self._image_manifest_from_row(row)

    def overwrite_campaign(self, manifest: CampaignManifest) -> CampaignManifest:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE campaigns
                SET updated_at = ?, provider = ?, mode = ?, brief_json = ?, output_json = ?, export_zip_path = ?
                WHERE campaign_id = ? AND workspace_id = ?
                """,
                (
                    manifest.updated_at,
                    manifest.provider,
                    manifest.mode,
                    model_to_json(manifest.brief),
                    model_to_json(manifest.output),
                    manifest.artifacts.export_zip_path,
                    manifest.campaign_id,
                    manifest.workspace_id,
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

    def persist_export_path(self, campaign_id: str, export_zip_path: Path, *, workspace_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE campaigns SET export_zip_path = ?, updated_at = ? WHERE campaign_id = ? AND workspace_id = ?",
                (
                    self.relative_path(export_zip_path),
                    datetime.now(UTC).isoformat(),
                    campaign_id,
                    workspace_id,
                ),
            )
            connection.commit()

    def record_audit_event(
        self,
        *,
        workspace_id: str,
        user_id: str | None,
        action: str,
        status: str,
        campaign_id: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (workspace_id, user_id, action, campaign_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    user_id,
                    action,
                    campaign_id,
                    status,
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.commit()

    def count_audit_events(
        self,
        *,
        workspace_id: str,
        action: str,
        created_after: datetime,
        status: str | None = None,
    ) -> int:
        query = """
            SELECT COUNT(*) AS count
            FROM audit_events
            WHERE workspace_id = ? AND action = ? AND created_at >= ?
        """
        params: list[Any] = [workspace_id, action, created_after.isoformat()]
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return int(row["count"]) if row else 0

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
