locals {
  prefix = "campaignforge-${var.environment}"
  services = toset([
    "artifactregistry.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtasks.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "sqladmin.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each           = local.services
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "api" {
  account_id   = "campaignforge-api-${var.environment}"
  display_name = "CampaignForge API (${var.environment})"
}

resource "google_service_account" "worker" {
  account_id   = "campaignforge-worker"
  display_name = "CampaignForge task worker"
}

resource "google_storage_bucket" "assets" {
  name                        = "${var.project_id}-${local.prefix}-assets"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning { enabled = true }
  lifecycle_rule {
    condition { num_newer_versions = 3 }
    action { type = "Delete" }
  }
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.prefix}-postgres"
  database_version = "POSTGRES_16"
  region           = var.region
  deletion_protection = var.environment == "production"

  settings {
    tier              = var.database_tier
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = 10
    disk_autoresize   = true
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = var.environment == "production"
    }
    ip_configuration { ipv4_enabled = true }
  }
  depends_on = [google_project_service.required]
}

resource "google_sql_database" "app" {
  name     = "campaignforge"
  instance = google_sql_database_instance.postgres.name
}

resource "google_cloud_tasks_queue" "agent_runs" {
  name     = "${local.prefix}-agent-runs"
  location = var.region
  rate_limits {
    max_concurrent_dispatches = 2
    max_dispatches_per_second = 1
  }
  retry_config {
    max_attempts       = 5
    min_backoff        = "5s"
    max_backoff        = "300s"
    max_doublings      = 4
  }
  depends_on = [google_project_service.required]
}

resource "google_kms_key_ring" "app" {
  name     = local.prefix
  location = var.region
}

resource "google_kms_crypto_key" "integration_tokens" {
  name            = "integration-token-envelope"
  key_ring        = google_kms_key_ring.app.id
  rotation_period = "7776000s"
  lifecycle { prevent_destroy = true }
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "${local.prefix}-openai-api-key"
  replication { auto {} }
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "api" {
  name     = "${local.prefix}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image = var.api_image
      resources {
        limits = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }
      env { name = "CAMPAIGNFORGE_ENV" value = var.environment == "production" ? "production" : "staging" }
      env { name = "GCP_PROJECT_ID" value = var.project_id }
      env { name = "GCP_REGION" value = var.region }
      env { name = "GCS_ASSET_BUCKET" value = google_storage_bucket.assets.name }
      env { name = "CLOUD_TASKS_QUEUE" value = google_cloud_tasks_queue.agent_runs.name }
      env { name = "OPENAI_TEXT_MODEL" value = "gpt-5.6-luna" }
      env { name = "OPENAI_IMAGE_MODEL" value = "gpt-image-1-mini" }
      env { name = "CAMPAIGNFORGE_IMAGE_MAX_PER_RUN" value = "2" }
      env { name = "OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA" value = "0" }
    }
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "public_api" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "worker_invoker" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_service_account_iam_member" "api_can_sign_worker_tasks" {
  service_account_id = google_service_account.worker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.api.email}"
}

resource "google_storage_bucket_iam_member" "api_assets" {
  bucket = google_storage_bucket.assets.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_task_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.api.email}"
}
