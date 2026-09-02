"use client";

import { useEffect, useMemo, useState } from "react";
import type { Action, Bundle, Room, RoomMessage } from "@/lib/api";
import { api } from "@/lib/api";
import { pct } from "@/lib/utils";
import { Button } from "@/components/ui";
import { AgentBadge } from "@/components/agent-badge";
import { ProofEmbed, ProofGrid, type ProofPayload } from "@/components/proof-embed";
import { proofsFromRoom, metricSparkFromProof } from "@/lib/collect-proofs";
import { FlowConnector } from "./flow-connector";
import { MIcon } from "./icon";

function SparkFromProof({ proof, highlightFrom }: { proof?: ProofPayload | null; highlightFrom?: number }) {
  const values = metricSparkFromProof(proof);
  if (!values.length) {
    return (
      <div className="mt-stack-md flex h-48 w-full items-center justify-center rounded border border-outline-variant bg-surface-container">
        <ProofEmbed proof={proof} className="w-full max-w-md" compact />
      </div>
    );
  }
  const max = Math.max(...values, 1);
  return (
    <div className="relative z-10 mt-stack-md flex h-48 w-full items-end gap-1 rounded border border-outline-variant bg-surface-container px-2 pb-2">
      {values.map((v, i) => {
        const hot = highlightFrom !== undefined && i >= highlightFrom;
        return (
          <div
            key={i}
            className={`w-full rounded-t-sm ${hot ? "bg-error/80 shadow-[0_0_8px_rgba(186,26,26,0.35)]" : "bg-primary/20"}`}
            style={{ height: `${Math.max(12, (v / max) * 100)}%` }}
          />
        );
      })}
    </div>
  );
}

function EvidenceTable({ rows, cols }: { rows: Array<Record<string, unknown>>; cols: string[] }) {
  if (!cols.length || !rows.length) {
    return <p className="text-body-sm text-on-surface-variant">No warehouse rows yet — agents query BigQuery as they investigate.</p>;
  }
  return (
    <div className="overflow-hidden rounded border border-outline-variant">
      <table className="w-full border-collapse text-left">
        <thead className="bg-surface-container-low font-label-caps uppercase text-on-surface-variant">
          <tr>
            {cols.map((c) => (
              <th key={c} className="border-b border-outline-variant p-2">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="font-mono text-code-sm text-on-surface">
          {rows.slice(0, 6).map((row, i) => (
            <tr key={i} className="border-b border-outline-variant bg-error-container/5">
              {cols.map((c) => (
                <td key={c} className="p-2">
                  {String(row[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Port of ui/.../investigation_reasoning_lab_1/code.html — signal → understand → fix
 * with live GA4 / BQ / GitHub embeds (not mock text).
 */
export function InvestigationLab({
  room,
  messages,
  bundle,
  pending,
  busy,
  onDecide,
}: {
  room: Room;
  messages: RoomMessage[];
  bundle: Bundle | null;
  pending: Action[];
  busy: boolean;
  onDecide: (actionId: string, d: "approve" | "deny") => void;
}) {
  const [globalProof, setGlobalProof] = useState<{
    ga4?: ProofPayload | null;
    warehouse?: ProofPayload | null;
    github?: ProofPayload | null;
    cards?: ProofPayload[];
  }>({});

  useEffect(() => {
    api
      .proof()
      .then((pf) =>
        setGlobalProof({
          ga4: (pf.ga4 as ProofPayload) || null,
          warehouse: (pf.warehouse as ProofPayload) || null,
          github: (pf.github as ProofPayload) || null,
          cards: ((pf.cards || []) as ProofPayload[]).filter((c) => c?.kind),
        })
      )
      .catch(() => undefined);
  }, []);

  const roomProofs = useMemo(() => proofsFromRoom(messages, bundle), [messages, bundle]);
  const ga4 =
    roomProofs.find((p) => p.kind === "ga4") ||
    globalProof.ga4 ||
    globalProof.cards?.find((c) => c.kind === "ga4");
  const warehouse =
    roomProofs.find((p) => p.kind === "warehouse" || p.kind === "bq") ||
    globalProof.warehouse ||
    globalProof.cards?.find((c) => c.kind === "warehouse");
  const github =
    roomProofs.find((p) => p.kind === "github") ||
    globalProof.github ||
    globalProof.cards?.find((c) => c.kind === "github");

  const signal = bundle?.signals?.[0] as Record<string, unknown> | undefined;
  const hyp = bundle?.hypotheses?.[0];
  const action = pending[0] || bundle?.actions?.[0];
  const outcome = bundle?.outcomes?.[0];
  const magnitude = signal?.magnitude != null ? Number(signal.magnitude) : null;

  const bqCols = warehouse?.columns?.length ? warehouse.columns : ["segment", "metric", "value"];
  const bqRows =
    warehouse?.rows?.length
      ? warehouse.rows
      : bundle?.evidence?.slice(0, 4).map((e) => ({
          segment: e.independence_group,
          metric: e.source_type,
          value: e.claim,
        })) || [];

  const timeline = bundle?.timeline || [];
  const handoffs = bundle?.agent_calls || [];

  return (
    <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto bg-background p-container-padding">
      <div className="mb-stack-lg border-b border-outline-variant pb-stack-md">
        <div className="mb-unit flex flex-wrap items-center gap-stack-sm">
          {action?.risk_tier === "HIGH" ? (
            <span className="flex items-center gap-1 rounded bg-error-container px-2 py-0.5 text-label-caps uppercase tracking-widest text-on-error-container">
              <MIcon name="priority_high" className="text-[14px]" />
              {action.risk_tier} gate
            </span>
          ) : null}
          {bundle?.investigation?.id ? (
            <span className="font-mono text-code-sm text-on-surface-variant">
              Mission {bundle.investigation.id.slice(0, 12)}
            </span>
          ) : null}
        </div>
        <h1 className="mb-stack-sm text-display-lg text-primary">{room.title}</h1>
        {hyp?.statement || room.topic ? (
          <p className="text-body-lg text-on-surface-variant">{hyp?.statement || room.topic}</p>
        ) : null}
      </div>

      <div className="grid grid-cols-12 gap-stack-md">
        <div className="col-span-12 flex flex-col gap-stack-md lg:col-span-8">
          {/* Signal card — reference HTML */}
          <div className="group relative overflow-hidden rounded-lg border border-outline-variant bg-surface-container-lowest p-container-padding shadow-sm transition-colors hover:bg-[#EEF2FF]">
            <div className="relative z-10 mb-stack-sm flex items-start justify-between">
              <div>
                <h2 className="flex items-center gap-unit text-headline-md">
                  <MIcon name="sensors" className="text-secondary" />
                  Signal: {String(signal?.metric || "anomaly").replace(/_/g, " ")}
                </h2>
                <p className="mt-1 flex items-center gap-1 text-body-sm text-on-surface-variant">
                  <MIcon name="bar_chart" className="text-[16px]" />
                  Source: Google Analytics · checkout funnel
                </p>
              </div>
              {magnitude != null && !Number.isNaN(magnitude) ? (
                <span className="rounded bg-error-container/50 px-2 py-1 font-mono text-code-sm text-error">
                  {pct(magnitude)} vs baseline
                </span>
              ) : null}
            </div>
            <SparkFromProof proof={ga4} highlightFrom={Math.max(0, metricSparkFromProof(ga4).length - 4)} />
            {ga4 ? (
              <div className="relative z-10 mt-3">
                <ProofEmbed proof={ga4} compact className="mt-0" />
              </div>
            ) : null}
          </div>

          <FlowConnector />

          {/* Understand — BigQuery embedding */}
          <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-container-padding shadow-sm transition-colors hover:bg-[#EEF2FF]">
            <div className="mb-stack-md flex items-start justify-between">
              <div>
                <h2 className="flex items-center gap-unit text-headline-md">
                  <MIcon name="analytics" className="text-secondary" />
                  Understand: evidence cohort
                </h2>
                <p className="mt-1 flex items-center gap-1 text-body-sm text-on-surface-variant">
                  <MIcon name="database" className="text-[16px]" />
                  Source: BigQuery · tenant warehouse
                </p>
              </div>
              {warehouse?.console_url ? (
                <a
                  href={warehouse.console_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 font-mono text-code-sm text-secondary hover:underline"
                >
                  View query <MIcon name="open_in_new" className="text-[14px]" />
                </a>
              ) : null}
            </div>
            <EvidenceTable rows={bqRows} cols={bqCols} />
            {warehouse ? <ProofEmbed proof={warehouse} compact className="mt-3" /> : null}
            {hyp ? (
              <p className="mt-stack-sm text-body-sm text-on-surface-variant">
                Confidence {Math.round((hyp.confidence || 0) * 100)}% · {hyp.statement}
              </p>
            ) : null}
          </div>

          <FlowConnector />

          {/* Fix proposed — GitHub */}
          <div className="relative rounded-lg border border-outline-variant bg-surface-container-lowest p-container-padding shadow-sm ring-1 ring-secondary/30">
            <div className="mb-stack-md flex items-start justify-between">
              <div>
                <h2 className="flex items-center gap-unit text-headline-md">
                  <MIcon name="build" className="text-secondary" />
                  Fix proposed
                </h2>
                <p className="mt-1 flex items-center gap-1 text-body-sm text-on-surface-variant">
                  <MIcon name="code" className="text-[16px]" />
                  Source: GitHub · {action?.tenant_repo || "tenant repo"}
                </p>
              </div>
              <span className="flex items-center gap-1 rounded border border-[#E2E8F0] bg-[#EEF2FF] px-2 py-1 text-label-caps">
                <span className="h-2 w-2 rounded-full bg-secondary" />
                {action?.status === "executed" ? "Applied" : "Ready for review"}
              </span>
            </div>
            {github ? (
              <ProofEmbed proof={github} className="mt-0" />
            ) : (
              <p className="text-body-sm text-on-surface-variant">No PR yet — code agent opens one after approval.</p>
            )}
            {action && ["proposed", "awaiting_approval"].includes(action.status) ? (
              <div className="mt-stack-md flex justify-end gap-stack-sm">
                <Button variant="outline" disabled={busy} onClick={() => onDecide(action.id, "deny")}>
                  Reject &amp; re-prompt
                </Button>
                <Button disabled={busy} onClick={() => onDecide(action.id, "approve")}>
                  <MIcon name="rocket_launch" className="mr-1 text-[18px]" />
                  Approve
                </Button>
              </div>
            ) : null}
            {action?.consequence ? (
              <p className="mt-3 text-body-sm text-on-surface-variant">{action.consequence}</p>
            ) : null}
          </div>
        </div>

        {/* Right rail — reasoning + tools touched (not message inbox) */}
        <div className="col-span-12 flex flex-col gap-stack-md lg:col-span-4">
          <div className="flex h-[420px] flex-col rounded-lg border border-outline-variant bg-surface-container-lowest shadow-sm">
            <div className="rounded-t-lg border-b border-outline-variant bg-surface-container-low p-3">
              <h3 className="flex items-center gap-unit text-headline-sm">
                <MIcon name="psychology" className="text-secondary" />
                Agent reasoning trail
              </h3>
            </div>
            <div className="custom-scrollbar flex flex-1 flex-col gap-3 overflow-y-auto p-3 font-mono text-code-sm">
              {timeline.length === 0 ? (
                <p className="text-on-surface-variant">Timeline fills as agents work.</p>
              ) : (
                timeline.map((t, i) => (
                  <div key={t.id} className="flex gap-2">
                    <div className="flex flex-col items-center">
                      <div
                        className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold ${
                          i === timeline.length - 1
                            ? "bg-secondary text-white"
                            : "bg-secondary-container text-on-secondary-container"
                        }`}
                      >
                        {i + 1}
                      </div>
                      {i < timeline.length - 1 ? <div className="my-1 w-px flex-1 bg-outline-variant" /> : null}
                    </div>
                    <div className="pb-2">
                      <div className="font-bold text-on-surface">{t.title}</div>
                      <div className="mt-1 text-on-surface-variant">{t.detail}</div>
                      <div className="mt-1 text-[10px] text-outline">{t.actor}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-3 shadow-sm">
            <h3 className="mb-2 flex items-center gap-unit text-headline-sm">
              <MIcon name="hub" className="text-secondary" />
              Tools in this mission
            </h3>
            <ProofGrid cards={[ga4, warehouse, github, ...roomProofs].filter(Boolean)} compact className="grid-cols-1" />
          </div>

          {handoffs.length > 0 ? (
            <div className="rounded-lg border border-outline-variant bg-surface-container-lowest p-3 shadow-sm">
              <h3 className="mb-2 flex items-center gap-unit text-headline-sm">
                <MIcon name="swap_horiz" className="text-secondary" />
                Agent handoffs
              </h3>
              <ul className="space-y-2">
                {handoffs.slice(-4).map((h) => (
                  <li
                    key={String(h.id)}
                    className="flex items-start gap-2 rounded border border-outline-variant/60 bg-surface p-2"
                  >
                    <AgentBadge name={String(h.from_agent || "orchestrator")} size={22} variant="face" />
                    <div className="min-w-0 text-body-sm">
                      <span className="font-mono text-[10px] text-outline">
                        {String(h.from_agent)} → {String(h.to_agent)}
                      </span>
                      <p className="text-on-surface">{String(h.summary)}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {outcome ? (
            <div className="rounded-lg border border-outline-variant border-l-4 border-l-[#0F172A] bg-surface-container-lowest p-3 shadow-sm">
              <h3 className="mb-2 flex items-center gap-unit text-headline-sm">
                <MIcon name="verified" className="text-secondary" />
                Verification
              </h3>
              <p className="text-body-sm font-semibold text-on-surface">{String(outcome.verdict)}</p>
              <p className="mt-1 font-mono text-code-sm text-on-surface-variant">
                {String(outcome.metric)} {pct(Number(outcome.pre_value))} → {pct(Number(outcome.post_value))}
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
