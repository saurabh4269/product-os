resource "google_bigquery_dataset" "raw" {
  dataset_id                  = "loop_raw"
  location                    = var.region
  delete_contents_on_destroy  = false
  depends_on                  = [google_project_service.cheap]
}

resource "google_bigquery_dataset" "metrics" {
  dataset_id                 = "loop_metrics"
  location                   = var.region
  delete_contents_on_destroy = false
  depends_on                 = [google_project_service.cheap]
}

resource "google_bigquery_dataset" "ops" {
  dataset_id                 = "loop_ops"
  location                   = var.region
  delete_contents_on_destroy = false
  depends_on                 = [google_project_service.cheap]
}
