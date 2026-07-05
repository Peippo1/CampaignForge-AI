# Asset storage abstraction

CampaignForge AI now routes generated image assets and export bundles through an asset-store boundary.

The default implementation is still local filesystem storage. That keeps demos, downloadable codebase use, and productised-service workflows simple while avoiding direct coupling between campaign metadata and hard-coded asset paths.

## Current local backend

`LocalAssetStore` stores assets under:

- images: `CAMPAIGNFORGE_STORAGE_ROOT/assets/images/<campaign_id>/`
- exports: `CAMPAIGNFORGE_STORAGE_ROOT/assets/exports/<campaign_id>.zip`

The metadata store records relative asset references such as:

```text
assets/exports/<campaign_id>.zip
```

Those references are resolved through the asset store, not by hand-building filesystem paths in campaign services.

## Interface responsibilities

An asset store is responsible for:

- choosing the image output location for a campaign
- choosing the export bundle location for a campaign
- converting local asset paths into persisted references
- resolving persisted references back to readable local paths when using the local backend
- deleting campaign image assets during retention cleanup
- deleting referenced export bundles during retention cleanup

## Hosted direction

A hosted SaaS deployment should move binary assets from mounted disk to object storage such as S3, R2, Blob Storage, or equivalent.

The expected future backend should preserve the current behaviours while changing the implementation:

- generate or stage image/export files locally during a request or worker job
- upload generated files to object storage
- persist object keys or signed-reference metadata in the database
- stream or redirect downloads through an authenticated API route
- delete object-store keys during retention cleanup

## Current limitation

The API still serves assets through `FileResponse`, so the shipped backend remains local filesystem based. Object storage should be added as a future backend rather than implied as production-ready today.
