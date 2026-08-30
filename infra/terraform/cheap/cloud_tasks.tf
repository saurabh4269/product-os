resource "google_cloud_tasks_queue" "jobs" {
  name     = "loop-jobs"
  location = var.region

  rate_limits {
    max_dispatches_per_second = 2
    max_concurrent_dispatches = 1
  }

  retry_config {
    max_attempts = 3
    min_backoff  = "10s"
    max_backoff  = "300s"
  }

  depends_on = [google_project_service.cheap]
}
