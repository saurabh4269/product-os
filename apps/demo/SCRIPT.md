# Product OS — MacOsDemo voiceover script

Locked script for the All Things Agentic / LOOP product film. Timing is @ 30 fps in `src/script.ts`.

**Tone:** Founder walking a judge through Product OS. Natural, confident, specific. No hype, no “in this video…”, no feature laundry list.

**Cove** = demo tenant only. Product OS is the control plane.

---

## Cold open · 0:00–0:08 (240 frames)

*Quiet Mac desktop. Cursor rests. Product OS window opens.*

> Checkout just stalled for a bunch of people. Not a ticket. A signal.

---

## Signal · 0:08–0:20 (360 frames)

*Tenant metric ingest → new room opens.*

> Product OS opens a room the moment the metric breaks. Same generic pipeline we’d use for any product — Cove is just the tenant we’re demoing.

---

## Specialists / A2A · 0:20–0:38 (540 frames)

*Room with parallel agents, handoffs visible.*

> Specialists fan out in parallel — analytics, logs, code, research, customer voice. You can see them hand work to each other. No black box.

---

## Outreach · 0:38–0:52 (420 frames)

*Contact lookup · mail abandon cohort.*

> We don’t guess. We look up people who abandoned mid-checkout and ask what they saw. Mail first — calls only if they don’t respond.

---

## Root cause · 0:52–1:08 (480 frames)

*Customer Voice diagnostic · hypothesis locked.*

> Feedback lines up with the logs: OTP verify is hanging. That’s the root cause — not a vague “payments feel slow.”

---

## HIGH gate + PR · 1:08–1:28 (600 frames)

*Approve door · tenant flags PR.*

> Fix is HIGH risk, so a human has to open the door. One click — flags PR on the tenant repo. We never auto-merge.

---

## Call / close · 1:28–1:50 (660 frames)

*Phone notify card · verify path.*

> If someone’s still stuck after the fix, Lexi calls — short, human, “it’s fixed, sorry for the wait.” Then we measure whether checkout recovers, and we remember the lesson.

---

## End card · 1:50–1:58 (240 frames)

*Product OS · productos.heisenbug.in*

> Observe. Investigate. Gate. Ship. Measure. Remember.

---

## Export + render

```bash
# Hosted hang room (preferred)
python3 -m loop.cli export-demo --room room_f627763ea9 -o apps/demo/out/hang.json
cp apps/demo/out/hang.json apps/demo/public/loop.json

# Or local generic
python3 -m loop.cli export-demo -o apps/demo/public/loop.json

cd apps/demo && npm run render:macos
```

Studio: `npm run dev` → **MacOsDemo** (~118 s).
