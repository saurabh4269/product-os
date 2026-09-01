resource "google_project_service" "cheap" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigquerystorage.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "modelarmor.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "serviceusage.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudtasks.googleapis.com",
    "aiplatform.googleapis.com",
    "firestore.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}
