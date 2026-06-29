# Durable storage for generated campaigns

CampaignForge AI no longer treats repository-local JSON files as the system of record for generated campaigns.

## Storage boundaries

- Campaign briefs, generated copy outputs, prompt metadata, provider metadata, and export references are stored in a durable SQLite metadata store.
- Generated image assets and export ZIP bundles are stored under a managed asset root.
- The application refers to campaign records through logical `campaign-record://...` URIs rather than assuming a manifest JSON file on disk.

## Current implementation

- Metadata store: `CAMPAIGNFORGE_STORAGE_ROOT/metadata/campaigns.sqlite3`
- Managed asset root: `CAMPAIGNFORGE_STORAGE_ROOT/assets/`
- Image assets: `CAMPAIGNFORGE_STORAGE_ROOT/assets/images/<campaign_id>/`
- Export bundles: `CAMPAIGNFORGE_STORAGE_ROOT/assets/exports/`

For local development the default storage root remains `data/generated/`.

For hosted deployment, `CAMPAIGNFORGE_STORAGE_ROOT` should point to a persistent volume or equivalent durable storage mount rather than the app container filesystem.

## Why this is better than the previous approach

- campaign records now have a durable metadata store
- the application can list and reload campaigns without reading repository JSON manifests
- image assets and export bundles are separated from source code paths
- retention can be enforced centrally rather than by ad hoc file cleanup

## Retention and cleanup

- `CAMPAIGNFORGE_RETENTION_DAYS` defaults to `30`
- each campaign record stores a retention expiry timestamp
- expired campaigns can be deleted together with their image assets and export bundles through `CampaignStorage.cleanup_expired_campaigns()`

## Hosted deployment guidance

This is a step toward deployment-grade storage, not the final storage architecture.

For a fuller hosted deployment, the likely next move is:

1. move metadata from SQLite to a managed relational database
2. move binary assets from a mounted volume to object storage
3. add tenant scoping and authorization around campaign access
4. add background cleanup and export lifecycle management
