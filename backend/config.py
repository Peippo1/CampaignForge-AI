from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    environment: str
    database_url: str | None
    firebase_project_id: str | None
    gcp_project_id: str | None
    gcp_region: str
    asset_bucket: str | None
    tasks_queue: str | None
    tasks_worker_url: str | None
    text_model: str
    image_model: str
    monthly_ai_budget_minor: int
    image_max_per_run: int
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            environment=os.getenv("CAMPAIGNFORGE_ENV", "development").lower(),
            database_url=os.getenv("DATABASE_URL"),
            firebase_project_id=os.getenv("FIREBASE_PROJECT_ID"),
            gcp_project_id=os.getenv("GCP_PROJECT_ID"),
            gcp_region=os.getenv("GCP_REGION", "europe-west2"),
            asset_bucket=os.getenv("GCS_ASSET_BUCKET"),
            tasks_queue=os.getenv("CLOUD_TASKS_QUEUE"),
            tasks_worker_url=os.getenv("CLOUD_TASKS_WORKER_URL"),
            text_model=os.getenv("OPENAI_TEXT_MODEL", "gpt-5.6-luna"),
            image_model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1-mini"),
            monthly_ai_budget_minor=int(os.getenv("CAMPAIGNFORGE_MONTHLY_AI_BUDGET_MINOR", "2000")),
            image_max_per_run=int(os.getenv("CAMPAIGNFORGE_IMAGE_MAX_PER_RUN", "2")),
            allowed_origins=tuple(
                origin.strip()
                for origin in os.getenv("CAMPAIGNFORGE_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
                if origin.strip()
            ),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.image_max_per_run < 1 or self.image_max_per_run > 4:
            raise ValueError("CAMPAIGNFORGE_IMAGE_MAX_PER_RUN must be between 1 and 4.")
        if self.monthly_ai_budget_minor < 0:
            raise ValueError("CAMPAIGNFORGE_MONTHLY_AI_BUDGET_MINOR cannot be negative.")
        if self.environment == "production":
            required = {
                "DATABASE_URL": self.database_url,
                "FIREBASE_PROJECT_ID": self.firebase_project_id,
                "GCP_PROJECT_ID": self.gcp_project_id,
                "GCS_ASSET_BUCKET": self.asset_bucket,
                "CLOUD_TASKS_QUEUE": self.tasks_queue,
                "CLOUD_TASKS_WORKER_URL": self.tasks_worker_url,
                "CAMPAIGNFORGE_ALLOWED_ORIGINS": self.allowed_origins,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise ValueError(f"Missing production configuration: {', '.join(missing)}")
            if self.database_url and self.database_url.startswith("sqlite"):
                raise ValueError("Production DATABASE_URL must use PostgreSQL.")
