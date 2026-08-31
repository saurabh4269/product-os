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
2. Upload to `gs://mystical-timing-442601-q8-loop-host/loop-host.tgz` (object is world-readable so the container can `curl` it).
**Fix:** Keep the known-good `apt-get` + `curl` boot (gcloud `--args` splits on commas, so a Python `urlretrieve(url, path)` will cut the script in half and the revision never listens). Set `--min-instances 1` so apt-get only runs on deploy, not on every user. Warm TTFB should be hundreds of ms. Do not treat that as a code bug.

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

**Fix:** Connect → paste client → `/api/oauth/google/start`. Redirect URI must be `https://loop-…/api/oauth/google/callback`. External + Testing: add yourself as a test user. Do not enable Agent Identity just for this. Hosted refresh tokens live under `LOOP_DATA_DIR` and die on cold wipe unless you also keep the client in env.

### Live WebSocket vs static export

**Symptom:** Console on a random port cannot open `ws://…` if `NEXT_PUBLIC_API_URL` points at localhost while the page is elsewhere; hosted static must use same-origin `wss://`.

**Fix:** `roomSocket()` derives WS from `BASE` or `window.location.origin`. Package with `NEXT_PUBLIC_API_URL` unset. SPA catch-all must not steal `/ws` (FastAPI WebSocket routes are registered on the app).

### ADK 2 Workflow vs SequentialAgent

**Symptom:** Copying ADK 1.x ParallelAgent / LoopAgent trees into ADK 2 triggers deprecation; Workflow is not a drop-in `sub_agent`.

**Fix:** Prefer Workflow + JoinNode + RequestInput. Workflow-as-Tool (≥2.4) needs an explicit Pydantic `input_schema` on the Workflow or NodeTool rejects it. Attach only schema'd workflows on investigator. Hosted path stays the deterministic engine — soft-fail if `google-adk` missing.

### HEAD on static files may 405

**Symptom:** A health check that `HEAD /city/campus.webp` fails; `GET` is 200.

**Why:** FastAPI SPA routes are GET. Don’t use HEAD for “is the image there.”

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

## 9. Quick debug checklist

```bash
# Hosted healthy?
curl -s -o /dev/null -w "%{http_code}" https://loop-5uy6fkd7bq-uc.a.run.app/
curl -s -o /dev/null -w "%{http_code}" https://loop-5uy6fkd7bq-uc.a.run.app/api/office
curl -s -o /dev/null -w "%{http_code}" https://loop-5uy6fkd7bq-uc.a.run.app/city/campus.webp

# Did we bake localhost?
# View-source the hosted JS or search the tarball:
grep -R "127.0.0.1:8080" apps/console/out || true

# Local office has people?
curl -s http://127.0.0.1:8080/api/office | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['working'], len(d['desks']))"
```

If hosted HTML is the campus but XHR 404s, you shipped a new revision that is still installing apt packages — wait and retry, don’t revert the UI.
