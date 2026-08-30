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
- `POST /api/scenarios/:slug/run`

## Memory / traces

- `GET /api/memory` · `GET /api/traces` · `GET /api/signals`

## Forbidden on this origin

`/shop`, `/company`, and any tenant storefront — **404**. Product Y is a separate repo + Cloud Run service.
