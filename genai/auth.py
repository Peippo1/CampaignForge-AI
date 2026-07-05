from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import os


@dataclass(frozen=True)
class WorkspacePrincipal:
    workspace_id: str
    user_id: str
    role: str
    request_limit_per_hour: int


class AuthenticationError(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


class UsageLimitExceededError(RuntimeError):
    pass


class AuthManager:
    def __init__(self, storage):
        self.storage = storage
        self.auth_mode = os.getenv("CAMPAIGNFORGE_AUTH_MODE", "disabled").lower()
        self.dashboard_auth_mode = os.getenv("CAMPAIGNFORGE_DASHBOARD_AUTH_MODE", self.auth_mode).lower()
        self.default_workspace_id = os.getenv("CAMPAIGNFORGE_DEFAULT_WORKSPACE_ID", "local-demo")
        self.default_workspace_name = os.getenv("CAMPAIGNFORGE_DEFAULT_WORKSPACE_NAME", "Local demo workspace")
        self.default_api_key = os.getenv("CAMPAIGNFORGE_DEFAULT_API_KEY", "campaignforge-demo-key")
        self.default_user_id = os.getenv("CAMPAIGNFORGE_DEFAULT_USER_ID", "local-operator")
        self.default_request_limit = int(os.getenv("CAMPAIGNFORGE_DEFAULT_REQUEST_LIMIT_PER_HOUR", "60"))
        self.dashboard_username = os.getenv("CAMPAIGNFORGE_DASHBOARD_USERNAME", "operator")
        self.dashboard_password = os.getenv("CAMPAIGNFORGE_DASHBOARD_PASSWORD", "campaignforge-demo-password")
        self.seed_workspaces()

    def seed_workspaces(self) -> None:
        seeds = os.getenv("CAMPAIGNFORGE_WORKSPACE_SEEDS", "").strip()
        if seeds:
            payload = json.loads(seeds)
            for item in payload:
                self.storage.create_workspace(
                    workspace_id=item["workspace_id"],
                    name=item.get("name", item["workspace_id"]),
                    owner_user_id=item.get("user_id", "workspace-admin"),
                    api_key=item["api_key"],
                    request_limit_per_hour=item.get("request_limit_per_hour", self.default_request_limit),
                    role=item.get("role", "admin"),
                )
            return

        self.storage.create_workspace(
            workspace_id=self.default_workspace_id,
            name=self.default_workspace_name,
            owner_user_id=self.default_user_id,
            api_key=self.default_api_key,
            request_limit_per_hour=self.default_request_limit,
            role="admin",
        )

    def is_api_auth_enabled(self) -> bool:
        return self.auth_mode != "disabled"

    def is_dashboard_auth_enabled(self) -> bool:
        return self.dashboard_auth_mode != "disabled"

    def demo_principal(self) -> WorkspacePrincipal:
        return WorkspacePrincipal(
            workspace_id=self.default_workspace_id,
            user_id=self.default_user_id,
            role="admin",
            request_limit_per_hour=self.default_request_limit,
        )

    def authenticate_api_key(self, api_key: str | None) -> WorkspacePrincipal:
        if not self.is_api_auth_enabled():
            return self.demo_principal()
        if not api_key:
            raise AuthenticationError("Missing API key.")
        principal = self.storage.resolve_api_key(api_key)
        if principal is None:
            raise AuthenticationError("Invalid API key.")
        return WorkspacePrincipal(**principal)

    def authenticate_dashboard(self, username: str, password: str) -> WorkspacePrincipal:
        if not self.is_dashboard_auth_enabled():
            return self.demo_principal()
        if username != self.dashboard_username or password != self.dashboard_password:
            raise AuthenticationError("Invalid dashboard credentials.")
        return self.demo_principal()

    def enforce_usage_limit(self, principal: WorkspacePrincipal, action: str) -> None:
        if not self.is_api_auth_enabled():
            return
        cutoff = datetime.now(UTC) - timedelta(hours=1)
        usage_count = self.storage.count_audit_events(
            workspace_id=principal.workspace_id,
            action=action,
            created_after=cutoff,
            status="success",
        )
        if usage_count >= principal.request_limit_per_hour:
            raise UsageLimitExceededError(
                f"Workspace {principal.workspace_id} exceeded the hourly limit for {action}."
            )
