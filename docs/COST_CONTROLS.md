# Early-version cost controls

- Text model default: `gpt-5.6-luna`; switch models only through environment configuration.
- Image default: `gpt-image-1-mini`, maximum two images per approved run.
- Tests and demos use deterministic mock adapters and make no paid requests.
- A reviewer/owner must confirm image count and estimated cost before a worker can run.
- Initial workspace budget defaults to 2,000 minor currency units (£20 in the sample workspace).
- Cloud Tasks dispatches at one job/second with at most two concurrent jobs.
- Cloud Run starts at zero and is capped at two instances.
- Staging SQL defaults to a small zonal shared-core tier; production sizing must be reviewed before launch.
- Google and Meta connectors remain disconnected fixtures until production OAuth approval.

The application still needs a PostgreSQL-backed usage ledger and atomic budget reservation before paid multi-user production. Provider dashboards and GCP billing budgets remain required backstops.
