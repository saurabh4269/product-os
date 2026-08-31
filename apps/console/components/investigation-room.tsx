"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";
import { api, type Bundle } from "@/lib/api";
import { queryId, segmentId } from "@/lib/route-id";
import { pct, when } from "@/lib/utils";
import { Badge, Button, Card, ErrorState, Loading } from "@/components/ui";
import { EvidenceGraph } from "@/components/evidence-graph";

const PIXEL: Record<string, string> = {
  signal_agent: "#6e6e73",
  orchestrator: "#0071e3",
  analytics_agent: "#5b7c99",
  logs_agent: "#8e8e93",
  deployment_agent: "#4a5568",
  customer_voice_agent: "#6b7c6e",
  feedback_agent: "#a3b5c9",
  root_cause_agent: "#636366",
  risk_agent: "#b75106",
  code_agent: "#48484a",
  product_agent: "#5b7c99",
  learning_agent: "#248a3d",
  tool_output_armor: "#de3b2f",
};

function Pixel({ name, size = 10 }: { name: string; size?: number }) {
  const color = PIXEL[name] ?? "#64748b";
  return (
    <span
      className="inline-grid grid-cols-2 gap-px"
      style={{ width: size, height: size }}
      aria-hidden
    >
      {[0, 1, 2, 3].map((i) => (
        <span key={i} style={{ background: i % 2 ? color : `${color}99` }} />
      ))}
    </span>
  );
}

function useInvestigationId(fallback?: string) {
  const path = usePathname() || "";
  const [q, setQ] = useState("");
  useEffect(() => {
    setQ(queryId(window.location.search));
  }, [path]);
  return q || segmentId(path, "investigations") || fallback || "";
}

export function InvestigationRoom({ initialId }: { initialId?: string }) {
  const id = useInvestigationId(initialId);
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [agents, setAgents] = useState<Array<{ id: string; role: string; tb: string; room: string }>>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(target: string) {
    try {
      const [b, a] = await Promise.all([api.investigation(target), api.agents()]);
      setBundle(b);
      setAgents(a.agents);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  useEffect(() => {
    if (id) void load(id);
  }, [id]);

  const active = useMemo(() => {
    if (!bundle) return new Set<string>();
    return new Set(bundle.timeline.map((t) => t.actor));
  }, [bundle]);

  if (err) return <ErrorState message={err} />;
  if (!id || !bundle) return <Loading label="Opening incident room" />;

  const hyp = bundle.hypotheses[0];
  const action = bundle.actions[0];
  const outcome = bundle.outcomes[0];
  const voice = bundle.evidence.find((e) => e.source_type === "customer_voice");

  async function decide(decision: "approve" | "deny") {
    if (!action) return;
    setBusy(true);
    try {
      await api.approve(action.id, decision);
      await load(id);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[220px_minmax(0,1fr)_320px]">
      <aside className="space-y-3">
        <p className="font-mono text-[11px] uppercase tracking-widest text-slate-500">Room roster</p>
        {agents.map((a) => (
          <div key={a.id} className="flex items-start gap-2 rounded-lg border border-border/70 bg-card/60 px-2 py-2">
            <Pixel name={a.id} />
            <div className="min-w-0">
              <p className="truncate font-mono text-[11px]">{a.id}</p>
              <p className="text-[11px] text-slate-500">{a.tb}</p>
              <p className={`text-[10px] ${active.has(a.id) ? "text-accent" : "text-slate-600"}`}>
                {active.has(a.id) ? "worked this room" : "standby"}
              </p>
            </div>
          </div>
        ))}
      </aside>

      <section className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-xs text-slate-500">{bundle.investigation.id}</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {hyp?.statement ?? "Agents are still gathering"}
            </h1>
            <p className="mt-2 text-sm text-slate-400">
              Graph and chat for this incident.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {action ? <Badge tone={action.risk_tier === "HIGH" ? "high" : "warn"}>{action.risk_tier}</Badge> : null}
            <Badge tone={bundle.investigation.state === "AWAITING_APPROVAL" ? "warn" : "ok"}>
              {bundle.investigation.state}
            </Badge>
          </div>
        </div>

        {action?.status === "awaiting_approval" ? (
          <Card className="border-amber-500/30">
            <p className="text-sm font-medium">What happens if you approve</p>
            <p className="mt-2 text-sm text-slate-300">{action.consequence}</p>
            <p className="mt-2 text-xs text-slate-500">{action.tier_rationale}</p>
            <div className="mt-4 flex gap-2">
              <Button disabled={busy} onClick={() => void decide("approve")}>
                Approve rollback
              </Button>
              <Button variant="ghost" disabled={busy} onClick={() => void decide("deny")}>
                Deny
              </Button>
            </div>
          </Card>
        ) : null}

        <Card className="max-h-[28rem] overflow-y-auto">
          <p className="font-mono text-[11px] uppercase text-slate-500">Agent chat</p>
          <ol className="mt-4 space-y-3">
            {bundle.timeline.map((t) => (
              <li key={t.id} className="flex gap-3">
                <Pixel name={t.actor} size={12} />
                <div className="min-w-0">
                  <p className="text-sm">
                    <span className="font-mono text-[11px] text-slate-500">{t.actor}</span>{" "}
                    {t.title}
                    {t.denial ? <span className="ml-2 text-red-400">denied</span> : null}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">{t.detail}</p>
                  <p className="mt-1 font-mono text-[10px] text-slate-600">{when(t.at)}</p>
                </div>
              </li>
            ))}
          </ol>
        </Card>

        {voice ? (
          <Card>
            <p className="font-mono text-[11px] uppercase text-slate-500">Customer voice · structured</p>
            <p className="mt-2 text-sm text-slate-300">{voice.claim}</p>
            <p className="mt-2 font-mono text-[11px] text-slate-500">{voice.source_reference}</p>
          </Card>
        ) : null}

        {outcome ? (
          <Card className="shadow-glow">
            <p className="font-mono text-[11px] uppercase text-slate-500">Verification</p>
            <p className="mt-2 text-lg">{String(outcome.verdict)}</p>
            <p className="mt-1 font-mono text-sm text-slate-400">
              {String(outcome.metric || "Metric")} {pct(Number(outcome.pre_value))} → {pct(Number(outcome.post_value))}
            </p>
            {bundle.lessons[0] ? (
              <p className="mt-3 text-sm text-slate-300">{String(bundle.lessons[0].statement)}</p>
            ) : null}
          </Card>
        ) : null}
      </section>

      <aside className="space-y-4">
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Evidence graph</p>
          <div className="mt-3">
            <EvidenceGraph evidence={bundle.evidence} hypotheses={bundle.hypotheses} />
          </div>
        </Card>
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Provenance</p>
          <div className="mt-3 space-y-3">
            {bundle.evidence.map((e) => (
              <div key={e.id} className="border-l-2 border-accent/40 pl-3">
                <div className="flex items-center gap-2">
                  <Pixel name={e.collected_by} />
                  <p className="text-sm">{e.source_type}</p>
                  <Badge tone={e.trust_level === "untrusted" ? "danger" : "muted"}>{e.trust_level}</Badge>
                </div>
                <p className="mt-1 text-xs text-slate-400">{e.claim}</p>
              </div>
            ))}
          </div>
        </Card>
        {bundle.verdicts.length > 0 ? (
          <Card>
            <p className="font-mono text-[11px] uppercase text-slate-500">Policy denials</p>
            {bundle.verdicts.map((v) => (
              <p key={String(v.id)} className="mt-2 text-xs text-red-300">
                {String(v.tool)} · {String(v.verdict)}. {String(v.rationale)}
              </p>
            ))}
          </Card>
        ) : null}
      </aside>
    </div>
  );
}
