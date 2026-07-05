from __future__ import annotations

from datetime import datetime, UTC
import json
from pathlib import Path
import zipfile

from genai.brief_parser import slugify_campaign_name
from genai.copy_generator import MockCampaignGenerator, get_campaign_generator
from genai.image_generator import MockImageGenerator, get_image_generator
from genai.pydantic_compat import model_copy, model_to_dict, model_to_json
from genai.schemas import (
    CampaignBrief,
    CampaignManifest,
    CampaignRegenerationRequest,
    ImageGenerationManifest,
    ImageGenerationRequest,
    ImageReviewRequest,
)
from genai.storage import CampaignStorage


class CampaignBriefService:
    def __init__(self, storage: CampaignStorage | None = None):
        self.storage = storage or CampaignStorage()

    def generate_and_save(
        self,
        brief: CampaignBrief,
        *,
        workspace_id: str = "local-demo",
        actor_user_id: str = "local-operator",
    ) -> CampaignManifest:
        generator = get_campaign_generator()
        try:
            output = generator.generate(brief)
            provider_name = generator.provider_name
            mode = generator.mode
        except Exception:
            fallback = MockCampaignGenerator()
            output = fallback.generate(brief)
            provider_name = fallback.provider_name
            mode = "fallback-mock"

        base_name = brief.campaign_name or brief.product_name or "campaignforge-brief"
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        campaign_id = f"{slugify_campaign_name(base_name)}-{timestamp}"
        return self.storage.save(
            campaign_id,
            provider_name,
            mode,
            brief,
            output,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
        )

    def load_campaign(self, campaign_id: str, *, workspace_id: str | None = None) -> CampaignManifest | None:
        return self.storage.load(campaign_id, workspace_id=workspace_id)

    def list_campaigns(self, *, workspace_id: str | None = None) -> list[CampaignManifest]:
        return self.storage.list_campaigns(workspace_id=workspace_id)

    def regenerate(
        self,
        campaign_id: str,
        request: CampaignRegenerationRequest | None = None,
        *,
        workspace_id: str | None = None,
    ) -> CampaignManifest:
        existing = self.storage.load(campaign_id, workspace_id=workspace_id)
        if existing is None:
            raise ValueError("Campaign output not found")

        generator = get_campaign_generator()
        try:
            output = generator.generate(existing.brief)
            provider_name = generator.provider_name
            mode = generator.mode
        except Exception:
            fallback = MockCampaignGenerator()
            output = fallback.generate(existing.brief)
            provider_name = fallback.provider_name
            mode = "fallback-mock"

        scope = request.scope if request else "all"
        if scope == "copy":
            for old_angle, new_angle in zip(existing.output.angles, output.angles):
                old_angle.headlines = new_angle.headlines
                old_angle.body_copy = new_angle.body_copy
                old_angle.ctas = new_angle.ctas
                old_angle.summary = new_angle.summary
            existing.output.campaign_summary = output.campaign_summary
            existing.output.audience_suggestions = output.audience_suggestions
            existing.output.channel_recommendations = output.channel_recommendations
            existing.output.tone_options = output.tone_options
        elif scope == "prompts":
            for old_angle, new_angle in zip(existing.output.angles, output.angles):
                old_angle.image_prompts = new_angle.image_prompts
        else:
            existing.output = output

        existing.provider = provider_name
        existing.mode = mode
        existing.updated_at = datetime.now(UTC).isoformat()
        return self.storage.overwrite_campaign(existing)


class CampaignImageService:
    def __init__(self, storage: CampaignStorage | None = None):
        self.storage = storage or CampaignStorage()

    def generate_and_save(
        self,
        request: ImageGenerationRequest,
        *,
        workspace_id: str | None = None,
    ) -> ImageGenerationManifest:
        campaign = self.storage.load(request.campaign_id, workspace_id=workspace_id)
        if campaign is None:
            raise ValueError("Campaign output not found")

        selected_angle = None
        if request.angle_id:
            selected_angle = next(
                (angle for angle in campaign.output.angles if angle.angle_id == request.angle_id),
                None,
            )
            if selected_angle is None:
                raise ValueError("Campaign angle not found")

        prompt = request.prompt
        if not prompt:
            if selected_angle and selected_angle.image_prompts:
                prompt = selected_angle.image_prompts[0]
            else:
                raise ValueError("A prompt or valid angle_id is required")

        generator = get_image_generator()
        image_dir = self.storage.campaign_image_dir(request.campaign_id)
        try:
            assets = generator.generate(
                output_dir=image_dir,
                campaign_id=request.campaign_id,
                prompt=prompt,
                style=request.style,
                count=request.count,
            )
            provider_name = generator.provider_name
            mode = generator.mode
        except Exception:
            fallback = MockImageGenerator()
            assets = fallback.generate(
                output_dir=image_dir,
                campaign_id=request.campaign_id,
                prompt=prompt,
                style=request.style,
                count=request.count,
            )
            provider_name = fallback.provider_name
            mode = "fallback-mock"

        relative_assets = [
            model_copy(asset, update={"file_path": self.storage.relative_path(Path(asset.file_path))})
            for asset in assets
        ]
        manifest = ImageGenerationManifest(
            campaign_id=request.campaign_id,
            angle_id=request.angle_id,
            created_at=datetime.now(UTC).isoformat(),
            provider=provider_name,
            mode=mode,
            style=request.style,
            prompt=prompt,
            assets=relative_assets,
        )
        return self.storage.save_image_manifest(manifest)

    def load_manifest(self, campaign_id: str, *, workspace_id: str | None = None) -> ImageGenerationManifest | None:
        return self.storage.load_image_manifest(campaign_id, workspace_id=workspace_id)

    def review_asset(
        self,
        campaign_id: str,
        request: ImageReviewRequest,
        *,
        workspace_id: str | None = None,
    ) -> ImageGenerationManifest:
        manifest = self.storage.load_image_manifest(campaign_id, workspace_id=workspace_id)
        if manifest is None:
            raise ValueError("Campaign image output not found")

        updated = False
        for asset in manifest.assets:
            if asset.image_id == request.image_id:
                asset.approval_status = request.approval_status
                updated = True
                break
        if not updated:
            raise ValueError("Image asset not found")

        manifest.updated_at = datetime.now(UTC).isoformat()
        return self.storage.save_image_manifest(manifest)


class CampaignExportService:
    def __init__(self, storage: CampaignStorage | None = None):
        self.storage = storage or CampaignStorage()

    def export_campaign(self, campaign_id: str, *, workspace_id: str | None = None) -> Path:
        campaign = self.storage.load(campaign_id, workspace_id=workspace_id)
        if campaign is None:
            raise ValueError("Campaign output not found")

        image_manifest = self.storage.load_image_manifest(campaign_id, workspace_id=workspace_id)
        export_path = self.storage.export_zip_path(campaign_id)
        prompt_payload = self.storage.campaign_prompt_payload(campaign)

        with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("brief.json", model_to_json(campaign.brief, indent=2))
            archive.writestr("copy.json", json.dumps(model_to_dict(campaign.output), indent=2))
            archive.writestr("prompts.json", json.dumps(prompt_payload, indent=2))
            archive.writestr("manifest.json", model_to_json(campaign, indent=2))

            if image_manifest is not None:
                archive.writestr("images/manifest.json", model_to_json(image_manifest, indent=2))
                for asset in image_manifest.assets:
                    asset_path = self.storage.resolve_managed_path(asset.file_path)
                    if asset_path.exists():
                        archive.write(asset_path, arcname=f"images/{asset_path.name}")

        campaign.artifacts.export_zip_path = self.storage.relative_path(export_path)
        campaign.updated_at = datetime.now(UTC).isoformat()
        self.storage.overwrite_campaign(campaign)
        self.storage.persist_export_path(campaign_id, export_path, workspace_id=campaign.workspace_id or "local-demo")
        return export_path
