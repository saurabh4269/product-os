# Few-dollar ceiling. Requires billing account; skipped when unset.
resource "google_billing_budget" "loop" {
  count           = var.billing_account == "" ? 0 : 1
  billing_account = var.billing_account
  display_name    = "loop-cheap-ceiling"
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "8"
    }
  }
  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
}
