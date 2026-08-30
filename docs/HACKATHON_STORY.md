# Hackathon story — what we took from winners, and what ADK 2.0 changes

## What Product OS is

A **generic** control plane: observe → rooms → agents → gate → measure → remember.
Safari / 3DS is a **fixture**, not the product. Live demo: campus + multi-room chat.
Product Y (Northstar) is a **separate** repo + Cloud Run service — never `/shop` on this origin.

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
| Deterministic Type A/B graph | `loop/agents/graphs.py` |
| docker-compose | root `docker-compose.yml` (boot.sh remains primary) |

### SalesShortcut (ADK hackathon winners, **pre-ADK-2**)

Shipped with Sequential / Parallel / Loop agents and multi-service Cloud Run.

| Pattern | Where it landed |
|---------|-----------------|
| `POST /agent_callback` → UI fan-out | `/api/agent_callback` → Hub (+ optional `world.post`) |
| Funnel status chips | Room header from investigation state |
| Skip-if-done HITL (`before_tool_callback`) | Approve reuse + `loop/agents/callbacks.py` |
| Review / Critique | ADK 2 `proposal_critique` Workflow |
| Parallel evidence fan-out | ADK 2 `investigation_fanout` + JoinNode; engine still joins ≥3 independence groups |
| after_agent push | `after_agent_push` helper |

We did **not** copy: Gmail send + domain-wide SA, PSTN / ElevenLabs, five separate agent Cloud Run services, or a shop on the OS origin.

## ADK 2.0 (winners could not use this)

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
