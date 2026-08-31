"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useDemoGuide } from "@/lib/demo-guide-context";
import { getDemoCount, hasRunDemo, markDemoRun } from "@/lib/first-visit";
import { demoToastMessage } from "@/lib/home-pulse";
import { useToast } from "@/lib/toast-context";
import {
  applyPipelineCard,
  pendingApprovalFromCard,
  pollDemoPipeline,
} from "@/lib/pipeline-demo";
import { useGlobalWs } from "@/lib/use-global-ws";
import { GuidedDemoStrip } from "@/components/guided-demo-strip";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

export function DemoRunner({ variant = "card" }: { variant?: "card" | "bar" }) {
  const router = useRouter();
  const demo = useDemoGuide();
  const toast = useToast();
  const { activity } = useGlobalWs();
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);
  const firstRun = !hasRunDemo();

  const fleetWorking = demo?.fleetWorking ?? false;

  const run = useCallback(async () => {
    setBusy(true);
    setErr(null);
    setRoomId(null);
    setLog(["Posting checkout signal…", "Opening investigation room…"]);
    demo?.startDemo(null);
    try {
      const out = await api.demoRun();
      const demoCountBefore = getDemoCount();
      markDemoRun();
      setLog((l) => [
        ...l,
        out.joined ? "Joined open investigation" : "Room open — agents collecting evidence",
        out.async ? "Watch Live work · each step is real (BQ / logs / deploy)" : "Pipeline running",
      ]);
      toast?.push(demoToastMessage(demoCountBefore + 1), { hot: true });
      if (out.room_id) {
        setRoomId(out.room_id);
        demo?.startDemo(out.room_id);
      }
      window.setTimeout(() => {
        document.getElementById("pipeline-board")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        document.getElementById("live-work")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 200);
      try {
        const pipe = await api.pipeline();
        const card = pipe.cards.find((c) => c.room_id === out.room_id);
        if (card && out.room_id) {
          const { needsApproval, actionId } = applyPipelineCard(card, demo);
          if (needsApproval && actionId) {
            demo?.setPendingApproval(await pendingApprovalFromCard(card, out.room_id));
            demo?.setFleetWorking(false);
          } else {
            // Async path: investigators still running — poll until approval (~10–15s)
            void pollDemoPipeline(out.room_id, demo, out.async ? 90000 : 45000);
          }
        } else if (out.room_id) {
          void pollDemoPipeline(out.room_id, demo, out.async ? 90000 : 45000);
        }
      } catch {
        /* pipeline optional */
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Demo failed");
      demo?.endDemo();
    } finally {
      setBusy(false);
    }
  }, [demo, toast]);

  useEffect(() => {
    demo?.registerRunDemo(() => void run());
    return () => demo?.registerRunDemo(null);
  }, [demo, run]);

  useEffect(() => {
    if (!fleetWorking && !demo?.active) return;
    const latest = activity[0];
    if (!latest?.message) return;
    const line = latest.message;
    setLog((prev) => (prev[0] === line ? prev : [line, ...prev].slice(0, 10)));
  }, [activity, fleetWorking, demo?.active]);

  const progressStrip =
    (fleetWorking || busy) && demo?.active ? (
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center p-3 sm:p-4">
        <div className="pointer-events-auto w-full max-w-xl rounded-2xl border border-border bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[13px] font-semibold tracking-tight">
                {busy ? "Starting investigation…" : "Agents at work"}
              </p>
              <p className="mt-0.5 text-[12px] text-[var(--dim)]">
                Real steps — signal → evidence → approve. Watch the board above.
              </p>
            </div>
            {!busy ? (
              <button
                type="button"
                className="shrink-0 text-[12px] text-[var(--faint)] hover:text-foreground"
                onClick={() => demo?.setFleetWorking(false)}
              >
                Hide
              </button>
            ) : null}
          </div>
          <ul className="mt-2 max-h-28 space-y-1 overflow-y-auto text-[12px] text-[var(--dim)]">
            {log.slice(0, 6).map((line, i) => (
              <li key={`${line}-${i}`} className={i === 0 ? "font-medium text-foreground" : ""}>
                {line}
              </li>
            ))}
          </ul>
          {roomId ? (
            <div className="mt-2 flex flex-wrap gap-2">
              <Button variant="ghost" className="h-8 rounded-full px-3 text-[12px]" onClick={() => router.push(`/rooms/${roomId}`)}>
                Open room
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    ) : null;

  return (
    <>
      {progressStrip}

      {variant === "bar" ? (
        <div id="demo" className="flex flex-wrap items-center gap-2">
          <Button
            onClick={() => void run()}
            disabled={busy}
            className={cn("rounded-full px-4", firstRun && !busy && "cta-pulse")}
          >
            {busy ? "Starting…" : firstRun ? "See it work" : "Run demo"}
          </Button>
          {roomId ? (
            <>
              <Button variant="ghost" onClick={() => router.push(`/rooms/${roomId}`)} className="rounded-full">
                Room
              </Button>
            </>
          ) : null}
          {err ? <p className="text-[12px] text-red-600">{err}</p> : null}
        </div>
      ) : (
        <div id="demo" className="rounded-2xl border border-border bg-white px-5 py-4">
          <h2 className="text-[20px] font-semibold tracking-tight">Run demo</h2>
          <GuidedDemoStrip />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button onClick={() => void run()} disabled={busy}>
              {busy ? "Starting…" : "Run demo"}
            </Button>
            {roomId ? (
              <Button variant="ghost" onClick={() => router.push(`/rooms/${roomId}`)}>
                Open room
              </Button>
            ) : null}
            {err ? <p className="text-[13px] text-red-600">{err}</p> : null}
          </div>
          {!fleetWorking && log.length ? (
            <ul className="mt-4 space-y-1 text-[12px] text-[var(--dim)]">
              {log.slice(0, 6).map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
    </>
  );
}
