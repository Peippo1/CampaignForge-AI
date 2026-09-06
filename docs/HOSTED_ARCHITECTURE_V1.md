# Hosted architecture v1

## Decision

CampaignForge uses a Next.js 16 app on Vercel and a FastAPI service on GCP Cloud Run. PostgreSQL is authoritative for workflow and job state, Cloud Storage holds private assets, and Cloud Tasks delivers asynchronous agent/image/export work. Both the visual workspace and campaign chat call the same `CampaignWorkflow` interface.

## Campaign boundary

`backend/campaigns/workflow.py` owns valid transitions and role gates. It does not call HTTP, Firebase, OpenAI, or GCS. Repositories isolate persistence. This keeps approval rules consistent across UI, chat, API keys, and workers.

Current stages are draft → strategy ready → strategy approved → copy ready → copy approved → image generation approved → assets ready → final approved. Paid image work requires an explicit count and estimated-cost authorization. Export is enabled only after every asset and the final campaign are approved.

## Agent boundary

The campaign manager uses typed Pydantic output and specialist agents as tools. Uploaded content and campaign fields are treated as untrusted data. Agents may draft or propose; they cannot approve, publish, spend, or bypass the campaign state machine. Sensitive trace content is disabled. Provider failures must remain explicit rather than silently falling back to mock content.

## Identity and tenancy

Firebase verifies identity; PostgreSQL membership records authorize a UID within a workspace as owner, editor, or reviewer. Development identity headers are accepted only when `CAMPAIGNFORGE_ENV=development`; staging and production fail closed without bearer-token identity. Repository reads are workspace-scoped and foreign resources return not found.

## Current implementation boundary

The vertical slice implements campaign progression, async run creation/status, agent schemas/guardrails, Firebase verification, PostgreSQL adapters/migrations, GCS upload validation/signed URLs, operational/performance UI, and connector placeholders. Durable conversations, API key lifecycle, real image workers, exports, invitations, encrypted Google/Meta OAuth tokens, scheduled sync, immutable revision/audit tables, and production SSE remain follow-up slices. The UI uses fixture data until those APIs land.
