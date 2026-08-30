# Product OS API contract (frozen for console + connectors)

Base: same origin on Cloud Run, or `http://127.0.0.1:8080` locally.
WebSocket: `ws(s)://<host>/ws` and `/ws/rooms/:id`

## Rooms (campus chat, not a dashboard)

- `GET    /api/rooms` → `{ rooms }`
- `GET    /api/rooms/:id` → RoomDetail (`messages`, `bundle`, `presence`, `funnel`)
- `POST   /api/rooms/:id/messages` body `{ text }`
- `WS     /ws/rooms/:id` events below

Room.kind: `incident` | `opportunity` | `review` | …

## Live events (WS)

```
{ type: "message", message }
{ type: "agent_presence", agentId, status: "idle"|"thinking"|"tool"|"speaking", pixel }
{ type: "artifact", artifact }
{ type: "approval_required" | "approval_resolved", approval }
{ type: "a2a", envelope | from, to, kind, summary }
{ type: "trace", traceId, step }
{ type: "signal", signal }
```

## Tenant wire (Product Y lives elsewhere)

- `GET/POST /api/tenants`
- `GET  /api/t/{tenant}/flags` Bearer
- `POST /api/t/{tenant}/signals` Bearer
- `POST /api/t/{tenant}/voice` Bearer

## Approvals (Risk / HITL)

- `GET  /api/approvals`
- `POST /api/approvals/:id` `{ decision: approve|deny, approver, rationale }`
  - Skip-if-done: already `executed` → `{ reused: true }` (SalesShortcut before_tool pattern)
  - HIGH + tenant repo → real GitHub PR; OS never merges / never deploys Y

## Workspace OAuth (enterprise pattern)

- `GET  /api/oauth/google` status + authorize URL
- `POST /api/oauth/google/client` save Web client id/secret
- `GET  /api/oauth/google/start` → Google consent (`access_type=offline`)
- `GET  /api/oauth/google/callback`
- Mail: draft only when connected; **send stays denied**
- Calendar: hold when connected

## Agents / live push

- `GET  /api/agents` · `GET /api/agents/:id`
- `POST /api/agent_callback` SalesShortcut-style push → Hub fan-out
- `GET  /api/workflows` ADK 2 Workflow catalog (soft-fail without google-adk)
- `GET  /api/office`

## Scenarios (eval fixtures, not product shape)

- `GET  /api/scenarios`
- `POST /api/scenarios/:slug/run` — fixtures + thin recipes (e.g. `checkout_abandon`) on research infra

## Research (generic event → agents → voice evidence)

- `POST /api/research` body ResearchEvent → probes, memory match, Customer Context Brief, call (Twilio / Google inbound callback / simulated), StructuredCallEvidence
- `GET  /api/telephony` — Google inbound vs Twilio outbound vs simulated
- `POST /api/calls` — manual outbound when Twilio is configured

## Improve (Type A / Type B product loop)

- `POST /api/improve` body ProductSignalEvent → detect → ≥3 evidence → hypothesis → **fix** (Type A) or **experiment design + measure** (Type B) → lesson
- Recipes (e.g. `shipping_ux` fixture) only supply the event payload; pipeline is shared

## Coordinate (HITL in company workflow)

- `POST /api/coordinate` → resolve owners (CODEOWNERS/surface) → Calendar suggest/create → Gmail **draft** notify → await human. **Never auto-merge.**
- Risk paths: LOW notify+wait · MEDIUM optional hold · HIGH schedule + Meet when OAuth
- `GET /api/calendar` · `POST /api/calendar/suggest` — list/freebusy/suggest/create (simulated without Workspace OAuth)
- Bridge: pass `action_id` to coordinate from a pending ProposedAction

## Investigate (broad signals → ADK-shaped fan-out → evidence → briefs)

- `GET  /api/signals/catalog` — funnel / technical / business / customer watch list
- `POST /api/investigate` — parallel analytics·logs·deploy·db·customer·code → Evidence pack → hypothesis → voice_context + code_brief + risk
- `POST /api/product-intel` — N feature mentions → one Product proposal (not N issues)

## Signals
- `GET  /api/signals`
- `POST /api/signals` body SignalIn → `{ signalId, roomId, trace_id }` — opens/joins a room and runs the **live fleet graph** (presence, messages, artifacts, gateway)

## Status (SalesShortcut dashboard energy)
- `GET /api/status` → open rooms, pending approvals, live presence, funnel counters, Workspace connected

## Memory
- `GET  /api/memory?q=&type=`
- `POST /api/memory` body `{ type, title, body, tags, room_id }` — remember a lesson (not warehouse facts)

## Observability
- `GET /api/traces`
- `GET /api/traces/:id` — investigation bundle or live Hub trace steps

## Gateway
Identity allow/deny before tools (`loop/gateway.py`). Forbidden: `customer_records.dump` / PII export. High-risk tools require approval.

## Live graph patterns (from winners + ADK 2)
- Parallel investigator fan-out → merge
- Review/critique with `output_key` state
- `funnel_stage` + `agent_callback` WS events
- skip-if-done tool replay

## Forbidden on this origin

`/shop`, `/company`, and any tenant storefront — **404**. Product Y is a separate repo + Cloud Run service.
