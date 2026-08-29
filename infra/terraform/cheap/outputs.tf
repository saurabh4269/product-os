output "datasets" {
  value = [
    google_bigquery_dataset.raw.dataset_id,
    google_bigquery_dataset.metrics.dataset_id,
    google_bigquery_dataset.ops.dataset_id,
  ]
}

output "topics" {
  value = [
    google_pubsub_topic.signals.name,
    google_pubsub_topic.verification.name,
  ]
}

output "runtime_sa" {
  value = local.runtime_member
}

output "model_armor_fail_open" {
  value = local.fail_open
}
