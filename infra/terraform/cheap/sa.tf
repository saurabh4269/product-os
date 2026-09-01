variable "create_runtime_sa" {
  type    = bool
  default = false
}

variable "grant_project_iam" {
  type    = bool
  default = true
}

resource "google_service_account" "runtime" {
  count        = var.create_runtime_sa ? 1 : 0
  account_id   = "loop-runtime"
  display_name = "LOOP cheap runtime"
  depends_on   = [google_project_service.cheap]
}

locals {
  runtime_member = var.create_runtime_sa ? "serviceAccount:${google_service_account.runtime[0].email}" : "serviceAccount:loop-cloud-agent@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "runtime_bq" {
  count   = var.grant_project_iam ? 1 : 0
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = local.runtime_member
}

resource "google_project_iam_member" "runtime_armor_user" {
  count   = var.grant_project_iam ? 1 : 0
  project = var.project_id
  role    = "roles/modelarmor.user"
  member  = local.runtime_member
}

# Trap 1: admin is NOT a superset and lacks callouts.invoke. Gateway path uses calloutUser.
resource "google_project_iam_member" "runtime_armor_callout" {
  count   = var.grant_project_iam ? 1 : 0
  project = var.project_id
  role    = "roles/modelarmor.calloutUser"
  member  = local.runtime_member
}

resource "google_project_iam_member" "runtime_firestore" {
  count   = var.grant_project_iam ? 1 : 0
  project = var.project_id
  role    = "roles/datastore.user"
  member  = local.runtime_member
}

resource "google_project_iam_member" "runtime_tasks_enqueuer" {
  count   = var.grant_project_iam ? 1 : 0
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = local.runtime_member
}
