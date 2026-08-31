"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  FIVE_PLANES,
  HITL_GATES,
  INVESTIGATION_FANOUT,
  PRODUCT_FLOW,
  SIGNAL_SOURCES,
  SYSTEM_HUB,
  withHighlight,
} from "@/lib/diagram-definitions";
import { STAGE_NODE_IDS, usePipelineHighlight } from "@/lib/pipeline-highlight";
import { ArchifyEmbed } from "@/components/archify-embed";
import { ArchitectureTabs, type ArchTab } from "@/components/diagrams/architecture-tabs";
import { MermaidDiagram } from "@/components/diagrams/mermaid-diagram";
import { FleetSwimlanes, SignalSourcesDiagram } from "@/components/diagrams/signal-sources-diagram";
import {
  EventPathsDiagram,
  HybridEngineDiagram,
  InvestigationFanoutDiagram,
  SystemHubDiagram,
  WorkflowDetailPanel,
} from "@/components/diagrams/system-hub-diagram";
import { TenantWireDiagram } from "@/components/diagrams/tenant-wire-diagram";
import { TrustBoundariesDiagram } from "@/components/diagrams/trust-boundaries-diagram";
import { DiagramDetailPanel } from "@/components/diagrams/diagram-detail-panel";
import { SevenStepLoop } from "@/components/seven-step-loop";

const LANE_DETAILS: Record<string, { body: string; adk: string }> = {
  Detect: { body: "Signal agent reads webhooks and warehouse anomalies. It does not investigate alone.", adk: "Detect opens a room" },
  Investigate: { body: "Investigators work in parallel and post findings to the room.", adk: "Workflow + JoinNode" },
  Decide: { body: "Evidence from at least 3 independent sources. Root cause agent writes the call.", adk: "Merge · confidence" },
  Act: { body: "Bug path: code and test. Feature path: product and experiment.", adk: "Type A / B" },
  Govern: { body: "High risk waits for your approval. OAuth for side effects.", adk: "HITL" },
  Verify: { body: "Learning agent watches the metric and writes a lesson.", adk: "Metric → memory" },
};

const TB_DETAILS: Record<string, string> = {
  "TB-0": "Exfil is denied by Gateway identity, not by a prompt.",
  "TB-1": "Orchestration merge, evidence groups, approval gate.",
  "TB-2": "Warehouse and logs. Read only.",
  "TB-3": "Customer voice with redaction.",
  "TB-4": "Code clone, test, PR. No auto-merge.",
  "TB-5": "Product specs, calendar drafts, coordination.",
  "TB-6": "Pct rollout experiments with guardrails.",
  "TB-7": "Post-ship verification and lessons.",
};

function parseTab(raw: string | null): ArchTab {
  if (raw === "loop" || raw === "fleet" || raw === "deep") return raw;
  return "overview";
}

export default function ArchitectureContent() {
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<ArchTab>(() => parseTab(searchParams.get("tab")));
  const stage = usePipelineHighlight();
  const [agents, setAgents] = useState<Array<{ id: string; room: string; role: string; tb?: string }>>([]);
  const [workflows, setWorkflows] = useState<Awaited<ReturnType<typeof api.workflows>> | null>(null);
  const [fleetLane, setFleetLane] = useState<string | null>(null);
  const [trustTb, setTrustTb] = useState<string | null>(null);
  const [signalSide, setSignalSide] = useState<"push" | "pull" | null>(null);
  const [eventPath, setEventPath] = useState<string | null>(null);
  const [signalProofs, setSignalProofs] = useState<Array<Record<string, unknown>>>([]);
  const [fleetProofs, setFleetProofs] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    setTab(parseTab(searchParams.get("tab")));
  }, [searchParams]);

  useEffect(() => {
    Promise.all([api.agents(), api.workflows()])
      .then(([a, w]) => {
        setAgents(a.agents);
        setWorkflows(w);
      })
      .catch(() => {
        setAgents([]);
        setWorkflows(null);
      });
  }, []);

  useEffect(() => {
    if (!signalSide) {
      setSignalProofs([]);
      return;
    }
    let cancelled = false;
    api
      .proofResources({ signal: signalSide })
      .then((r) => {
        if (!cancelled) setSignalProofs(r.cards || []);
      })
      .catch(() => {
        if (!cancelled) setSignalProofs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [signalSide]);

  useEffect(() => {
    const laneAgent: Record<string, string> = {
      Detect: "signal_agent",
      Investigate: "investigator_agent",
      Decide: "root_cause_agent",
      Act: "code_agent",
      Govern: "security_policy_agent",
      Verify: "learning_agent",
    };
    const agent = fleetLane ? laneAgent[fleetLane] : "";
    if (!agent) {
      setFleetProofs([]);
      return;
    }
    let cancelled = false;
    api
      .proofResources({ agent })
      .then((r) => {
        if (!cancelled) setFleetProofs(r.cards || []);
      })
      .catch(() => {
        if (!cancelled) setFleetProofs([]);
      });
    return () => {
      cancelled = true;
    };
  }, [fleetLane]);

  const flowSrc = useMemo(
    () => withHighlight(PRODUCT_FLOW, stage, stage ? STAGE_NODE_IDS[stage] || [] : []),
    [stage]
  );
  const planesSrc = useMemo(() => {
    const ids = stage ? [...(STAGE_NODE_IDS[stage] || [])] : [];
    if (stage === "approve") ids.push("hitl_gate", "stage_approve", "s6");
    if (stage === "reviews") ids.push("deny", "reviews");
    return withHighlight(FIVE_PLANES, stage, ids);
  }, [stage]);

  function pickTab(next: ArchTab) {
    setTab(next);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", next);
      window.history.replaceState(null, "", url.pathname + url.search);
    }
  }

  return (
    <div className="page-pad mx-auto max-w-5xl">
      <Link href="/labs" className="text-[13px] text-[var(--faint)] hover:text-foreground">
        ← Labs
      </Link>
      <header className="mt-6 max-w-2xl">
        <p className="text-[13px] text-[var(--faint)]">Architecture</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-tight sm:text-[32px]">How it fits together</h1>
        {stage ? (
          <p className="mt-3 rounded-xl border border-accent/25 bg-[color-mix(in_srgb,var(--accent)_6%,white)] px-3 py-2 text-[13px] text-accent">
            {stage.replace(/_/g, " ")} ·{" "}
            <Link href="/" className="underline">
              pipeline
            </Link>
          </p>
        ) : null}
      </header>

      <ArchitectureTabs tab={tab} onTab={pickTab} className="mt-8" />

      {tab === "overview" ? (
        <div className="mt-8 space-y-10">
          <ArchifyEmbed hero defaultDiagram="system" />
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Tenant wire</h2>
            <div className="mt-4 overflow-x-auto rounded-2xl border border-border bg-white p-4">
              <TenantWireDiagram />
            </div>
            <p className="mt-3 text-[13px] text-[var(--faint)]">
              <Link href="/connect" className="text-accent hover:underline">
                Connect
              </Link>
            </p>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">System hub</h2>
            <div className="mt-4">
              <SystemHubDiagram />
            </div>
            <div className="mt-4">
              <MermaidDiagram source={SYSTEM_HUB} />
            </div>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Signal sources</h2>
            <SignalSourcesDiagram selected={signalSide} onSelect={setSignalSide} />
            {signalSide ? (
              <DiagramDetailPanel
                className="mt-3"
                title={signalSide === "push" ? "Push" : "Pull"}
                subtitle={signalSide === "push" ? "Tenant initiates" : "OS reads facts"}
                body={
                  signalSide === "push"
                    ? "Webhooks from Product Y: checkout hangs, voice, feedback."
                    : "Warehouse pull: GA4 to BigQuery. Investigators query metrics."
                }
                proofs={signalProofs as never}
                onClear={() => setSignalSide(null)}
              />
            ) : null}
            <div className="mt-4">
              <MermaidDiagram source={SIGNAL_SOURCES} title="Push + pull + live callback paths" />
            </div>
          </section>
        </div>
      ) : null}

      {tab === "loop" ? (
        <div className="mt-8 space-y-10">
          <SevenStepLoop activeStage={stage} />
          <section>
            <MermaidDiagram source={flowSrc} title="Seven-step loop with HITL, OAuth, and DENY gates" />
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Event paths</h2>
            <div className="mt-4">
              <EventPathsDiagram selected={eventPath} onSelect={setEventPath} />
            </div>
          </section>
          <section>
            <MermaidDiagram source={HITL_GATES} title="Human-in-the-loop and hard denies" />
          </section>
        </div>
      ) : null}

      {tab === "fleet" ? (
        <div className="mt-8 space-y-10">
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Functional swimlanes</h2>
            <p className="mt-2 text-[14px] text-[var(--dim)]">Detect → Investigate → Decide → Act → Govern → Verify</p>
            <div className="mt-4">
              <FleetSwimlanes
                agents={agents}
                workflows={
                  workflows
                    ? {
                        investigation_fanout: workflows.investigation_fanout,
                        proposal_critique: workflows.proposal_critique,
                        investigators_fanout: workflows.investigators_fanout,
                      }
                    : null
                }
                selected={fleetLane}
                onSelect={setFleetLane}
              />
            </div>
            {fleetLane && LANE_DETAILS[fleetLane] ? (
              <DiagramDetailPanel
                className="mt-3"
                title={fleetLane}
                subtitle="Functional lane"
                body={LANE_DETAILS[fleetLane].body}
                meta={[{ label: "ADK 2", value: LANE_DETAILS[fleetLane].adk }]}
                proofs={fleetProofs as never}
                onClear={() => setFleetLane(null)}
              />
            ) : null}
            <div className="mt-4">
              <WorkflowDetailPanel workflows={workflows} />
            </div>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Trust boundaries</h2>
            <div className="mt-4 rounded-2xl border border-border bg-white p-4">
              <TrustBoundariesDiagram agents={agents} selected={trustTb} onSelect={setTrustTb} />
            </div>
            {trustTb && TB_DETAILS[trustTb] ? (
              <DiagramDetailPanel
                className="mt-3"
                title={trustTb}
                subtitle="Trust boundary"
                body={TB_DETAILS[trustTb]}
                onClear={() => setTrustTb(null)}
              />
            ) : null}
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Investigation fan-out</h2>
            <InvestigationFanoutDiagram />
            <div className="mt-4">
              <MermaidDiagram source={INVESTIGATION_FANOUT} />
            </div>
          </section>
        </div>
      ) : null}

      {tab === "deep" ? (
        <div className="mt-8 space-y-10">
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Five planes + Product Y</h2>
            <div className="mt-4">
              <MermaidDiagram source={planesSrc} />
            </div>
            <p className="mt-3 text-[13px] text-[var(--faint)]">
              <a href="/docs/architecture.svg" className="text-accent hover:underline">
                Light SVG export
              </a>{" "}
              ·{" "}
              <a
                href="https://github.com/saurabh4269/product-os/blob/main/docs/architecture.mmd"
                className="text-accent hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                architecture.mmd
              </a>
            </p>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Hybrid engine</h2>
            <p className="mt-2 text-[14px] text-[var(--dim)]">
              Hosted loop runs deterministic engine; loop-adk optional when Gemini creds exist.
            </p>
            <div className="mt-4">
              <HybridEngineDiagram />
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
