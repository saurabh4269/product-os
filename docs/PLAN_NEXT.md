# PLAN NEXT — make Product OS a product Company X can run

## Active 2026-09-03 (owner unpaused)

Do not merge Cove.

Done / live:

1. ~~Persist GCS → package → deploy #30–#31~~ — `loop-00127-7dc`. Hang survived. Persist POST 200.
2. ~~Confirm hang demo UI~~ — browser verified; GitHub PR DONE; leftover HIGH gate hidden (#32).
3. ~~Workspace OAuth~~ — connected on Connect (`saurabhgupta0342@gmail.com`).
4. **Remotion hang render** (optional local) — `apps/demo/out/hang.json` exported; copy to `public/loop.json` for render only; restore generic fixture.

Never merge Cove PRs (#1–#4, #7) or LOOP leftovers (#11–#17). Do not approve `act_4754e1ae24f5`.

---

| Field | Value |
|---|---|
| Status | Phases A–F shipped. Start here only for later work (Workspace OAuth, Live, Gateway). |
| Date | 2026-08-30 (paused list above: 2026-09-03) |
| Spec | [`PRD.md`](PRD.md) remains binding (safety, risk tiers, no autonomous merge/deploy) |
| Architecture | [`PLAN.md`](PLAN.md) is what the fixture engine already implements |
| Tenant split | [`TENANT.md`](TENANT.md) — Product Y is Northstar, never hosted on Cloud Run `loop` |

This is the plan for everything that is **specified but not wired**. The campus and the fixture loop stay. We stop pretending `pr_opened: True` is a pull request.

---

## 0. Honest now vs Company X

If Company X arrived today with Product Y, we can give them the **OS UI** and a real wire: token-gated flags, signal/voice ingest into rooms, and a GitHub PR on approve (no merge, no tenant deploy).

We still cannot:
- draft or send their mail (Workspace OAuth)
- put a meeting on their calendar
- dial outbound on **Google** telephony (GTP/CX = inbound only; optional Twilio trial for PSTN)

We can run **generic research events** (`POST /api/research`): probes → brief → simulated or Twilio call → structured evidence. Checkout abandon is one recipe on that infra, not the architecture.

We can run the **Type A / Type B product loop** (`POST /api/improve`): detect → evidence → hypothesis → fix **or** experiment → measure → learn. Shipping UX / conversion-drop examples are recipes only.

We can run **developer coordination** (`POST /api/coordinate`): owners → Calendar → schedule/Meet → Gmail draft → await human. Never merges. Low-risk vs high-risk payment recipes only supply the request payload.

We can run **investigation** (`POST /api/investigate`): catalog signals → 6-way fan-out → evidence pack → hypothesis → voice/code briefs → risk. Product intel clusters N feature requests into one proposal (`POST /api/product-intel`).

Demo tenant: **Cove** at `github.com/saurabh4269/cove`, Cloud Run `cove`.

---

## 1. Non-negotiables (do not “complete” the spec by violating it)

| Rule | Why |
|---|---|
| OS does not host Product Y | No `/shop`, `/company`, `public/shop`. Demo shop = **other repo + other deploy**. |
| OS does not merge PRs | PRD C-4 / N1. Human merge. |
| OS does not prod-deploy Y | Registry `prod.deploy` deny. |
| OS does not send mail until Workspace OAuth exists | Draft is allowed when we have a client. `send_gmail` stays denied unless a later, explicit product decision + OAuth + approval. |
| No PSTN at launch | PRD N7 / no Google outbound PSTN for ADK. Call path = request + text fallback + optional Live when entitled. |
| `fail_open = false` | Safety. |
| Idempotent side effects | PRD A-7. Key = `(investigation_id, node_id, semantic)`. |
| Secrets never in git or chat | Env / Cloud Run secret **names** only. |
| Cheap GCP only | BQ, Pub/Sub, Cloud Run, Model Armor. Gateway / SGP stay plan-only until entitled. |

---

## 2. Target shape (Company X, Product Y)

Three pieces, always:

```
Product Y  ──signals / voice / flag read──►  Product OS (loop)
     ▲                                           │
     │  deploy (their CI)                        │ approve
     │                                           ▼
     └──────── their git ◄── PR (no merge) ── Code connector
```

1. **Product OS** — this repo, service `loop`.
2. **Product Y** — their repo and URL. First demo tenant is the same contract.
3. **Connectors** — real HTTP/API when credentials exist; **honest skip** (recorded, not a fake success) when they do not.

Every connector returns one of:

- `applied` — external system changed
- `skipped` — no credential / not entitled; reason stored on the timeline
- `denied` — Gateway identity said no
- `reused` — idempotent replay

Never set `pr_opened: true` unless a GitHub PR URL exists.

---

## 3. Work we start **without** waiting

These land in `product-os` now. They work against fixtures and against a tenant record even if the tenant repo is still empty.

| Phase | Build | Done when |
|---|---|---|
| **A — Tenant** | `tenants` table + API. One org: name, product, git repo, deploy URL, token hash, connector status. Console **Connect** page (not a shop). | `GET/POST /api/tenants`, `GET /api/tenants/{id}`. Seed a placeholder tenant `acme` that is clearly “not connected.” |
| **B — Flags Y can read** | `GET /api/t/{tenant}/flags` with `Authorization: Bearer`. Per-tenant flags in SQLite (later: their store). | After approve, a curl with the tenant token sees `pay_sdk_4_3=off`. Fixture JS in-repo still does not pretend to be Y. |
| **C — Signal ingest** | `POST /api/t/{tenant}/signals` (events) and `POST /api/t/{tenant}/voice`. Normalize into existing `Signal` / Customer Voice → rooms. | A posted conversion drop opens or joins a room the same way warehouse detect does. |
| **D — Connectors** | `loop/connectors/`: `github.py`, `mail.py`, `calendar.py`, `voice.py`, `warehouse.py`. Each: apply or skip. Wire `execute_approved` through them. | Approve HIGH → flag **and** `github.open_pr` if `LOOP_GITHUB_TOKEN` + tenant repo set; else timeline `skipped: no github token`. Mail: create **draft record** + optional Gmail API when OAuth present. Calendar: same. Voice: ingest + place_call stays text-fallback unless Live entitled. |
| **E — Warehouse path** | If BQ configured, `Warehouse` can read `loop_raw` for the tenant; else keep files. Pub/Sub: publish `loop.signals` on ingest (best-effort). | File path still green in CI. BQ path tested when `GOOGLE_CLOUD_PROJECT` + dataset exist. |
| **F — Console** | Rail **Connect** (not Shop). Tenant status, last ingest, last PR URL, connector skips. Approvals show “will open PR on `org/y`” vs “will only flip an OS flag.” | No campus Shop pin. Memory / Approvals landmarks unchanged. |

---

## 4. Work that **waits** on the user (do not fake)

Workspace OAuth **flow is wired** (Connect + `/api/oauth/google/*`, Gmail draft / Calendar hold). You still must create the Web OAuth client in Google Auth Platform and click Authorize once. `send_gmail` stays denied. Agent Identity / GEAP stay plan-only.

Product Y is no longer blocked: repo `saurabh4269/cove`, Cloud Run `cove`.

---

## 5. What each missing capability becomes

| Capability | Implementation | Not this |
|---|---|---|
| Watch their app | Ingest API + optional BQ/file warehouse keyed by tenant | Scraping Y’s HTML from `loop` |
| Onboard / set up teams | Tenant record + Connect UI + token | Seven GEAP runtimes on day one |
| Draft mail | `mail.draft` record; Gmail API when OAuth | Claiming send |
| Send mail | Still **denied** by default (`GMAIL_CANNOT_SEND`) | Silent send |
| Calendar | `calendar.hold` record; Calendar API when OAuth | Fake Meet links as if created |
| Call customer | Twilio free trial + Gemini (`GOOGLE_API_KEY`) Say/Gather; skip if unset | ElevenLabs paid; fake PSTN |
| Feedback | `POST /voice` → structured JSON → room | Only fixture dialogue |
| Flags | Token-gated GET; approve writes tenant flags | Shop on this origin reading `/api/company` |
| Open PR | GitHub REST/Octokit when token+repo | `pr_opened: true` with no URL |
| Push / patch | Commit on a branch in **their** repo as part of open-PR | Editing `apps/northstar-shop` as if it were Y |
| Merge | **Never** | — |
| Deploy Y | **Never** from OS | — |
| GitHub issue | `issues.create` when token | Boolean `github_issue` |
| ADK on hosted | Keep deterministic engine as source of truth; optional Gemini when key present | Requiring Gemini to approve a flag |

---

## 6. Code map (where it goes)

```
services/loop/loop/tenant.py          Tenant model, token hash, seed placeholder
services/loop/loop/connectors/        github, mail, calendar, voice, warehouse
services/loop/loop/engine.py          execute_approved → connectors (not booleans)
services/loop/loop/api.py             /api/tenants, /api/t/{id}/flags|signals|voice
apps/console/app/connect/page.tsx     Connect desk
apps/console/lib/api.ts               tenant + flag helpers
apps/console/components/shell.tsx     Connect on the rail (plug icon), not Shop
docs/TENANT.md                        Update when APIs exist
```

Tests: connector skip without token; flag GET 401 without bearer; approve + token (vcr/mock) records PR URL; ingest opens a signal; `merged` never true; no `/shop` route.

---

## 7. Build order (this branch and after)

1. **Shipped:** Phases A–F. Connect form, flags Y can read, ingest opens rooms, GitHub PR on HIGH approve (never merge), Cove on Cloud Run `cove` (Northstar retired as demo tenant).
2. **Shipped (live layer):** WebSocket rooms, agent_callback, funnel chips, Work/Transcript, flip artifacts, typed A2A, skip-if-done HITL, scenario run, ADK 2 Workflow catalog. Story: [`HACKATHON_STORY.md`](HACKATHON_STORY.md). Contract: `packages/contracts/api.md`.
3. **Later:** Finish Workspace OAuth client in Google Auth Platform (user paste on Connect), optional Live/PSTN, Agent Gateway still plan-only.

Do not build Y inside this repo. Do not restore `/shop` on `loop`.

---

## 8. Out of scope until named again

- Slack
- Secret Manager productization beyond Cloud Run env
- Second GCP project
- Custom domain
- Autonomous merge, send, or deploy
- Re-adding a storefront on `loop`
