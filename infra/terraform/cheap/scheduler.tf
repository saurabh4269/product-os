variable "scheduler_enabled" {
  type    = bool
  default = true
}

resource "google_cloud_scheduler_job" "loop_worker_tick" {
  count       = var.scheduler_enabled ? 1 : 0
  name        = "loop-worker-tick"
  description = "BQ detect + auto-investigate + job drain"
  schedule    = "*/10 * * * *"
  time_zone   = "UTC"
  region      = var.region
  project     = var.project_id

  http_target {
    http_method = "POST"
    uri         = "${var.loop_public_url}/api/internal/worker/tick"
    headers = {
      "Content-Type" = "application/json"
    }
    oidc_token {
      service_account_email = replace(local.runtime_member, "serviceAccount:", "")
      audience              = var.loop_public_url
    }
  }

  depends_on = [google_project_service.cheap]
}
