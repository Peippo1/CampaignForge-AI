from pathlib import Path

from genai.auth import AuthManager, AuthenticationError, UsageLimitExceededError
from genai.storage import CampaignStorage


def test_auth_manager_resolves_seeded_api_keys(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key="key-a",
        request_limit_per_hour=7,
    )
    auth_manager = AuthManager(storage)
    auth_manager.auth_mode = "workspace_api_key"

    principal = auth_manager.authenticate_api_key("key-a")

    assert principal.workspace_id == "workspace-a"
    assert principal.user_id == "user-a"
    assert principal.request_limit_per_hour == 7


def test_auth_manager_rejects_unknown_api_keys(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    auth_manager = AuthManager(storage)
    auth_manager.auth_mode = "workspace_api_key"

    try:
        auth_manager.authenticate_api_key("not-a-real-key")
    except AuthenticationError as exc:
        assert "Invalid API key" in str(exc)
    else:
        raise AssertionError("Expected AuthenticationError for unknown API key")


def test_usage_limit_is_enforced_from_audit_history(tmp_path: Path):
    storage = CampaignStorage(root=tmp_path / "generated")
    storage.create_workspace(
        workspace_id="workspace-a",
        name="Workspace A",
        owner_user_id="user-a",
        api_key="key-a",
        request_limit_per_hour=1,
    )
    auth_manager = AuthManager(storage)
    auth_manager.auth_mode = "workspace_api_key"
    principal = auth_manager.authenticate_api_key("key-a")

    storage.record_audit_event(
        workspace_id=principal.workspace_id,
        user_id=principal.user_id,
        action="campaign:create",
        campaign_id="campaign-1",
        status="success",
    )

    try:
        auth_manager.enforce_usage_limit(principal, "campaign:create")
    except UsageLimitExceededError:
        pass
    else:
        raise AssertionError("Expected usage cap enforcement")
