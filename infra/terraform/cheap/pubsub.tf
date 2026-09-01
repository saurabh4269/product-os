resource "google_pubsub_topic" "signals" {
  name       = "loop.signals"
  depends_on = [google_project_service.cheap]
}

resource "google_pubsub_topic" "verification" {
  name       = "loop.verification"
  depends_on = [google_project_service.cheap]
}

resource "google_pubsub_subscription" "signals_push" {
  name  = "loop.signals.loop-push"
  topic = google_pubsub_topic.signals.name
  push_config {
    push_endpoint = "${var.loop_public_url}/api/internal/pubsub/signals"
    oidc_token {
      service_account_email = replace(local.runtime_member, "serviceAccount:", "")
      audience              = var.loop_public_url
    }
  }
  ack_deadline_seconds = 30
  depends_on           = [google_project_service.cheap]
}
