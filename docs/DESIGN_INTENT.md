# Design intent — Product OS (LOOP)

Binding spec for UI and architecture. Hosted production runs `LOOP_EVAL=0` at https://productos.heisenbug.in. Tenant apps (e.g. Cove) are separate deploys — never theme or special-case the control plane around a demo tenant.

Safari / 3DS / Apple Pay / checkout examples in scenario fixtures are **recipes only**. Do not bias architecture, tests, or UI around them.

---

## UI language

Think Grok Bot, OpenClaw, Buzz — campus + multi-room chat, pixel agents in rooms, live A2A graph of the Incident Commander fanning out to specialists, live embeddings/cards of the tool in focus (tenant UI, GitHub PR, logs, mail, BQ evidence) so the user never leaves the page. Quiet Google / Apple. No Demo chrome on hosted.

References (visual register, not licensed art):

- https://beautifului.dev · https://beui.dev · https://rareui.com · https://transitions.dev · https://ui.shadcn.com
- refero.design · https://land-book.com · https://saaslandingpage.com · https://siteinspire.com · https://lapa.ninja
- Pixel agents: https://github.com/pixel-agents-hq/pixel-agents
- Architecture diagrams: excalidraw-skill · openflipbook · react-isometric-grid (isometric office only — campus stays painted art)

---

## Agents (named specialists)

Visible in registry, A2A graph, and room — not one blob:

| Agent | Role |
|---|---|
| **Signal** | Detect anomalies across technical, business, and customer signal families |
| **Investigator** | Fan out in parallel to Analytics, Logs, Deployment, Database, Customer, Code |
| **Customer Voice** | Adaptive diagnostic conversation with incident context; structured JSON evidence, not a survey |
| **Feedback** | Extract reasons; cluster feature requests |
| **Root Cause** | Hypothesis with confidence and checked evidence arms |
| **Code** | Patch, tests, PR — never merge, never customer PII |
| **Test** | Regression must fail pre-change and pass post-change |
| **Product** | Feature proposals with impact |
| **Risk** | LOW / MEDIUM / HIGH surface tier — not model confidence |
| **Learning** | Post-fix before/after metrics; write lesson to Memory Bank |

**Incident Commander** (`orchestrator`) discovers agents via Registry and coordinates via A2A; does not gather evidence itself.

---

## Customer Voice

Diagnostic, not a survey. Receives incident context and produces structured evidence JSON:

`reason`, `severity`, `purchase_intent`, `friction`, `competitor_mentioned`, `feature_request`, `willing_to_retry`, `confidence`

Plus transcript when available. Never architect around “why didn’t you complete payment?”

---

## Evidence and paths

- **Multi-source aggregation**: analytics + logs + deploy + customer + code
- **Three-source gate**: ≥3 independent evidence groups before root-cause hypothesis
- **Type A** — find and fix (BUG → code / test / PR)
- **Type B** — find and improve (FEATURE → proposal + impact, human)
- **Risk**: LOW auto test+PR (docs/typo/test); MEDIUM developer (business logic/db); HIGH mandatory human (auth, payment authorization, financial calc, destructive)
- `fail_open=false`. LOOP never auto-merges or prod-deploys tenant

---

## Learning and memory

After-fix Learning Agent: before/after metrics, did it work, recovered outcome.

**Four memory kinds** (recall on similar signals):

1. customer  
2. product  
3. engineering  
4. organizational  

BigQuery = facts. Memory Bank = knowledge. Do not dump raw GA4 into memory.

---

## Gateway and registry

Gateway is **identity + policy** — an agent cannot do what it lacks permission for. Model Armor on content. Registry lists owner, capabilities, permissions, version, risk, status.

Examples: Analytics agent cannot Gmail / GitHub-write / deploy. Engineering cannot customer PII. Exfil is **DENY via identity**, not a prompt.

---

## Signals

Technical + business + customer. Acquisition funnel is one signal family, not the only one.

---

## Honest skip

Do not fake capabilities. When not wired or not entitled, show **skipped** in UI with reason:

- Google Telephony / Gemini Live voice  
- Experiment % rollout when not entitled  
- Model Armor when API not enabled  

Never silent pretend success.

---

## MCP / connectors (plan vs wired)

Analytics, GitHub, logs, CRM, DB, deploy, support, calendar, email, telephony — each returns `applied`, `skipped`, `denied`, or `reused`. Developer coordination: CODEOWNER, Calendar, Gmail/Meet draft (never send).

---

## Homepage information architecture

1. **Campus** — painted map, pixel agents on buildings, handoff paths when live  
2. **A2A graph** — who handed what to whom from `/api/office` handoffs  
3. **Glass box** — live proof cards (BQ, GitHub, mail, tenant) from `/api/proof` and `/api/live-work`  
4. **Open rooms** — walk into live work; fixture rooms hidden when `eval_mode` is false  
5. **Honest empty** — no fake “live” strip when WS or receipts are absent  

Rooms are the unit of work. Home should make you want to enter a live room.

---

## Hard rules

- No hardcoded Safari / checkout / Cove paths  
- Generic pipeline only  
- Models only in `config/models.yaml`  
- No secrets in git or static bundle  
- `./scripts/verify-deploy.sh` must pass  
