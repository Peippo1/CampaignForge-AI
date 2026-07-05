# Hosted MVP cut

CampaignForge AI should not be hosted as a broad platform on the first release.

The smallest credible hosted cut is a narrow single-workspace or small-team workflow built on the same commercial MVP:

```text
brief -> generate -> review -> export
```

## Hosted MVP goal

Let a small team create and manage campaign packs in one protected workspace without pretending to be a full campaign operations platform.

## In scope for the first hosted cut

- workspace-scoped auth
- durable campaign metadata
- managed asset storage
- campaign history
- regenerate copy and prompts
- review image concepts
- export campaign bundles
- basic usage controls
- audit events

## Explicitly out of scope

- multi-workspace collaboration
- role-heavy approval chains
- billing and plan management
- external publishing
- enterprise admin controls
- custom model routing per tenant
- complex CRM write-back

## Dependency chain

- `#38` made campaign storage durable
- `#39` added auth, tenant boundaries, and usage controls
- `#40` established runtime and observability baseline
- `#49` introduced an asset-store boundary for future object storage

Those changes are prerequisites. They make a narrow hosted cut plausible, but they do not make it production-ready by themselves.

## Credible first hosted workflow

1. Create a brief in a protected workspace.
2. Generate campaign strategy, copy, and image prompts.
3. Regenerate weak outputs where needed.
4. Review concept images.
5. Export a handoff bundle.

## Still required before production claims

- managed relational database rollout
- non-filesystem asset backend for hosted deployments
- backup and restore plan
- secret management and deployment hardening
- error monitoring and operational alerting
- clearer hosted pricing and support model

## Positioning rule

If the hosted cut cannot make the brief-to-export workflow faster or safer for a small team, it should stay out of scope.
