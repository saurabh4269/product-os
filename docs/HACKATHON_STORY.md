# Hackathon story — adopted patterns and ADK 2.0 changes

## What Product OS is

A **generic** control plane: observe → rooms → agents → gate → measure → remember.
Safari / 3DS is a **fixture**, not the product. Live demo: campus + multi-room chat.
Product Y (Cove) is a **separate** repo + Cloud Run service — never `/shop` on this origin.

## Inspiration (integrated)

### product-os-v2

| Idea | Where it landed |
|------|-----------------|
| WebSocket live rooms + presence (`idle\|thinking\|tool\|speaking`) | `loop/live.py` Hub · `/ws/rooms/:id` |
| Typed A2A envelopes on the bus | `loop/a2a_protocol.py` · engine `a2a()` |
| Work / Transcript + flipable artifacts | Room `FunnelChips` + `ArtifactCard` |
| Handoff rail with live status | `FunnelChips` presence overlay |
| Frozen API contract | `packages/contracts/api.md` |
| Scenario run endpoint | `POST /api/scenarios/{slug}/run` (+ presence sweep) |
| Deterministic Type A/B graph | `loop/agents/graphs.py` `run_live_graph` (speak / artifact / gateway / A2A) |
| `POST /api/signals` runs the fleet | Creates/joins room + live graph |
| `POST /api/memory` | Remember lessons (not warehouse facts) |
| Gateway authorize → invoke | `loop/gateway.py` + deny artifacts on the bus |
| Scenario chips on campus | `ScenarioChips` → `POST /api/scenarios/{slug}/run` |
| Richer flip artifacts | Kind tones + nested fields + expand |

### Common ADK 1.x multi-agent patterns

Typical pre–ADK-2 stacks used Sequential / Parallel / Loop agents and multiple Cloud Run services.

| Pattern | Where it landed |
|---------|-----------------|
| `POST /agent_callback` → UI fan-out | `/api/agent_callback` → Hub (+ optional `world.post`) |
| Funnel status chips + stage bus | Room `FunnelChips` + `funnel_stage` WS events |
| Dashboard counters | `GET /api/status` + campus `StatusStrip` |
| Skip-if-done HITL (`before_tool_callback`) | Approve reuse + `tool(..., output_key=)` + `callbacks.py` |
| Review / Critique + `output_key` | FEATURE path: `product_agent` draft → `feedback_agent` critique loop |
| Parallel fan-out / merger | Investigators run as a fan-out block; evidence merges `final_merged_evidence` |
| after_agent push | Each agent completion publishes `agent_callback` on the bus |
| `config.template` | Root env template (secrets never committed) |

We did **not** copy: domain-wide Gmail send SA, ElevenLabs (no subscription — Twilio trial + Gemini instead), five separate agent Cloud Run services, or a shop on the OS origin.

### Infra: research events → agents → voice evidence

Generic pipeline in `loop/customer_research.py` (not one hardcoded loop):

1. **ResearchEvent** (kind, user, dimensions, memory conditions)  
2. Pluggable **probes** (GA4 / Ads / device / logs / support…) → claims  
3. Memory match on `applicable_conditions`  
4. **Customer Context Brief** + call plan  
5. Voice: Google GTP **inbound/callback** (no Google outbound), optional Twilio dial-out, else **simulated** dialogue  
6. **StructuredCallEvidence** JSON for the rest of the fleet  

`POST /api/research` accepts any event. Recipes are thin: e.g. checkout abandon is `abandon_research.example_abandon_event` + campus chip `POST /api/scenarios/checkout_abandon/run`.

### Infra: Type A / Type B product improvement

Generic pipeline in `loop/product_improvement.py`:

| | Type A (negative) | Type B (opportunity) |
|---|---|---|
| Signal | conversion↓ crashes↑ latency↑ … | reopen loops, workarounds, requests, abandon-at-step |
| Agent job | Find and **fix** | Find and **improve** |
| Path | hypothesis → PR / flag rollback → measure → learn | hypothesis → product proposal → experiment design → 5% flag → control/treatment → decision → learn |

`POST /api/improve` accepts any `ProductSignalEvent`. Shipping UX (`shipping_ux`) is only an example recipe on that infra — Detect → hypothesize → build → experiment → measure → learn.

### Infra: developer coordination (HITL in real workflow)

Generic pipeline in `loop/coordination.py` + Calendar tools in `connectors/calendar.py`:

```
need human
  → resolve owners (CODEOWNERS / surface map)
  → risk policy (LOW notify+wait · HIGH schedule+Meet)
  → Calendar free/busy → suggest → create
  → Gmail draft / Chat skip / room artifact
  → await human  (never auto-merge)
```

`POST /api/coordinate` accepts any `CoordinationRequest`. Low-risk PR vs high-risk payment PR are **recipes** only. Gmail **send** stays Gateway-denied.

### Infra: investigation (broad signals → fan-out → evidence → briefs)

Generic pipeline in `loop/investigation.py` + ADK 2 `investigation_fanout` (6-way JoinNode):

```
Signal catalog (funnel · technical · business · customer)
       ↓
Parallel: Analytics · Logs · Deploy · DB · Customer · Code
       ↓
Evidence Agent (correlation + confidence + checklist)
       ↓
Hypothesis (≥3 independence groups)
       ↓
Voice diagnostic context  |  Code issue brief  |  Risk policy
```

`POST /api/investigate` / `GET /api/signals/catalog` / `POST /api/product-intel` (N requests → one proposal). Segmented conversion / Apple Pay fixtures are recipes only.

### Phone (outbound path, free/GCP)

Google Telephony Platform / CX Phone Gateway = **inbound only** (PRD K-6). We keep optional **Twilio + Gemini** for outbound, default **simulate** so evidence still ships without a carrier.

| Piece | Where |
|-------|--------|
| `POST /api/research` | Generic event → brief → call → evidence |
| `POST /api/calls` | Manual outbound from a room |
| `/api/twilio/voice\|gather\|status` | TwiML + transcript finalize |
| Classifier | `loop/classify.py` on voice ingest + call hangup |
| Connect desk | Twilio / Gemini / Google inbound status |
| Cove `/feedback` | Optional callback phone |

Optional Cloud Run `loop` env: `TWILIO_*`, `GOOGLE_API_KEY`, `LOOP_GTP_PHONE_NUMBER`, `LOOP_PUBLIC_URL`.

## ADK 2.0 (what changed)

| ADK 1.x | ADK 2.0 |
|---------|---------|
| SequentialAgent / ParallelAgent / LoopAgent | **Workflow** graphs; those agents are deprecated |
| Nested sub-agent pipelines | Agents are **nodes**; Workflow-as-Tool (≥2.4) on `LlmAgent` |
| Custom pause hacks | **RequestInput** pauses; resume with human payload |
| Fan-out join by hand | **JoinNode** barrier |
| Ad-hoc session | **App** + resumability |

Hosted Cloud Run still runs the **deterministic engine** (cold start without Gemini). Workflows are catalogued at `GET /api/workflows`. Workflow-as-Tool (≥2.4) needs an explicit Pydantic `input_schema` on the node — we do not hang raw Workflows on `LlmAgent.tools` until those schemas exist (App build stays green).

## Google Enterprise / Workspace (codelab pattern)

No service account for Gmail/Calendar. One browser consent with `access_type=offline`, store refresh token, refresh in memory.

- Connect → paste Web client → Authorize
- `mail.draft` / `calendar.hold` when connected
- `send_gmail` stays **denied**
- Agent Identity / GEAP stay plan-only

## Safety (unchanged)

`fail_open = false`. Exfil DENY via Gateway identity. No autonomous merge/deploy.
