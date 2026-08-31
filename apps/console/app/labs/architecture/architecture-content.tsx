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
import { SevenStepLoop } from "@/components/seven-step-loop";

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
        <h1 className="mt-1 text-[28px] font-semibold tracking-tight sm:text-[32px]">Three layers + five planes</h1>
        <p className="mt-3 text-[15px] leading-6 text-[var(--dim)]">
          Tier A user flow · Tier B tenant wire · Tier C fleet &amp; governance. Highlights sync with the live pipeline
          when a demo is running.
        </p>
        {stage ? (
          <p className="mt-3 rounded-xl border border-accent/25 bg-[color-mix(in_srgb,var(--accent)_6%,white)] px-3 py-2 text-[13px] text-accent">
            Live: <strong>{stage.replace(/_/g, " ")}</strong> —{" "}
            <Link href="/" className="underline">
              pipeline board
            </Link>
          </p>
        ) : null}
      </header>

      <ArchitectureTabs tab={tab} onTab={pickTab} className="mt-8" />

      {tab === "overview" ? (
        <div className="mt-8 space-y-10">
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Tier B · Tenant wire</h2>
            <p className="mt-2 max-w-xl text-[14px] text-[var(--dim)]">
              Product Y on their origin — signals and flags through Connect — outcomes to GitHub, flags, Calendar.
            </p>
            <div className="mt-4 overflow-x-auto rounded-2xl border border-border bg-white p-4">
              <TenantWireDiagram />
            </div>
            <p className="mt-3 text-[13px] text-[var(--faint)]">
              <Link href="/connect" className="text-accent hover:underline">
                Connect desk
              </Link>{" "}
              · configure repo, deploy URL, warehouse
            </p>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">System hub</h2>
            <p className="mt-2 max-w-xl text-[14px] text-[var(--dim)]">
              Console ↔ LoopEngine ↔ optional ADK worker. WebSocket pushes agent_callback events back to the UI.
            </p>
            <div className="mt-4">
              <SystemHubDiagram />
            </div>
            <div className="mt-4">
              <MermaidDiagram source={SYSTEM_HUB} />
            </div>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Signal sources</h2>
            <SignalSourcesDiagram />
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
            <p className="mt-2 text-[14px] text-[var(--dim)]">Reactive triggers beyond “user clicked Run”.</p>
            <div className="mt-4">
              <EventPathsDiagram />
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
              />
            </div>
            <div className="mt-4">
              <WorkflowDetailPanel workflows={workflows} />
            </div>
          </section>
          <section>
            <h2 className="text-[20px] font-semibold tracking-tight">Trust boundaries × agents</h2>
            <p className="mt-2 text-[14px] text-[var(--dim)]">Seven TBs from PRD §7.2 — generated from registry.</p>
            <div className="mt-4 rounded-2xl border border-border bg-white p-4">
              <TrustBoundariesDiagram agents={agents} />
            </div>
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
