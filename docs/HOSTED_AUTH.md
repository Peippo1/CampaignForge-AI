# Hosted auth and workspace boundary

CampaignForge AI now has a minimal hosted-deployment control layer built around workspaces, API keys, dashboard sign-in, and usage tracking.

## Model

- Workspace: the tenant boundary for campaign data
- User: the actor represented by an API key or dashboard session
- Role: currently tracked as metadata for future admin/editor separation

## Current implementation

- FastAPI can run in `CAMPAIGNFORGE_AUTH_MODE=workspace_api_key`
- requests authenticate with `X-CampaignForge-API-Key` or `Authorization: Bearer <key>`
- campaign list, read, regenerate, image, and export paths are scoped by workspace
- dashboard access can run in `CAMPAIGNFORGE_DASHBOARD_AUTH_MODE=password`
- usage is limited through per-workspace hourly request caps
- audit events are stored for campaign and asset actions

## Storage scoping

Campaign records carry `workspace_id` and `created_by` metadata. Campaign list, load, image manifest, asset, and export paths all require the caller workspace to match the campaign workspace before content is returned.

This keeps hosted auth meaningful below the API surface: an authenticated workspace can only read, regenerate, review, or export its own campaign records and managed assets.

## Demo vs hosted posture

Code asset / demo mode:

- `CAMPAIGNFORGE_AUTH_MODE=disabled`
- `CAMPAIGNFORGE_DASHBOARD_AUTH_MODE=disabled`
- useful for local review and buyer demos

Hosted mode:

- `CAMPAIGNFORGE_AUTH_MODE=workspace_api_key`
- `CAMPAIGNFORGE_DASHBOARD_AUTH_MODE=password`
- requires seeded workspace/API key credentials

## Limitations

- this is a starter hosted-control layer, not a full SaaS identity system
- dashboard auth is environment-backed rather than a full user database
- API key issuance and rotation are not yet exposed as admin workflows
- role separation is not yet enforced beyond stored metadata

## Follow-on work

- `#48` managed database migration for hosted campaign records
- `#49` object-storage abstraction for image and export assets
- future auth expansion for multi-user hosted deployment
