"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type Bundle } from "@/lib/api";
import { pct, when } from "@/lib/utils";
import { Badge, Button, Card, ErrorState, Loading } from "@/components/ui";
import { EvidenceGraph } from "@/components/evidence-graph";

export default function InvestigationPage() {
  const params = useParams<{ id: string }>();
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .investigation(params.id)
      .then((b) => {
        if (!cancelled) setBundle(b);
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "failed");
      });
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  async function reload() {
    try {
      setBundle(await api.investigation(params.id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  if (err) return <ErrorState message={err} />;
  if (!bundle) return <Loading label="Reconstructing investigation" />;

  const hyp = bundle.hypotheses[0];
  const action = bundle.actions[0];
  const outcome = bundle.outcomes[0];

  async function decide(decision: "approve" | "deny") {
    if (!action) return;
    setBusy(true);
    try {
      await api.approve(action.id, decision);
      await reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-slate-500">{bundle.investigation.id}</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            {hyp?.statement ?? "Evidence still arriving"}
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Judge the conclusion from the graph and the timeline — not from a model’s confidence.
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

      <Card>
        <p className="font-mono text-[11px] uppercase text-slate-500">Evidence graph</p>
        <div className="mt-4">
          <EvidenceGraph evidence={bundle.evidence} hypotheses={bundle.hypotheses} />
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Provenance</p>
          <div className="mt-4 space-y-4">
            {bundle.evidence.map((e) => (
              <div key={e.id} className="border-l-2 border-accent/40 pl-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm">{e.source_type}</p>
                  <Badge tone={e.trust_level === "untrusted" ? "danger" : "muted"}>{e.trust_level}</Badge>
                </div>
                <p className="mt-1 text-sm text-slate-300">{e.claim}</p>
                <p className="mt-1 font-mono text-[11px] text-slate-500">{e.source_reference}</p>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Agent timeline</p>
          <ol className="mt-4 space-y-3">
            {bundle.timeline.map((t) => (
              <li key={t.id} className="flex gap-3">
                <span className={`mt-1 h-2 w-2 rounded-full ${t.denial ? "bg-danger" : "bg-accent"}`} />
                <div>
                  <p className="text-sm">
                    {t.title}
                    {t.denial ? <span className="ml-2 text-red-400">denied</span> : null}
                  </p>
                  <p className="text-xs text-slate-500">
                    {t.actor} · {when(t.at)}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">{t.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </Card>
      </div>

      {hyp ? (
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Hypothesis</p>
          <p className="mt-2 text-sm">{hyp.statement}</p>
          <p className="mt-2 font-mono text-xs text-slate-500">
            confidence {pct(hyp.confidence)} · groups {hyp.independence_groups.join(", ")}
          </p>
        </Card>
      ) : null}

      {outcome ? (
        <Card className="shadow-glow">
          <p className="font-mono text-[11px] uppercase text-slate-500">Verification</p>
          <p className="mt-2 text-lg">{String(outcome.verdict)}</p>
          <p className="mt-1 font-mono text-sm text-slate-400">
            Safari conversion {pct(Number(outcome.pre_value))} → {pct(Number(outcome.post_value))}
          </p>
          {bundle.lessons[0] ? (
            <p className="mt-3 text-sm text-slate-300">{String(bundle.lessons[0].statement)}</p>
          ) : null}
        </Card>
      ) : null}

      {bundle.verdicts.length > 0 ? (
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Policy denials</p>
          {bundle.verdicts.map((v) => (
            <p key={String(v.id)} className="mt-2 text-sm text-red-300">
              {String(v.tool)} · {String(v.verdict)} — {String(v.rationale)}
            </p>
          ))}
        </Card>
      ) : null}
    </div>
  );
}
