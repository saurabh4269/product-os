# PLAN-ONLY. Do not apply until Agent Gateway + SGP entitlements exist.
# Copy-paste from Google examples sets fail-open — that is forbidden (M-5a).

resource "google_network_services_lb_traffic_extension" "loop_armor" {
  name     = "loop-model-armor"
  location = var.region
  extension_chains {
    name = "model-armor"
    match_condition {
      cel_expression = "true"
    }
    extensions {
      name      = "model-armor-authz"
      authority = "modelarmor.googleapis.com"
      service   = "projects/${var.project_id}/locations/${var.region}/authzExtensions/loop-model-armor"
      timeout   = "3s"
    }
  }
  load_balancing_scheme = "INTERNAL_MANAGED"
  forwarding_rules      = []
}

# Service Extensions AuthzExtension — CONTENT_AUTHZ for Model Armor.
# fail_open MUST be false. Timeout raised above the documented 1s (M-5a).
resource "google_network_services_authz_extension" "loop_model_armor" {
  name     = "loop-model-armor"
  location = var.region
  load_balancing_scheme = "INTERNAL_MANAGED"
  authority             = "modelarmor.googleapis.com"
  service               = "projects/${var.project_id}/locations/${var.region}/modelArmor"
  fail_open             = false
  timeout               = "3s"
  metadata = {
    policyProfile = "CONTENT_AUTHZ"
  }
}

# SGP is Preview and probabilistic (L-4, Q-4). Plan only.
# gcloud beta network-security security-profile-groups create ...
# Then attach constraints to MEDIUM/HIGH tools only.

# Telephony: no Google product originates outbound ADK+Live calls (K-6).
# Default: Twilio Media Streams. LiveKit SIP alternative.
# This stack mocks the Live API; do not apply carrier resources here.
