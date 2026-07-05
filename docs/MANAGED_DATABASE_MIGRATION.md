# Managed database migration plan

CampaignForge AI currently stores campaign metadata in SQLite under `CAMPAIGNFORGE_STORAGE_ROOT/metadata/campaigns.sqlite3`.

That is suitable for local demos, downloadable code assets, and small single-operator deployments. It is not the final metadata store for a hosted multi-tenant product.

## Target hosted shape

For hosted deployment, campaign metadata should move to a managed relational database such as Postgres.

The current SQLite tables map cleanly to managed tables:

- `workspaces`: tenant boundary, owner, and request limit
- `workspace_api_keys`: hashed API keys linked to workspaces and users
- `campaigns`: campaign brief, generated output, provider metadata, workspace ownership, export reference, and retention expiry
- `image_manifests`: generated image metadata linked to a campaign
- `audit_events`: API usage, approval, export, and failure receipts

Binary assets should not be stored in the relational database. Image files and export bundles should move separately to object storage, with database rows storing object keys or signed-reference metadata.

## Migration assumptions

- `workspace_id` remains the tenant boundary.
- API keys remain hashed before storage.
- campaign reads, lists, image manifests, asset access, and exports stay workspace-scoped.
- audit events remain append-only operational evidence.
- retention cleanup remains explicit and scheduled, but deletes database rows and object-store assets through the same lifecycle policy.

## Migration stages

1. Keep SQLite as the default local/starter store.
2. Add a database URL setting such as `CAMPAIGNFORGE_DATABASE_URL`.
3. Introduce a storage interface that preserves the current `CampaignStorage` public behaviours.
4. Add a Postgres-backed implementation with schema migrations.
5. Run parity tests against SQLite and Postgres for save, load, list, image manifest, export reference, audit, auth, and cleanup behaviours.
6. Add backup, restore, retention, and observability checks before positioning hosted deployment as production-ready.

## What stays local

The SQLite store should remain supported for:

- downloadable/licensed codebase use
- local demos
- productised-service preparation work
- single-user review environments

## What must change for hosted SaaS

Hosted SaaS should not rely on container-local SQLite. Before making hosted production claims, the app needs:

- managed relational database metadata
- object storage for generated assets and export bundles
- explicit migration scripts and rollback guidance
- database backups and restore testing
- operational monitoring for storage errors, cleanup failures, and auth/audit write failures

## Design constraint for current work

New hosted features should depend on storage behaviours, not SQLite internals. Code should call the storage layer for campaign ownership, listing, image manifest lookup, export references, audit events, and cleanup so that the backing store can be swapped later.
