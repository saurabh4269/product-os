# DEMO_JUDGE_SCRIPT — All Things Agentic / LOOP product film

**Founder voice.** Natural, confident, specific. No hype, no “in this video…”, no feature laundry list.

**Room:** `room_65a4654bec` · **metric:** `otp_verify_hang_demo_1788625174` · **Voice:** `otp_verify_timeout` · **HIGH → Cove PR #18**

**Cove** = demo tenant only. Product OS is the control plane.

Timing @ 30 fps in `src/script.ts`. Export payload: `fixtures/demo-room_65a4654bec.json`.

---

## Cold open · 0:00–0:08

*Quiet Mac desktop. Cursor rests. Product OS window opens.*

> Checkout just stalled for a bunch of people. Not a ticket. A signal.

---

## Signal · 0:08–0:20

*Export scene 1: `otp_verify_hang_demo_1788625174` −18% vs 64% baseline.*

> Product OS opens a room the moment the metric breaks. Same generic pipeline we’d use for any product — Cove is just the tenant we’re demoing.

---

## Specialists / A2A · 0:20–0:38

*Export scene 2: analytics · code · customer_voice · deploys · logs.*

> Specialists fan out in parallel — analytics, logs, code, research, customer voice. You can see them hand work to each other. No black box.

---

## Outreach · 0:38–0:52

*Contact lookup · mail abandon cohort.*

> We don’t guess. We look up people who abandoned mid-checkout and ask what they saw. Mail first — calls only if they don’t respond.

---

## Root cause · 0:52–1:08

*Export scene 3: `otp_verify_timeout` · client-error cluster.*

> Feedback lines up with the logs: OTP verify is hanging. That’s the root cause — not a vague “payments feel slow.”

---

## HIGH gate + PR · 1:08–1:28

*Export scene 4: human gate · Cove `config/flags.json` PR #18 · never auto-merge.*

> Fix is HIGH risk, so a human has to open the door. One click — flags PR on the tenant repo. We never auto-merge.

---

## Call / close · 1:28–1:50

*Export scenes 5–6: verify INCONCLUSIVE · lesson · Lexi call.*

> If someone’s still stuck after the fix, Lexi calls — short, human, “it’s fixed, sorry for the wait.” Then we measure whether checkout recovers, and we remember the lesson.

---

## End card · 1:50–1:58

> Observe. Investigate. Gate. Ship. Measure. Remember.

**productos.heisenbug.in**

---

## Export + render

```bash
# Owner box (preferred)
python3 -m loop.cli export-demo --room room_65a4654bec -o apps/demo/out/hang.json
cp apps/demo/out/hang.json apps/demo/public/loop.json

# VM / CI fixture (committed)
cp apps/demo/fixtures/demo-room_65a4654bec.json apps/demo/public/loop.json

cd apps/demo && npm run render:macos
```
