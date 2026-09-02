"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Phone } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { api, roomSocket, type Action, type RoomDetail, type RoomMessage } from "@/lib/api";
import { queryId, segmentId } from "@/lib/route-id";
import { cn } from "@/lib/utils";
import { Button, ErrorState, Loading } from "@/components/ui";
import { AgentBadge } from "@/components/agent-badge";
import { ProofEmbed, proofFromArtifact } from "@/components/proof-embed";
import { proofsFromRoom } from "@/lib/collect-proofs";
import { RoomCaseBanner } from "@/components/room-case-banner";
import { EvidenceGraph } from "@/components/evidence-graph";
import { ProofGrid } from "@/components/proof-embed";
import { InvestigationLab } from "@/components/ref/investigation-lab";
import { ThreadRoomHeader, WorkChatThread, type ChatThreadEvent } from "@/components/work-chat-thread";

function useRoomId(fallback?: string) {
  const path = usePathname() || "";
  const [q, setQ] = useState("");
  useEffect(() => {
    setQ(queryId(window.location.search));
  }, [path]);
  return q || segmentId(path, "rooms") || fallback || "";
}

function eventsFromRoom(data: RoomDetail): ChatThreadEvent[] {
  const rows: ChatThreadEvent[] = [];
  for (const msg of data.messages) {
    if (msg.kind === "system" || msg.author === "system") {
      rows.push({ kind: "system", id: msg.id, at: msg.created_at, text: msg.text });
      continue;
    }
    rows.push({
      kind: "chat",
      id: msg.id,
      at: msg.created_at,
      author: msg.author,
      author_kind: msg.author_kind,
      text: msg.text,
      artifact_type: msg.artifact_type,
      artifact: msg.artifact || {},
      msg_kind: msg.kind,
    });
  }
  for (const call of data.bundle?.agent_calls ?? []) {
    rows.push({
      kind: "handoff",
      id: String(call.id ?? `${call.from_agent}-${call.to_agent}-${call.started_at}`),
      at: String(call.started_at ?? data.room.created_at),
      from_agent: String(call.from_agent ?? ""),
      to_agent: String(call.to_agent ?? ""),
      summary: String(call.summary ?? ""),
    });
  }
  return rows.sort((a, b) => a.at.localeCompare(b.at));
}

function Gate({
  action,
  busy,
  onDecide,
}: {
  action: Action;
  busy: boolean;
  onDecide: (d: "approve" | "deny") => void;
}) {
  const execution = (action.artifacts?.execution ?? {}) as {
    pr_url?: string;
    flag?: string;
    value?: string;
    proof?: Record<string, unknown>;
  };
  if (action.status === "executed") {
    const proof =
      proofFromArtifact(
        {
          ...(execution.proof || {}),
          pr_url: execution.pr_url,
          url: execution.pr_url,
          proof: execution.proof,
        },
        "pr"
      ) ||
      (execution.pr_url
        ? proofFromArtifact({ pr_url: execution.pr_url, url: execution.pr_url, state: "open" }, "pr")
        : null);
    return (
      <div className="mx-auto my-2 max-w-md fade-in">
        {proof ? (
          <ProofEmbed proof={proof} compact className="mt-0" />
        ) : execution.pr_url ? (
          <a href={execution.pr_url} className="inline-block text-[13px] text-accent" target="_blank" rel="noreferrer">
            Open PR →
          </a>
        ) : (
          <p className="text-[13px] text-[var(--dim)]">Done.</p>
        )}
      </div>
    );
  }
  if (!["proposed", "awaiting_approval"].includes(action.status)) return null;
  return (
    <div className="mx-auto my-2 max-w-md rounded-2xl border border-border bg-white px-4 py-3 shadow-sm">
      <p className="text-[14px] font-medium">Needs your OK</p>
      {action.consequence ? (
        <p className="mt-1 text-[13px] leading-5 text-[var(--dim)]">{action.consequence}</p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button onClick={() => onDecide("approve")} disabled={busy}>
          {busy ? "…" : "Approve"}
        </Button>
        <Button variant="ghost" onClick={() => onDecide("deny")} disabled={busy}>
          Not yet
        </Button>
      </div>
    </div>
  );
}

/** Live room — messenger chat (same chrome as the old Traces view). */
export function RoomView({ initialId }: { initialId?: string }) {
  const id = useRoomId(initialId);
  const searchParams = useSearchParams();
  const viewParam = searchParams?.get("view");
  const [tab, setTab] = useState<"chat" | "lab">(viewParam === "lab" ? "lab" : "chat");
  const [data, setData] = useState<RoomDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [callPhone, setCallPhone] = useState("");
  const [callNote, setCallNote] = useState<string | null>(null);
  const [contactOnFile, setContactOnFile] = useState<{
    phone?: string | null;
    email?: string | null;
    found: boolean;
    detail?: string;
    feedback?: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [livePresence, setLivePresence] = useState<Record<string, string>>({});
  const [toolsOpen, setToolsOpen] = useState(false);
  const gateRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  async function load(target: string) {
    try {
      const d = await api.room(target);
      setData(d);
      const p: Record<string, string> = {};
      for (const row of d.presence ?? []) p[row.agentId] = row.status;
      setLivePresence(p);
      setErr(null);
      try {
        const contact = await api.roomContact(target);
        setContactOnFile(contact);
        if (contact.found && contact.phone) {
          setCallPhone((prev) => prev || contact.phone || "");
        }
      } catch {
        setContactOnFile(null);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  useEffect(() => {
    if (!id) return;
    setData(null);
    setErr(null);
    setToolsOpen(false);
    void load(id);
  }, [id]);

  useEffect(() => {
    if (viewParam === "lab") setTab("lab");
  }, [viewParam]);

  useEffect(() => {
    if (!id) return;
    let ws: WebSocket | null = null;
    try {
      ws = roomSocket(id);
      ws.onmessage = (ev) => {
        try {
          const e = JSON.parse(ev.data);
          if (e.type === "agent_presence" && e.agentId) {
            setLivePresence((prev) => ({ ...prev, [e.agentId]: e.status || "thinking" }));
          }
          if (e.type === "message" && e.message) {
            setData((r) =>
              r
                ? {
                    ...r,
                    messages: [...r.messages, e.message as RoomMessage],
                  }
                : r,
            );
          }
          if (e.type === "artifact" && e.artifact) {
            const art = e.artifact as {
              text?: string;
              kind?: string;
              payload?: Record<string, unknown>;
              id?: string;
              author?: string;
              author_kind?: string;
              created_at?: string;
            };
            setData((r) => {
              if (!r) return r;
              const msg: RoomMessage = {
                id: String(art.id ?? `live-${Date.now()}`),
                room_id: id,
                author: String(art.author || "code_agent"),
                author_kind: (art.author_kind as RoomMessage["author_kind"]) || "agent",
                kind: "artifact",
                text: String(art.text ?? art.kind ?? "artifact"),
                artifact_type: String(art.kind ?? "note"),
                artifact: (art.payload as Record<string, unknown>) ?? {},
                created_at: art.created_at || new Date().toISOString(),
              };
              if (r.messages.some((m) => m.id === msg.id)) return r;
              return { ...r, messages: [...r.messages, msg] };
            });
          }
          if (e.type === "approval_required" || e.type === "approval_resolved") {
            void load(id);
            window.requestAnimationFrame(() => {
              gateRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
            });
          }
          if (e.type === "a2a") {
            const env = (e.envelope ?? {}) as Record<string, unknown>;
            const payload = (env.payload ?? {}) as Record<string, unknown>;
            const from = String(e.from ?? env.from_agent ?? "");
            const to = String(e.to ?? env.to_agent ?? "");
            const summary = String(e.summary ?? payload.summary ?? "handed off");
            if (from || to) {
              setData((r) => {
                if (!r?.bundle) return r;
                const call = {
                  id: `live-a2a-${Date.now()}`,
                  from_agent: from,
                  to_agent: to,
                  summary,
                  started_at: new Date().toISOString(),
                };
                return {
                  ...r,
                  bundle: {
                    ...r.bundle,
                    agent_calls: [...(r.bundle.agent_calls ?? []), call],
                  },
                };
              });
              if (to) setLivePresence((prev) => ({ ...prev, [to]: "thinking" }));
            }
          }
          if (e.type === "funnel_stage" && e.stage) {
            const stage = String(e.stage);
            setData((r) => {
              if (!r?.funnel) return r;
              const steps = r.funnel.steps.map((s, i, arr) => {
                const cur = arr.findIndex((x) => x.id === stage);
                return { ...s, on: cur >= 0 ? i <= cur : s.on };
              });
              return { ...r, funnel: { ...r.funnel, current: stage, steps } };
            });
            if (e.agentId) {
              setLivePresence((prev) => ({ ...prev, [String(e.agentId)]: "thinking" }));
            }
          }
          if (e.type === "agent_callback" && e.agentId) {
            setLivePresence((prev) => ({ ...prev, [String(e.agentId)]: String(e.status || "speaking") }));
          }
        } catch {
          /* ignore */
        }
      };
    } catch {
      /* runtime down */
    }
    return () => ws?.close();
  }, [id]);

  const events = useMemo(() => (data ? eventsFromRoom(data) : []), [data]);
  const roomProofs = useMemo(
    () => (data ? proofsFromRoom(data.messages, data.bundle) : []),
    [data]
  );
  const showEvidence = Boolean(data?.bundle?.evidence?.length);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  if (err) return <ErrorState message={err} />;
  if (!id || !data) return <Loading label="Opening chat" />;

  const pending = data.bundle?.actions ?? [];
  const needsApproval = pending.some((a) => ["proposed", "awaiting_approval"].includes(a.status));
  const members = (data.room.members || []).filter((m) => m !== "system" && m !== "you");
  const live = Object.entries(livePresence).some(([, st]) => st && st !== "idle");

  async function send() {
    if (!text.trim()) return;
    setBusy(true);
    try {
      setData(await api.postRoom(id, text.trim()));
      setText("");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  async function decide(actionId: string, decision: "approve" | "deny") {
    setBusy(true);
    try {
      await api.approve(actionId, decision);
      if (decision === "approve") {
        for (let i = 0; i < 24; i++) {
          const st = await api.approvalStatus(actionId);
          const url = st.pr_url || (st.execution?.pr_url as string | undefined);
          if (url || st.status === "executed" || st.job?.status === "done") break;
          await new Promise((r) => window.setTimeout(r, 500));
        }
      }
      await load(id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  async function callCustomer() {
    setBusy(true);
    setCallNote(null);
    try {
      const out = await api.placeCall({
        to_number: callPhone.trim() || undefined,
        reason: data?.room.topic || data?.room.title || "customer follow-up",
        room_id: id,
        product: data?.tenant?.product || "Product",
        force: true,
      });
      if (out.to_number) setCallPhone(out.to_number);
      if (out.resolved?.found) {
        setContactOnFile({
          found: true,
          phone: out.resolved.phone,
          detail: out.resolved.detail,
          feedback: out.resolved.feedback,
        });
        setCallNote(out.resolved.detail || out.report.detail);
      } else {
        setCallNote(out.report.detail);
      }
      await load(id);
    } catch (e) {
      setCallNote(e instanceof Error ? e.message : "Call failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-[#f0f0f2] fade-in">
      <div className="shrink-0 border-b border-black/5 bg-white px-4 py-3 sm:px-6">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <ThreadRoomHeader title={data.room.title} members={members} />
            {members.length > 0 ? (
              <div className="mt-2 flex items-center gap-2">
                <div className="flex -space-x-1.5">
                  {members.slice(0, 7).map((mid) => (
                    <AgentBadge key={mid} name={mid} size={24} variant="face" className="ring-2 ring-white" />
                  ))}
                </div>
                {live ? <span className="text-[11px] font-medium text-accent">live</span> : null}
              </div>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-1.5">
            <div className="mr-1 flex rounded-full bg-[var(--elev)] p-0.5">
              <button
                type="button"
                onClick={() => setTab("chat")}
                className={cn(
                  "rounded-full px-3 py-1 text-[11px] font-medium transition-colors",
                  tab === "chat" ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)]"
                )}
              >
                Chat
              </button>
              <button
                type="button"
                onClick={() => setTab("lab")}
                className={cn(
                  "rounded-full px-3 py-1 text-[11px] font-medium transition-colors",
                  tab === "lab" ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)]"
                )}
              >
                Transparency
              </button>
            </div>
            {needsApproval ? (
              <button
                type="button"
                onClick={() => gateRef.current?.scrollIntoView({ behavior: "smooth", block: "center" })}
                className="rounded-full bg-[var(--elev)] px-2.5 py-1 text-[11px] font-medium text-accent hover:bg-accent/10"
              >
                Review
              </button>
            ) : null}
            <button
              type="button"
              aria-label={toolsOpen ? "Close call options" : "Call customer"}
              aria-expanded={toolsOpen}
              onClick={() => setToolsOpen((o) => !o)}
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full text-[var(--faint)] transition-colors hover:bg-[var(--elev)] hover:text-foreground",
                toolsOpen && "bg-[var(--elev)] text-foreground",
              )}
            >
              <Phone className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>
        </div>

        {toolsOpen ? (
          <div className="mt-3 max-w-lg space-y-2 rounded-2xl bg-[var(--elev)] px-3 py-3">
            <p className="text-[12px] text-[var(--dim)]">
              {contactOnFile?.found
                ? `Contact on file${contactOnFile.email ? ` · ${contactOnFile.email}` : ""}${
                    contactOnFile.phone ? ` · ${contactOnFile.phone}` : ""
                  }. Mail first; call only non-responders.`
                : "No contact yet — capture email at registration or phone on feedback."}
            </p>
            <div className="flex flex-wrap items-end gap-2">
              <label className="min-w-[10rem] flex-1 text-[11px] text-[var(--faint)]">
                Phone
                <input
                  className="mt-1 w-full rounded-xl border border-border bg-white px-3 py-2 text-[14px] outline-none focus:border-accent"
                  value={callPhone}
                  onChange={(e) => setCallPhone(e.target.value)}
                  placeholder={contactOnFile?.phone || "+1…"}
                  inputMode="tel"
                />
              </label>
              <Button type="button" onClick={() => void callCustomer()} disabled={busy}>
                {busy ? "…" : "Call"}
              </Button>
            </div>
            {callNote ? <p className="text-[12px] text-[var(--dim)]">{callNote}</p> : null}
          </div>
        ) : null}
      </div>

      {tab === "lab" ? (
        <InvestigationLab
          room={data.room}
          messages={data.messages}
          bundle={data.bundle}
          pending={pending.filter((a) => ["proposed", "awaiting_approval"].includes(a.status))}
          busy={busy}
          onDecide={(actionId, d) => void decide(actionId, d)}
        />
      ) : (
        <>
          <div className="chat-scroll min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6 lg:px-8">
            <RoomCaseBanner room={data.room} bundle={data.bundle} />
            {showEvidence ? (
              <details className="mb-4 group rounded-2xl border border-border bg-white">
                <summary className="cursor-pointer list-none px-4 py-3 text-[13px] font-medium text-[var(--dim)]">
                  Evidence graph
                  <span className="ml-2 text-[12px] font-normal text-[var(--faint)] group-open:hidden">show</span>
                </summary>
                <div className="border-t border-border px-3 pb-3">
                  <EvidenceGraph
                    evidence={data.bundle?.evidence ?? []}
                    hypotheses={data.bundle?.hypotheses ?? []}
                  />
                </div>
              </details>
            ) : null}
            {roomProofs.length > 0 ? (
              <div className="mb-4">
                <ProofGrid cards={roomProofs} compact className="grid-cols-1 sm:grid-cols-2" />
              </div>
            ) : null}
            <WorkChatThread
              events={events}
              variant="group"
              empty="Nothing yet — agents will talk through this here."
            />
            <div ref={gateRef}>
              {pending.map((action) => (
                <Gate key={action.id} action={action} busy={busy} onDecide={(d) => void decide(action.id, d)} />
              ))}
            </div>
            <div ref={bottomRef} />
          </div>

          <form
            className="shrink-0 border-t border-black/5 bg-white px-4 py-2.5 sm:px-6"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Message"
              disabled={busy}
              className="max-w-3xl rounded-full bg-[#ebebed] px-3.5 py-2.5 text-[13px] text-foreground outline-none placeholder:text-[var(--faint)] focus:ring-2 focus:ring-accent/20 disabled:opacity-60"
            />
          </form>
        </>
      )}
    </div>
  );
}
