# CampaignForge GCP foundation

This Terraform creates the low-cost hosted foundation in `europe-west2`: a scale-to-zero Cloud Run API, a private versioned asset bucket, throttled Cloud Tasks queue, KMS key, Secret Manager entry, and a small zonal PostgreSQL instance.

It intentionally does not create secret versions, database users, Firebase, OAuth applications, DNS, or GitHub/Vercel identity federation. Supply those through the deployment environment; never commit their values. The default shared-core SQL tier is suitable for staging and early low traffic, not an availability-sensitive production launch.

```bash
terraform init
terraform plan -var='project_id=YOUR_PROJECT' -var='api_image=REGION-docker.pkg.dev/PROJECT/REPO/IMAGE@sha256:DIGEST'
```

Before apply, set a billing budget/alerts in the GCP billing account. After apply, attach Cloud SQL to Cloud Run, provide `DATABASE_URL`, `FIREBASE_PROJECT_ID`, `CLOUD_TASKS_WORKER_URL`, and an OpenAI secret version, then run `alembic upgrade head` as a one-off migration job.
