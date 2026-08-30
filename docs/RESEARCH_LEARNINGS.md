# LOOP research — learnings & blockers

Notes from PRD research (2026-08-29). Full detail lives in `docs/PRD.md`.

## Research process blockers

- **Docs lie by omission / contradiction.** Launch-stage banners are HTML-only (text extractors drop them). GA dates in blogs ≠ release notes. Model Armor integration matrix still says Gateway is Preview while release notes say GA (2026-06-24).
- **Wrong URLs / stale paths.** Several GEAP pages 404’d under guessed paths; had to rediscover from nav (e.g. skill governance). Codelabs still show `gcloud alpha` for things that are GA.
- **“Sub-second cold start” vs measurements.** Marketing claim on overview + launch note; performance page says ~4.7s / 1.4s / 0.4s. No reconciliation doc. No Agent Runtime SLA at all.
- **ADK Model Armor plugin.** Assumed sample-only; actually first-party in ADK **2.8.0** (shipped ~4 days before research). Docs site lagged; source + changelog were truth.
- **Workspace MCP.** No service-account / DWD. Unattended = stored offline refresh token (Google’s own ADK codelab). Tool counts in docs wrong (Gmail 23 tools, not 9; 58 total across 9 servers). Model Armor only covers 5/9 servers.
- **GCP project quota while setting up Cloud Agent.** Pending-delete projects still count. Couldn’t create new project; had to undelete/reuse. `sturdy-charger-cxlvd` not deletable (no IAM). Promo credits ride the billing account once linked.

## Things that invert the “obvious” default

| Trap | What you expect | What’s true |
|---|---|---|
| Gateway `failOpen` | Copy Google’s examples | Examples set `true` → **fail-open**. Default is `false`. Pin `false` + CI. |
| Inline Model Armor | `INSPECT_AND_BLOCK` = fail-closed | Unavailable → **always fails open**. No knob. |
| ADK Model Armor plugin | Screens everything | **Does not screen tool output** — our main injection path. Need `after_tool_callback`. |
| `roles/modelarmor.admin` | Superset of editor | **Lacks `callouts.invoke`**. Gateway needs `calloutUser`. Role is `floorSettingsViewer` (plural). |
| Newest Flash model | Safer / better default | Short lifecycle (45-day notice). Prefer `gemini-3.5-flash`. Sampling params on 3.6 / 3.5-lite **silently ignored**. |
| Outbound phone for ADK+Live | GTP / CX / CCAI | **None do outbound for agents.** Google’s own answer: Twilio `calls.create`. |
| India telephony | Gap to configure | Hard ✘ even for BYOC (regulatory). Not a region toggle. |
| Live session length | “15 min” | That’s Developer API. **Agent Platform = 10 min.** Dial rate bottleneck: **10 new BidiStream connections/min**, not 1000 concurrent sessions. |
| SGP | Sole hard-limit enforcer | Preview + probabilistic LLM judge. Deterministic checks in tool code required. |
| Skill Registry | Only skills surface | Catalog can live on **GA Agent Registry**; Skill Registry mainly for semantic discovery (Preview). |

## Hard platform constraints that shaped the design

- **Region:** `us-central1` only (Code Execution + SGP + Gateway + Memory Bank intersection).
- **Immutable at create:** `identity_type=AGENT_IDENTITY` + `agent_gateway_config` — wrong → full redeploy.
- **Quotas that bite early:** Query ~90/min, A2A POST ~60/min, Live dial 10/min, SDP regional 100 req/min (global higher), Memory Bank 100 writes/min.
- **Voice model:** `gemini-live-2.5-flash-native-audio` retires **2026-12-13**, no Agent Platform successor named — largest open platform risk.
- **Still undocumented after search:** Live successor; DLP latency; SGP accuracy/latency numbers; GA4 pause vs streaming continuity; some CX quotas.

## Design takeaways worth remembering

- Group agents by **permission / trust boundary**, not by function (identity is per deployment).
- Two fail-closed safety layers: gateway `failOpen=false` + ADK plugin `block_on_screening_failure=True`, plus custom tool-output screening.
- SGP = defense-in-depth only; never sole hard limit.
- Voice is architecturally optional; mock Live/Twilio for first slice.
- Verify every “everyone knows” claim against official docs — several popular numbers were wrong.

## GCP setup (Cloud Agent) — quick facts

- Project used: `mystical-timing-442601-q8` (display name LOOP Cloud Agent).
- SA: `loop-cloud-agent@…` with limited admin roles (BQ, Run, Pub/Sub, Storage, Model Armor, AI Platform user).
- Key as Cursor **Runtime Secret** `GCP_SA_KEY` (base64); env `GOOGLE_CLOUD_PROJECT`.
- Auth in `start`, not `install` (build snapshot drops exported env).
