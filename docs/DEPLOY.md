# LOOP — GCP deploy (cheap path)

Project `mystical-timing-442601-q8`, region `us-central1`. Never echo, log, or commit `GCP_SA_KEY`.

## Already applied (this Cloud Agent SA)

| Resource | Name |
|---|---|
| Datasets | `loop_raw`, `loop_metrics`, `loop_ops` |
| Topics | `loop.signals`, `loop.verification` |
| Model Armor templates | `loop-prompt`, `loop-response` (`MEDIUM_AND_ABOVE`, injection filter) |
| APIs | BigQuery, Pub/Sub, Cloud Run, Model Armor, Logging, Monitoring |

Re-apply (idempotent):

```bash
./scripts/gcp-activate.sh
cd infra/terraform/cheap && terraform init && terraform apply
```

Load the seeded warehouse into BigQuery (pennies):

```bash
./scripts/load-bq.sh
```

## Cloud Run (API)

The Cloud Agent SA can **enable** some APIs and create BQ/Pub/Sub/Armor, but it cannot create a new runtime SA, set project IAM, or push images. Deploy after you grant the bindings below.

```bash
PROJECT=mystical-timing-442601-q8
SA=loop-cloud-agent@${PROJECT}.iam.gserviceaccount.com

gcloud services enable \
  run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  --project=$PROJECT

gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/run.admin
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/artifactregistry.admin
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/cloudbuild.builds.editor
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/iam.serviceAccountUser
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$SA --role=roles/storage.admin

# Optional: runtime SA + project IAM via Terraform
export TF_VAR_create_runtime_sa=true
export TF_VAR_grant_project_iam=true
# Optional $8 budget alert
export TF_VAR_billing_account=YOUR_BILLING_ACCOUNT_ID

./scripts/deploy-gcp.sh
```

The API image is built from the repo root (`services/loop/Dockerfile`). On boot it generates the warehouse if `var/warehouse/meta.json` is missing.

Point the console at the Cloud Run URL:

```bash
export NEXT_PUBLIC_API_URL=https://loop-api-….run.app
cd apps/console && npm run dev
```

CORS allow-list is `LOOP_CONSOLE_ORIGIN` plus localhost. For a public demo, set `LOOP_CONSOLE_ORIGIN=*` on the service.

## Do not apply (plan only)

```bash
cd infra/terraform/gated
terraform init
terraform plan -out=gated.tfplan
# Confirm fail_open = false (M-5a), then apply only if you accept Preview cost.
```

Agent Gateway, SGP, Agent Runtime `reasoningEngines`, and telephony stay plan-only.
