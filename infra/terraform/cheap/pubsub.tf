resource "google_pubsub_topic" "signals" {
  name       = "loop.signals"
  depends_on = [google_project_service.cheap]
}

resource "google_pubsub_topic" "verification" {
  name       = "loop.verification"
  depends_on = [google_project_service.cheap]
}
