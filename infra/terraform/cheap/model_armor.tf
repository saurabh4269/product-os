# Input/output templates (M-1) plus the fail-closed pin asserted by CI (M-5a).
# The live AuthzExtension lives in infra/terraform/gated (plan-only).

locals {
  # M-5a — never copy Google examples that set fail-open.
  model_armor_gateway_fail_open = false
  fail_open = false
}

resource "google_model_armor_template" "prompt" {
  location    = var.region
  template_id = "loop-prompt"
  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "MEDIUM_AND_ABOVE"
    }
    malicious_uri_filter_settings {
      filter_enforcement = "ENABLED"
    }
  }
  depends_on = [google_project_service.cheap]
}

resource "google_model_armor_template" "response" {
  location    = var.region
  template_id = "loop-response"
  filter_config {
    pi_and_jailbreak_filter_settings {
      filter_enforcement = "ENABLED"
      confidence_level   = "MEDIUM_AND_ABOVE"
    }
  }
  depends_on = [google_project_service.cheap]
}
