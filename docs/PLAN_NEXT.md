# PLAN NEXT — make Product OS a product Company X can run

| Field | Value |
|---|---|
| Status | Binding for the next build. Start here, then code. |
| Date | 2026-08-30 |
| Spec | [`PRD.md`](PRD.md) remains binding (safety, risk tiers, no autonomous merge/deploy) |
| Architecture | [`PLAN.md`](PLAN.md) is what the fixture engine already implements |
| Tenant split | [`TENANT.md`](TENANT.md) — Product Y is never hosted on Cloud Run `loop` |

This is the plan for everything that is **specified but not wired**. The campus and the fixture loop stay. We stop pretending `pr_opened: True` is a pull request.

---

## 0. Honest now vs Company X

If Company X arrived today with Product Y, we could give them the **OS UI** (campus, rooms, approvals, memory) running on **our** Cloud Run. We could **not**:

- watch their live app
- onboard their org / git / deploy
- draft or send their mail
- put a meeting on their calendar
- call their customers
- change a flag their app reads
- open, push, or merge a PR on their GitHub

`execute_approved` writes a SQLite flag (or a `github_issue: true` boolean) and always sets `merged: False`. That is the whole side-effect path.

The six fixtures and `data/generate.py` warehouse stay as **evals**. They are not Company X.

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

From [`TENANT.md`](TENANT.md):

1. Empty tenant git repo + write access (PAT secret or repo on this Cloud Agent).
2. Second deploy (e.g. Cloud Run `northstar` in the same project — confirm).
3. Shared token secret **name**.
4. Both repos on the environment.

Then, **in that other repo**, build the demo Product Y: pages, flag client against `/api/t/.../flags`, voice POST, ads landing. OS never serves those pages.

Workspace OAuth client (Gmail draft / Calendar) is a **separate** user grant. Until then, mail/calendar connectors stay `skipped`.

---

## 5. What each missing capability becomes

| Capability | Implementation | Not this |
|---|---|---|
| Watch their app | Ingest API + optional BQ/file warehouse keyed by tenant | Scraping Y’s HTML from `loop` |
| Onboard / set up teams | Tenant record + Connect UI + token | Seven GEAP runtimes on day one |
| Draft mail | `mail.draft` record; Gmail API when OAuth | Claiming send |
| Send mail | Still **denied** by default (`GMAIL_CANNOT_SEND`) | Silent send |
| Calendar | `calendar.hold` record; Calendar API when OAuth | Fake Meet links as if created |
| Call customer | Freq-cap + text fallback; Live only if entitled | PSTN |
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

1. **This PR:** this file, then Phase A–D + Connect UI on the same branch.
2. **Shipped in-repo now:** `GET/POST /api/tenants`, `GET /api/t/{id}/flags`, ingest signals/voice, connectors that skip without secrets, `execute_approved` no longer claims a PR URL it does not have, rail **Connect**.
3. **When the user hands over repo + token + second deploy:** Phase D applied (real PRs), demo Y in the other repo, E if we load BQ.
4. **Later:** Workspace OAuth, optional Live, Agent Gateway still plan-only.

Do not block A–D on the tenant repo. Do not build Y inside this repo.

---

## 8. Out of scope until named again

- Slack
- Secret Manager productization beyond Cloud Run env
- Second GCP project
- Custom domain
- Autonomous merge, send, or deploy
- Re-adding a storefront on `loop`
