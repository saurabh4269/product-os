# Turn Google ADK 2 into Your Product Reliability Control Plane: GA4, BigQuery, Workspace OAuth, and the Hosted Consent Pattern

| Field | Value |
|---|---|
| Format | Medium hands-on tutorial |
| Status | Draft — ready to paste into Medium |
| Live demo | https://loop-5uy6fkd7bq-uc.a.run.app |
| Repo | https://github.com/saurabh4269/product-os |

**Subtitle:** Less theory, more practice — wire a real tenant, export analytics to BigQuery, and connect Gmail/Calendar without `redirect_uri_mismatch`.

---

## Background

We built [Product OS (LOOP)](https://github.com/saurabh4269/product-os) — a generic agent control plane for product teams — on **ADK 2.8**, Cloud Run, and BigQuery. Along the way we hit familiar ADK integration walls: OAuth scopes scattered across docs, `localhost` redirect mismatches, and APIs that live on **`v1alpha`** while the rest of the world uses `v1beta`.

This is the guide we wish existed when we wired **Cove** (our demo storefront) to **LOOP** (our OS).

You will:

1. Connect a tenant on the hosted console
2. Authorize **Workspace** OAuth (Gmail draft + Calendar hold)
3. Authorize **GA4 Admin** OAuth (`analytics.edit`) and link GA4 → BigQuery
4. Point agents at the warehouse with `warehouse_mode: auto`
5. Push real-time signals from Product Y while BQ backfills

**Prerequisites:** A GCP project, `gcloud` CLI, a GA4 property (or let our script create one), a Web OAuth client in Google Auth Platform.

---

## Part 1 — Architecture in one picture

```
Product Y (Cove)          Product OS (LOOP)              Google Cloud
     │                           │                            │
     │  POST /api/t/acme/signals │                            │
     ├──────────────────────────►│  Pub/Sub loop.signals      │
     │                           │                            │
     │                           │  Query BQ loop_raw / GA4   │
     │                           ├───────────────────────────►│ BigQuery
     │                           │                            │
     │                           │  Draft mail / Calendar     │
     │                           ├───────────────────────────►│ Gmail / Calendar
     │                           │                            │
     │  PR opened on approve     │  GitHub connector          │
     ◄───────────────────────────┤                            │
```

Three pieces, always:

1. **Product OS** — control plane (this repo, Cloud Run service `loop`)
2. **Product Y** — tenant app (Cove: separate repo + URL)
3. **Connectors** — honest apply / skip / denied (never fake `pr_opened: true`)

Every connector returns one of: `applied`, `skipped`, `denied`, or `reused` (idempotent replay).

---

## Part 2 — Setting up the foundation

Every project starts with the right tools.

```bash
git clone https://github.com/saurabh4269/product-os
cd product-os
./scripts/boot.sh   # warehouse seed + API :8080 + console :3000
./scripts/verify.sh # ruff, pytest, console lint/typecheck/build
```

For console against **hosted** API (CORS is open on Cloud Run):

```bash
cd apps/console
env -u LOOP_STATIC NEXT_PUBLIC_API_URL=https://loop-5uy6fkd7bq-uc.a.run.app \
  ./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3010
```

Open **Connect** in the rail — not a shop page. Product Y lives on its own origin.

---

## Part 3 — Workspace OAuth (Gmail + Calendar)

To allow agents to draft mail and hold calendar slots — without sending autonomously — we use user OAuth with a **registered production redirect**, not localhost in a notebook.

### Step 1 — Create OAuth Web client

Google Cloud Console → **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID** → **Web application**.

Configure the OAuth consent screen first (app name, support email, scopes).

Add authorized redirect URI:

```
https://loop-5uy6fkd7bq-uc.a.run.app/api/oauth/google/callback
```

Use your own Cloud Run URL if self-hosting.

Copy **Client ID** and **Client Secret**.

### Step 2 — Paste credentials on Connect

Open https://loop-5uy6fkd7bq-uc.a.run.app/connect (or local `:3000/connect`).

Paste the Web client ID and secret. Secrets live in Cloud Run env or local `.env` — never in git.

### Step 3 — Authorize once

Click **Authorize Google** on Connect. After consent:

| Capability | Behavior |
|---|---|
| `mail.draft` | Gmail draft when coordination runs |
| `calendar.hold` | Calendar event on HIGH-risk paths |
| `send_gmail` | **Denied by design** (draft ≠ send) |

Check status:

```bash
curl -s https://loop-5uy6fkd7bq-uc.a.run.app/api/oauth/google/status
# {"ready": true}
```

This follows the ADK **`adk_request_credential`** pattern — with a **registered production redirect**, not `http://localhost:8000/callback`.

---

## Part 4 — GA4 OAuth (separate flow — this is the gotcha)

Workspace OAuth does **not** include `analytics.edit`. GA4 Admin API calls will return `ACCESS_TOKEN_SCOPE_INSUFFICIENT` until you run a dedicated flow.

We added a second hosted OAuth path: `/api/oauth/ga4/start` with scope `https://www.googleapis.com/auth/analytics.edit`.

### Option A — Scripted (recommended)

```bash
./scripts/setup-ga4-auth.sh
# Opens https://loop-.../api/oauth/ga4/start in browser
# Polls /api/oauth/ga4/status until ready
# Writes ~/.config/gcloud/application_default_credentials.json from GCS ga4_adc.json
```

### Option B — Manual

Visit your LOOP deployment:

```
https://loop-5uy6fkd7bq-uc.a.run.app/api/oauth/ga4/start
```

Approve Analytics access. Then pull credentials:

```bash
gcloud storage cat gs://YOUR_PROJECT-loop-host/ga4_adc.json \
  > ~/.config/gcloud/application_default_credentials.json
```

Verify:

```bash
curl -s https://loop-5uy6fkd7bq-uc.a.run.app/api/oauth/ga4/status
# {"ready": true}
```

---

## Part 5 — Warehouse setup (GA4 → BigQuery + tenant wire)

Once GA4 OAuth is ready:

```bash
export GOOGLE_CLOUD_PROJECT=mystical-timing-442601-q8   # your project
export COVE_URL=https://cove-5uy6fkd7bq-uc.a.run.app    # your Product Y URL
./scripts/setup-gcp-warehouse.sh
```

This script:

- Downloads `ga4_adc.json` from GCS if hosted OAuth completed
- Creates GA4 property + web stream (if needed) via **`v1beta`**
- Links GA4 → BigQuery via **`v1alpha`** BigQuery Links API (`v1beta` returns 404 on `bigQueryLinks`)
- Enables **streaming export** (`events_intraday_*`) — hours, not 24h daily-only
- Sets Cove `NEXT_PUBLIC_GA_MEASUREMENT_ID` on Cloud Run
- Updates tenant `acme` with `ga4_dataset`, `warehouse_mode: auto`

### BigQuery link payload (what actually works)

```json
{
  "project": "projects/YOUR_PROJECT_ID",
  "datasetLocation": "US",
  "dailyExportEnabled": true,
  "streamingExportEnabled": true,
  "freshDailyExportEnabled": true
}
```

Use `v1alpha`:

```
POST https://analyticsadmin.googleapis.com/v1alpha/properties/PROPERTY_ID/bigQueryLinks
```

---

## Part 6 — BigQuery datasets your agents read

| Dataset | Contents |
|---|---|
| `loop_raw` | Synthetic + loaded events (CI always works) |
| `loop_metrics` | Aggregates for detect / verify |
| `analytics_<PROPERTY_ID>` | GA4 daily + intraday export |
| `loop_ads` | Google Ads transfer (optional; demo copies synthetic if no Ads OAuth) |

On **Connect**, set for tenant `acme`:

| Field | Example |
|---|---|
| BQ project | `mystical-timing-442601-q8` |
| Raw dataset | `loop_raw` |
| Metrics dataset | `loop_metrics` |
| GA4 dataset | `analytics_552119204` (yours will differ) |
| Warehouse mode | `auto` — prefer GA4/Ads when tables exist |

Agents **detect** from warehouse; Cove **push** signals arrive in real time:

```bash
curl -X POST https://loop-.../api/t/acme/signals \
  -H "Authorization: Bearer YOUR_TENANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"kind":"conversion_drop","surface":"checkout","delta_pct":-12}'
```

Until GA4 tables populate, agents use synthetic `loop_raw`. Cove push signals still work immediately.

---

## Part 7 — Google Ads → BigQuery (optional)

```bash
export GOOGLE_ADS_CUSTOMER_ID=1234567890   # no dashes
./scripts/setup-gcp-warehouse.sh
```

Complete browser OAuth when `bq mk --transfer_config` prints a URL.

Correct flags (we hit this):

```bash
bq mk --transfer_config \
  --project_id=PROJECT \
  --location=us-central1 \
  --data_source=google_ads \
  --target_dataset=loop_ads \
  -p='{"customer_id":"CUSTOMER_ID"}'
```

Use `--location`, not `--transfer_location`. Create `loop_ads` in the same region as `loop_raw` (`us-central1`, not cross-region `US`).

Without Ads credentials, the script seeds `loop_ads` from synthetic data — honest skip, not fake success.

---

## Part 8 — ADK 2 agents (local / worker, not hosted cold path)

Hosted Cloud Run runs the **deterministic engine** — no Gemini on cold start. The ADK fleet runs locally or on optional `loop-adk` worker:

```bash
cd services/loop
pip install -e '.[adk]'
python -m pytest tests/ -q -k workflow
```

### Import paths (verified ADK 2.8+)

```python
from google.adk import Workflow
from google.adk.workflow import START, JoinNode

# NOT: from google.adk.workflows import Workflow  # ModuleNotFoundError
```

### Workflow-as-Tool requires input_schema

Wrapping a `Workflow` on `LlmAgent.tools` fails at runtime unless the workflow has a Pydantic `input_schema`:

```python
from pydantic import BaseModel

class InvestigationIn(BaseModel):
    signal_id: str

investigation_wf = Workflow(
    name="investigation_fanout",
    input_schema=InvestigationIn,
    # ...
)
```

### Tool-output armor (do not skip)

Stock `ModelArmorPlugin` screens prompts and model responses only. Untrusted GitHub issues and ingested mail arrive as **tool output**. We ship `ToolOutputArmorPlugin` on `after_tool_callback` — treat this as mandatory for production.

List workflow catalog:

```bash
curl -s https://loop-5uy6fkd7bq-uc.a.run.app/api/workflows
```

---

## Part 9 — End-to-end validation checklist

1. **Connect** shows tenant Cove linked (repo, deploy URL, datasets)
2. `curl .../api/oauth/google/status` → workspace ready
3. `curl .../api/oauth/ga4/status` → GA4 ready
4. `bq ls --project_id=PROJECT analytics_*` → GA4 export tables
5. Campus → open Safari 3DS room → evidence + approval
6. Approvals → Approve → timeline shows GitHub PR URL on tenant repo
7. Cove browse + checkout → GA4 Realtime; BQ `events_intraday_*` within hours

### Latency expectations

| Source | Typical latency |
|---|---|
| Cove push signals | Real time |
| GA4 Realtime (console) | Minutes |
| BQ `events_intraday_*` (streaming export) | ~1–3 hours |
| BQ daily `events_*` tables | ~24h export window |

Enable `streamingExportEnabled: true` on the BigQuery link for faster agent evidence from real traffic.

---

## Part 10 — What we intentionally do *not* automate

| Typical tutorial pattern | Our choice | Why |
|---|---|---|
| Service account + domain-wide Gmail send | User OAuth, send denied | PRD safety; no autonomous mail |
| Single OAuth for all Google APIs | Workspace + GA4 separate flows | Scope isolation |
| ADK 1.x `ParallelAgent` trees | ADK 2 `Workflow` + `JoinNode` | Deprecated in 2.x |
| `localhost` redirect in notebooks | Hosted callback on Cloud Run | Fixes `redirect_uri_mismatch` |
| Autonomous PR merge | Open PR only | Human merge; tenant CI deploys Y |

For enterprise buyers who need unattended send: document domain-wide delegation as an **explicit opt-in**, not the default path. See [`docs/PRD.md`](https://github.com/saurabh4269/product-os/blob/main/docs/PRD.md) Section 14.

---

## Part 11 — Deploy your own LOOP

```bash
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

After deploy: hard-refresh, confirm `/city/campus.webp` and `/api/office` return 200.

Optional ADK worker (full Gemini fleet):

```bash
./scripts/package-adk-worker.sh
./scripts/deploy-adk-worker.sh
./scripts/deploy-gcp.sh   # picks up LOOP_ADK_WORKER_URL
```

---

## Links

| Resource | URL |
|---|---|
| LOOP (hosted) | https://loop-5uy6fkd7bq-uc.a.run.app |
| Cove (Product Y) | https://cove-5uy6fkd7bq-uc.a.run.app |
| GitHub | https://github.com/saurabh4269/product-os |
| Upstream learnings handoff | [`docs/GOOGLE_OPEN_SOURCE_LEARNINGS.md`](../GOOGLE_OPEN_SOURCE_LEARNINGS.md) |

---

## Conclusion

ADK + Gmail + Calendar + Cloud Run is a proven stack for agent automation. This tutorial applies it to **product reliability**: BigQuery warehouse, GA4 export, governed agents, and OAuth that works in production redirects.

Copy the hosted consent pattern, split your OAuth scopes, enable GA4 streaming export, and wire `warehouse_mode: auto`. Your agents get evidence from the warehouse; your users still approve anything that touches prod.

The future of product ops is not another dashboard — it is a governed agent loop you can see, approve, and verify.

---

**Tags:** `#GoogleADK` `#ADK2` `#BigQuery` `#GA4` `#OAuth` `#CloudRun` `#ProductEngineering` `#Tutorial` `#AgentDevelopmentKit`

**Related:** [Architecture story draft](ARCHITECTURE_POST.md) · [Adoption notes](ADOPTION_NOTES.md)
