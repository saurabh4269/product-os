# Gated infrastructure — plan only

Agent Gateway, Semantic Governance, and telephony are **not applied** by LOOP's cheap path.

```bash
cd infra/terraform/gated
terraform init
terraform plan -out=gated.tfplan
# Review. Then, when you have entitlements:
# terraform apply gated.tfplan
```

Exact owner commands after plan review:

```bash
export PROJECT=mystical-timing-442601-q8
export REGION=us-central1

# 1. Confirm fail_open is false (M-5a)
terraform show -json gated.tfplan | python3 -c \
  'import json,sys; d=json.load(sys.stdin);
print("inspect AuthzExtension fail_open in planned values")'

# 2. Apply only after you accept Preview SGP + Gateway cost
terraform apply gated.tfplan

# 3. Deploy reasoning engines WITH identity + gateway at creation (A-1, immutable)
# gcloud ai reasoning-engines create ... --identity-type=AGENT_IDENTITY \
#   --agent-gateway-config=...
```

Do **not** grant `roles/modelarmor.admin` to the gateway SA (lacks `callouts.invoke`). Use `roles/modelarmor.calloutUser`.
