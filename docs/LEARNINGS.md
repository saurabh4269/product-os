# Learnings, pitfalls, and errors

Institutional memory so the next agent does not re-learn these the hard way. Pair with [`AGENTS.md`](../AGENTS.md).

---

## 1. Hosting

### `NEXT_PUBLIC_API_URL` bakes into the static JS

**Symptom:** Hosted UI calls `http://127.0.0.1:8080/api/...` and shows “Can’t reach the app.”

**Why:** `apps/console/lib/api.ts` reads `process.env.NEXT_PUBLIC_API_URL` at **build** time. `package-host.sh` runs `next build` with `LOOP_STATIC=1`. If the shell still has `NEXT_PUBLIC_API_URL=http://127.0.0.1:8080`, that URL is compiled into `out/`.

**Fix:**

```bash
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh && ./scripts/deploy-gcp.sh
```

Production console must use `BASE = ""` (same origin as FastAPI).

### `gcloud run deploy --source` does not work here

**Symptom:** Deploy fails; no Cloud Build.

**Why:** This Cloud Agent SA cannot run Cloud Build / Artifact Registry the usual way.

**Fix:** Use the public image + GCS tarball path already in `scripts/deploy-gcp.sh`:

1. `package-host.sh` writes `dist/loop-host.tgz` (vendor wheels + `loop/` + static `out/`).
2. Upload to `gs://mystical-timing-442601-q8-loop-host/loop-host.tgz` (object is world-readable so the container can fetch it).

### Cloud Run boot: `gcloud --args` commas vs one-arg `urlretrieve`

**Symptom:** New revision never listens; `/api/config` 503s until the previous revision is restored. `loop-00124-rc2` died this way after #30.

**Why:** Two separate traps.

1. `gcloud run deploy --args` splits on commas. A Python `urlretrieve(url, path)` inside a plain `--args="-c,…"` is cut in half.
2. One-arg `urlretrieve(url)` after `cd /tmp` does **not** write `loop-host.tgz`. Python 3.12 writes a random `NamedTemporaryFile`. `tar -xzf /tmp/loop-host.tgz` then fails and the container exits.

**Fix:** Use the `^|^` list delimiter so the bash `-c` script may contain commas, and pass an explicit dest: `urlretrieve(url, "/tmp/loop.tgz")`. Do **not** `apt-get` curl/git/node on every start — python:3.12-slim already has CA certs. `code_fix` extra skips cleanly without git/node; flags.json GitHub PR is the ship path. `--min-instances 1` so cold start is deploy-time, not every user.

### `LOOP_STATIC` left on breaks `next dev`

**Symptom:** Dev server behaves like a static export, or chunks 404 after `npm ci`.

**Why:** `package-host.sh` exports `LOOP_STATIC=1` in that process, but a leftover env in your shell / an old `next-server` will fight you.

**Fix:** `env -u LOOP_STATIC` when starting Next. After `package-host.sh` (`npm ci` wipes `node_modules`), **restart** `next dev`. Stale `next-server` on :3010 serves 404s for `/_next/static/chunks/main-app.js`.

### Do not `npx next`

**Symptom:** Next 16 appears, lockfile fights `npm ci`, two compilers race.

**Fix:** `apps/console/node_modules/.bin/next` only.

### Do not host the tenant product on this origin

**Symptom:** `/shop` and `/company` on `loop` Cloud Run; rail “Shop”; campus Shop pin.

**Why:** That made Product OS look like a demo that includes a fake store. Production OS observes a product. It does not serve the product.

**Fix:** Tenant HTML stays out of `apps/console/public` and FastAPI. `GET /api/company` does not exist. Fixture adapters stay in `apps/northstar-shop` (JS only). The real/demo shop is a **second repo and second deploy**. SPA fallback **404s** `/shop` and `/company` so they are not a fake storefront.

### Vendor for Cloud Run is Python 3.12

**Symptom:** New `loop` revision exits on boot: `No module named 'pydantic_core._pydantic_core'`. Previous revision still serves.

**Why:** `package-host.sh` used local `python3` (Kali 3.13). Cloud Run is `python:3.12-slim`. Native wheels are ABI-specific.

**Fix:** `package-host.sh` runs `pip install --target vendor` **inside** `docker run python:3.12-slim`. Confirm `pydantic_core/_pydantic_core.cpython-312-*.so` in the tarball.

Northstar does not vendor — it is stdlib-only (`python app.py`).

### Cloud Run SQLite is disposable

**Symptom:** Room IDs you bookmarked yesterday 404. Office looks freshly seeded.

**Why:** `/app/var` is not a volume. Lifespan calls `seed_world()` when there are no rooms.

**Fix:** Treat hosted IDs as ephemeral. `GET /api/rooms` after boot.

### Workspace OAuth client is Console-only

**Symptom:** Want a Google authorize URL; `gcloud` cannot create a standard Web OAuth client for Gmail/Calendar.

**Why:** Google Auth Platform clients are not the same as `gcloud iam oauth-clients` (workforce) or Agent Identity (plan-only / disabled here). The ADK Workspace codelab pattern is: create a Web client in Console → one `access_type=offline` consent → store refresh token → refresh in memory.

**Fix:** Connect → paste client → `/api/oauth/google/start`. Redirect URI must be `https://<LOOP_PUBLIC_URL host>/api/oauth/google/callback` (currently `https://productos.heisenbug.in/api/oauth/google/callback` when `LOOP_PUBLIC_URL` is set). External + Testing: add yourself as a test user. Do not enable Agent Identity just for this. Hosted refresh tokens live under `LOOP_DATA_DIR` and die on cold wipe unless you also keep the client in env.

### Live WebSocket vs static export

**Symptom:** Console on a random port cannot open `ws://…` if `NEXT_PUBLIC_API_URL` points at localhost while the page is elsewhere; hosted static must use same-origin `wss://`.

**Fix:** `roomSocket()` derives WS from `BASE` or `window.location.origin`. Package with `NEXT_PUBLIC_API_URL` unset. SPA catch-all must not steal `/ws` (FastAPI WebSocket routes are registered on the app).

### ADK 2 Workflow vs SequentialAgent

**Symptom:** Copying ADK 1.x ParallelAgent / LoopAgent trees into ADK 2 triggers deprecation; Workflow is not a drop-in `sub_agent`.

**Fix:** Prefer Workflow + JoinNode + RequestInput. Workflow-as-Tool (≥2.4) needs an explicit Pydantic `input_schema` on the Workflow or NodeTool rejects it. Attach only schema'd workflows on investigator. Hosted path stays the deterministic engine — soft-fail if `google-adk` missing.

### HEAD on static files may 405

**Symptom:** A health check that `HEAD /city/campus.webp` fails; `GET` is 200.

**Why:** FastAPI SPA routes are GET. Don’t use HEAD for “is the image there.”

### Custom domain on Cloud Run (`productos.heisenbug.in`)

**Symptom:** `gcloud beta run domain-mappings create` fails with “domain is not verified”; or HTTPS returns `TLS connect error: unexpected eof` for 15–60 minutes after mapping succeeds.

**Why:** Cloud Run custom domains need (1) a DNS CNAME to `ghs.googlehosted.com`, (2) the **base** domain verified once in Search Console for the same Google account as the GCP project, (3) time for Google-managed SSL to provision. Mapping before verification fails; TLS errors during cert issuance are normal, not a DNS typo.

**Fix:**

1. Cloudflare: `productos` CNAME → `ghs.googlehosted.com`, **DNS only** (grey cloud). Orange-cloud proxy breaks Google’s cert validation.
2. Verify the apex once: `gcloud domains verify heisenbug.in` → Search Console → **Domain** property → TXT at Cloudflare (covers all subdomains).
3. Run `./scripts/setup-productos-domain.sh` (or `gcloud beta run domain-mappings create --service=loop --domain=productos.heisenbug.in --region=us-central1`).
4. Set `LOOP_PUBLIC_URL=https://productos.heisenbug.in` on the service (`deploy-gcp.sh` already does). OAuth redirect, Twilio webhooks, and tenant onboard URLs all derive from this — update the Google OAuth client authorized redirect URI to `https://productos.heisenbug.in/api/oauth/google/callback` if you change the public URL.
5. Poll until `status.conditions[?type='Ready'].status` is `True`. The old `*.run.app` URL keeps working in parallel.

**Do not:** use the Site Verification REST API from a default `gcloud` token (403 insufficient scope) — use `gcloud domains verify` or Search Console UI. Wrangler/Cloudflare API is optional; DNS is manual in Cloudflare when no API token is configured.

### Auto-deploy on push to `main`

CI uses `./scripts/verify-deploy.sh` (skips Remotion). On green `main`, GitHub Actions runs
`package-host.sh` + `deploy-gcp.sh` — no laptop deploy needed. Requires repo secret
`GCP_SA_KEY`. See [`docs/DEPLOY.md`](DEPLOY.md).

---

## 2. Console API / CORS

### Local Next (:3010) → local API (:8080) is blocked

**Symptom:** Browser console: `Access-Control-Allow-Origin` missing on `/api/office`.

**Why:** CORS allow-list is `LOOP_CONSOLE_ORIGIN` plus `localhost:3000` / `127.0.0.1:3000`. Cloud Run sets wildcard via `K_SERVICE`. A random dev port is not listed.

**Fix (pick one):**

- `NEXT_PUBLIC_API_URL=https://loop-5uy6fkd7bq-uc.a.run.app` (hosted allows `*`)
- `LOOP_CONSOLE_ORIGIN=*` on local uvicorn
- Use `./scripts/boot.sh` so the console is on `:3000`

`next.config.ts` rewrites `/backend/:path*` — the client does **not** use that prefix. `lib/api.ts` calls `/api/...` directly.

### Rewrites vs baked URL

Dev without `NEXT_PUBLIC_API_URL` uses `http://127.0.0.1:8080`. That is a **cross-origin** fetch, not a rewrite. Same-origin only happens on the hosted static bundle (`BASE === ""`).

---

## 3. Static export / routing

### Dynamic `/rooms/[id]` and `/agents/[id]` need a placeholder

**Symptom:** `next build` with `LOOP_STATIC=1` fails, or hosted `/agents/analytics_agent` is a raw 404.

**Why:** `output: "export"` requires `generateStaticParams`. We emit `{ id: "_" }`.

**Fix:** Keep `app/rooms/[id]/layout.tsx`, `app/agents/[id]/layout.tsx`, `app/investigations/[id]/layout.tsx`. FastAPI `_spa_file()` maps `rooms/*`, `agents/*`, `investigations/*` to that `_` HTML.

Client pages then read the real id from `usePathname()` (see `lib/route-id.ts`). A mount-once `window.location` read is wrong: the `_` page is reused, so sidebar room/agent switches would keep the first id.

### `/investigations/:id` is not a room id

**Symptom:** Approvals “Open room” shows “Can’t reach the app” / `/api/rooms/inv_… 404`.

**Why:** The room view treated the last path segment as a room id. Investigation ids are `inv_*`. `GET /api/rooms/{inv_id}` is 404.

**Fix:** Resolve `investigation_id` → room, then `router.replace(/rooms/{id})`. Approvals should link the room when the list is loaded. Do not call `/api/rooms/{inv_id}`.

### Nested `<a>` in room cards

**Symptom:** React hydrate warning / invalid HTML if `HiveChamber` → `PixelOffice` wraps people in `<Link>` while the card is already a `<Link>`.

**Fix:** `PixelOffice` / `HiveChamber` use `link={false}` inside cards.

---

## 4. Campus map (the phone “everything is floating” bug)

### Pins were % of the **frame**, image was `object-contain`

**Symptom:** On a portrait phone, Memory / Approvals sit in white space below the island. Pins hover above buildings. Huge empty band under the map.

**Why:** Overlay `left/top: 26%` is relative to a tall `h-screen` box. The PNG is 3:2 and letterboxed, so 67% Y is below the grass.

**Fix:** `ResizeObserver` on the image frame vs `naturalWidth/Height`. Position pins **inside** that content box. Campus section on phone is `aspect-[3/2]` + `max-h-[56vh]`, not `h-screen`. Desktop can still be a full-viewport hero (`lg:h-full`).

### JSX: `<img>` vs `<img`

**Symptom:** `ModuleBuildError: Unexpected token` at the campus `<img>`.

**Why:** An eslint comment insertion once turned `<img` into a closed `<img>` and left attributes dangling.

**Fix:** Keep one `<img` with attributes. `@next/next/no-img-element` is a warning; `next/image` fights `object-contain` measurement. Leave the disable comment **above** the tag, not inside it.

### Do not restore the 2MB campus PNG

`campus.webp` (~75KB) + tiny JPEG LQIP + `<link rel="preload">` in `layout.tsx`. `pin.webp` is a few KB. Re-adding PNG makes first paint crawl on a phone.

### Landmark coordinates (full image, 1350×900)

Calibrated against the artwork, not the CSS box:

| Slot | % | Landmark |
|---|---|---|
| Incidents | 24, 48 | Workshop / factory |
| Reviews | 40, 42 | Clock hall |
| Ideas | 50, 56 | Bridge / center |
| Ops | 72, 44 | Yellow labs |
| Research | 84, 42 | Dark office |
| Memory | 28, 72 | Pocket watch |
| Approvals | 50, 80 | Tram |

Rooms that share a district **fan out** so three Ideas pins do not stack.

---

## 5. Layout / people / sidebar

### Sidebar as a 248px column on a phone

**Symptom:** User screenshot: tiny unreadable nav eating ~35% width, campus crushed.

**Why:** `hidden md:flex` still shows the desktop aside from 768px, and some phones / “desktop mode” hit that.

**What we do now:** 64px **icon rail always**. Expand button (Linear / Notion). **Same aside** grows in place on every width — the phone flyout was a second rail (second mark, second nav) and the user rejected it. Key: `loop-sidebar`. Do not bring back hamburger-only, a second overlay panel, or a permanent wide column on a phone.

### `overflow-x-auto` clips heads

**Symptom:** Room-card pixel people missing heads or feet even after you removed `h-[80px]`.

**Why:** If `overflow-x` is `auto`/`scroll` and `overflow-y` is `visible`, CSS computes **both** to auto. Combined with `items-end` and a short flex line, the bob animation and the top of the sprite clip.

**Fix:** Pad **inside** the scrollport (`py-2`). Give the people strip real `pt-6`. Do not use a fixed 80px / 120px height with `overflow-hidden` for sprites + desks + labels + speech chips.

Desks in compact room cards looked like “gray pedestals” under chopped bodies — compact mode is **sprites + names only**.

### `agent-bob` + overflow

`.agent-bob` translates −1px. Harmless if the parent does not clip. Combined with overflow it looks like shaved hair. Prefer padding over killing the animation.

### Office tiles at `w-[132px]` flex-wrap

**Symptom:** Six people on one row, a seventh alone; “doing” pills truncated to `Rage-clicks…`.

**Fix:** `grid-cols-2` on a phone, `Working` instead of the full sentence. In-flow status chips (not `absolute -top-5`) so `overflow-hidden` on the card does not clip them.

---

## 6. Product / UX decisions (do not silently revert)

| Tried | Outcome |
|---|---|
| Dark ink `#100e14` + coral + Instrument Serif “war room” | User rejected. Wanted Apple / Stripe / cloud, welcoming. |
| Google Doc as the source of “the office” | Unreadable (auth). Build the office in-product. |
| Full-viewport campus only, no scroll | User wanted the previous office / rooms / signals **below** the island. |
| Sidebar hidden until hamburger | “Always hidden.” They want a narrow rail + expand. |

| Host Northstar shop + ads on Cloud Run `loop` (`/shop`, `/company`) | User rejected. Product OS is not the tenant product. Separate repo + deploy. See [`TENANT.md`](TENANT.md). |
| Shop pin / Shop rail on the campus | Same. Landmarks are Memory (watch) and Approvals (tram) only. |
| `next.config` rewrite `/shop` → `/shop/index.html` | Only existed so Next could serve a storefront from `public/shop`. Removed. |
| Separate **Traces** rail entry + full-page trace list | User rejected duplicate UX. Live rooms and the old Traces view were the same job (messenger chat + handoffs). **Traces removed from sidebar**; `room-view.tsx` uses the Traces chrome. `/traces` redirects to `/` for old bookmarks. Backend `GET /api/traces` stays for debugging. |
| Incident room “war room” chrome (funnel badge, ← Campus, dual Send, All conversations → Traces) | User found it intimidating vs the lighter Traces messenger. Rooms are chat-first: compact header, inline Review chip, phone menu for calls — not a second navigation surface. |
| Architecture diagram / “Architecture →” on the **home page** | User rejected — homepage already busy. Loop/fleet diagrams live under **Labs → Architecture** only. Do not re-add `Link` to `/labs/architecture` on home, `DemoRunner`, `SevenStepLoop`, or `WorkflowLinksPanel`. `requestFlowView` scrolls to live work or opens the current room, not the diagram. |
| Raw Memory page (bare `<p>` lists) | User wanted minimal but polished. Memory uses search, kind icons, accent cards, provenance chips — keep that pattern; don’t regress to unstyled dumps. |

Keep the toy-town campus. Keep scroll-to-office. Keep per-bot pages at `/agents/:id`. Do not put a storefront back on this origin.

---

## 7. Verification traps

### Pixel bob vs Chrome `--virtual-time-budget`

Headless Chrome with virtual time can **hang** on `agent-bob` / `pin-bob` infinite animations. Prefer a real timeout + `networkidle0`, or disable animation in the test user-agent.

`/usr/bin/google-chrome` may be a wrapper that fights remote debugging. Use `/usr/bin/google-chrome-stable`.

`computerUse` Cloud Agent quota can be exhausted; fall back to puppeteer-core + screenshots.

### Image-description models lie about crop

A screenshot of a **scrolled** card (top of the next card in view) gets described as “heads clipped.” Measure `getBoundingClientRect()` of the canvas vs its parent before “fixing” sprites again.

The Next.js **N** overlay in `next dev` is not product UI. It sits on the rail avatar. Production does not have it.

### `next lint` img warning

`@next/next/no-img-element` on campus/pin. Warning only unless CI is set to fail on warnings. A prior commit existed only to quiet export. Do not switch those tags to `next/image` without re-doing box measurement.

---

## 8. Git / PR

- Feature branches: `cursor/<name>-e32b`, lowercase.
- Preferred base: `main`.
- `origin/main` can move independently (e.g. PR #1). **Rebase or merge main before you declare the PR mergeable.** PR #2 was `CONFLICTING` on `README.md` / `.gitignore` for this reason.
- `gh` in this environment is **read-only**. Do not `gh pr create`. Use the repo’s PR tool. Push with `git push -u origin <branch>`.
- Do not add AI co-author trailers. If a hook injects `Co-authored-by: Cursor <cursoragent@cursor.com>`, strip it with `git commit-tree` before you finish.

---

## 10. Homepage IA (2026-09-02)

**What was wrong:** `app/page.tsx` stacked CityMap + ops dashboard (collapsed pipeline, activity log, demo strip, static connector list). Users could not see A2A handoffs, tool embeds, or walk into live rooms without scrolling past empty chrome. `evalMode` defaulted `true` before config loaded, so fixture rooms flashed on hosted.

**What we ship now** (see [`DESIGN_INTENT.md`](DESIGN_INTENT.md)):

1. **Campus hero** — handoff paths animate when WS is live (not demo-only).
2. **A2A graph** — `HandoffGraph` from `/api/office` handoffs + working agents.
3. **Glass box** — `HomeGlassBox` from `/api/proof` + featured `/api/live-work` card with `ProofEmbed`.
4. **Open rooms rail** — fixture rooms hidden when `eval_mode` is false; Type A/B label on cards.
5. **Room chat** — `RoomCaseBanner` (path, risk, memory recall, gateway deny), evidence graph, structured Customer Voice cards.
6. **No Demo chrome** on hosted (`LOOP_EVAL=0`).

Honest empty/offline when no receipts — never a fake live strip.

---

## 9. Quick debug checklist

```bash
# Hosted healthy? (custom domain + run.app both valid)
curl -s -o /dev/null -w "%{http_code}" https://productos.heisenbug.in/
curl -s -o /dev/null -w "%{http_code}" https://productos.heisenbug.in/api/office
curl -s -o /dev/null -w "%{http_code}" https://loop-5uy6fkd7bq-uc.a.run.app/api/office
curl -s -o /dev/null -w "%{http_code}" https://productos.heisenbug.in/city/campus.webp

# Custom domain cert ready?
gcloud beta run domain-mappings describe --domain=productos.heisenbug.in --region=us-central1 \
  --project=mystical-timing-442601-q8 --format="yaml(status.conditions)"

# Did we bake localhost?
# View-source the hosted JS or search the tarball:
grep -R "127.0.0.1:8080" apps/console/out || true

# Local office has people?
curl -s http://127.0.0.1:8080/api/office | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['working'], len(d['desks']))"
```

If hosted HTML is the campus but XHR 404s, you shipped a new revision that is still installing apt packages — wait and retry, don’t revert the UI.

---

## 11. Hosted stability and handoff (2026-09-03)

### Unauth `/rooms` must not ErrorState on 401

**Symptom:** Logged-out user hits `/rooms` and sees a red error, or gets bounced to a stale last-room URL.

**Why:** Protected reads return 401 when `LOOP_EVAL=0`. Chrome autocomplete can leave a fake session that looks logged-in.

**Fix:** Stay on index with Connect CTA (PR #23). Do not `ErrorState` on 401 for `/rooms`. Do not redirect to `localStorage` last room.

### 4s campus poll + WS-tick world refetch OOMs 2Gi

**Symptom:** GFE returns **429 Rate exceeded** on campus, `/api/rooms`, or `/api/office`. Revision logs show **OOM** (RSS>2048) and **503** under load.

**Measured (loop-00136-xrw, 30m):** OOM×12 · GFE 429×229 · 503×329. Top request paths: `/api/rooms` (546), `/api/office` (521). Median client poll gap still ~4s. Default Cloud Run `containerConcurrency=80` stacks concurrent handlers until memory blows.

**Why:** Campus polled office + rooms on every WS tick (and faster when tab visible). `/api/office` called `list_all_messages` + `list_all_agent_calls` per poll. `/api/rooms` list did N SQL round-trips per room. GFE 429 is **not** an in-app rate limiter — it is often OOM/backpressure.

**Fix (PR #35 — stay on 2Gi forever, no 4Gi):**
- `deploy-gcp.sh`: `--memory 2Gi` + `--concurrency 8` (explicit; never 80). Production profile: `LOOP_INLINE_WORKER=0`, `LOOP_AUTO_INVESTIGATE=0`.
- Batch `room_message_summaries()` for GET `/api/rooms` list; no per-room `list_messages`.
- Office snapshot: SQL caps (`recent_agent_calls`, `message_stats_by_author`) — no full-table loads.
- Console: 30s/60s debounced refetch; **pause polls when `document.hidden`**.
- Slim `/api/status`; WS `initial_state` = activity only.

Do not re-add aggressive campus polling or raise memory to 4Gi without owner sign-off.

### Persist GCS before deploy; crash-loop must not overwrite a good snapshot

**Symptom:** After deploy, live rooms (e.g. hang demo `room_f627763ea9`) vanish. Office looks freshly seeded.

**Why:** `LOOP_STATE_GCS_URI` hydrates on boot. Packaging/deploy while live is 503/OOM uploads a corrupt or empty DB and wipes post-snapshot rooms.

**Fix:** When hang room `GET /api/rooms/{id}` is **200**, persist live sqlite to GCS **before** `package-host.sh`. If live is **503/OOM**, do **not** overwrite a good snapshot — fix the instance first.

### `code_fix` failure receipt must not `kind=github` on the flags PR URL

**Symptom:** Room UI shows a GitHub card pointing at Cove `flags.json` PR for a failed `code_fix` action.

**Why:** Failure receipt reused the `github_pr` artifact kind/URL. `code_fix` failed (no node in worker); `github_pr` is the real ship path.

**Fix:** PR #27 merged (`54b4b97`). Until deploy, hosted UI may still show FAILED+DONE conflated. Do not approve leftover `act_4754e1ae24f5` — duplicates Cove #17.

### Remotion Lesson scene must not use `recalled_lessons` from other metrics

**Symptom:** Demo video Lesson slide mentions `checkout_conversion` on an OTP hang investigation.

**Why:** `export-demo` / `build_demo_scenes` pulled global `recalled_lessons` instead of investigation-scoped `lessons[]`.

**Fix:** PR #26 — lesson scenes use `investigation.lessons[]` only. Regenerate `loop.json` after export. Do not commit hang-specific `loop.json`.

### Unique metric when an AWAITING_APPROVAL room still has pending actions

**Symptom:** Same-metric ingest opened a second demo room (or closed the hang room) after leftover HIGH was hidden because a flags PR already shipped.

**Why:** Join required visible pending actions. PR #27 hides duplicate HIGH once a sibling opened the tenant PR, so join returned false.

**Fix:** Same tenant+metric joins an open `AWAITING_APPROVAL` room when pending remains **or** a flags PR already shipped. Pick a **unique metric** only when you intend a new room (e.g. `otp_verify_hang_0904`). Do not approve leftover `act_4754e1ae24f5`.
