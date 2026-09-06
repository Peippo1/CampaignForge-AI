# Deployment and cutover

## Staging sequence

1. Create Firebase web/admin configuration and a GCP project in `europe-west2`.
2. Build `Dockerfile.hosted` and push an immutable image to Artifact Registry.
3. Review and apply `infra/terraform`; configure a billing budget first.
4. Create database credentials and Secret Manager versions outside source control.
5. Attach Cloud SQL to Cloud Run and set every production variable listed in `.env.example`.
6. Run `alembic upgrade head` as a one-off job.
7. Deploy `apps/web` to a Vercel preview with the Firebase public identifiers and API URL.
8. Verify health, Firebase access, workspace isolation, task delivery, approvals, asset signing, and mobile/keyboard workflows.

## CI/CD credentials

Use GitHub OIDC and Vercel/GCP workload identity federation. Do not store service-account JSON or long-lived cloud keys in GitHub or Vercel. Deployment jobs should use environment protection and immutable image digests.

## Direct cutover gate

Do not remove Streamlit or route production traffic until PostgreSQL counts, assets, Firebase roles, agent jobs, exports, analytics freshness, accessibility, monitoring, and rollback have passed. Retain the previous deployment image and database backup. The current branch is a staging foundation, not an authorized production cutover.
