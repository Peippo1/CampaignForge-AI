output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "asset_bucket" {
  value = google_storage_bucket.assets.name
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}
