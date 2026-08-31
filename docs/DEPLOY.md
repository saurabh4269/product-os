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

## Hosted now

Live: https://loop-5uy6fkd7bq-uc.a.run.app (Cloud Run service `loop` — Product OS only. Do not deploy a tenant shop into this service.)

This path does **not** need Cloud Build. It uploads `dist/loop-host.tgz` to
`gs://mystical-timing-442601-q8-loop-host` and runs `python:3.12-slim` which
downloads the bundle and serves FastAPI + the static console.

```bash
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

### Auto-deploy on push to `main`

CI runs `./scripts/verify-deploy.sh` (no Remotion render). When it passes on `main`, the
[`deploy-gcp`](../.github/workflows/deploy-gcp.yml) workflow packages and runs
`deploy-gcp.sh` — you do not need to deploy from your laptop.

One-time setup: add repo secret **`GCP_SA_KEY`** (JSON for a service account with
`roles/run.admin`, `roles/storage.admin`, and permission to describe/update Cloud Run
`loop`). Use the same account as local deploy (`loop-cloud-agent@…` or your owner SA).
Then push to `main`; watch **Actions → deploy-gcp**.

Manual deploy anytime: **Actions → deploy-gcp → Run workflow**.

SQLite is ephemeral on Cloud Run. Cold start re-runs the seeded Safari loop.

## Cloud Run (image build — optional, needs extra IAM)

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
