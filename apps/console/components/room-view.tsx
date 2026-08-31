"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { HandoffPacket } from "@/components/handoff-packet";
import { api, roomSocket, type Action, type RoomDetail, type RoomMessage } from "@/lib/api";
import { shortName } from "@/lib/names";
import { queryId, segmentId } from "@/lib/route-id";
import { when, cn } from "@/lib/utils";
import { Button, ErrorState, Loading } from "@/components/ui";
import { WorkFlipbook } from "@/components/work-flipbook";
import { pagesFromRoom } from "@/lib/work-pages";
import { FunnelChips } from "@/components/funnel-chips";
import { ArtifactCard } from "@/components/artifact-card";
import { ChatBubble, RoomAgentRail } from "@/components/room-chat";

function useRoomId(fallback?: string) {
  const path = usePathname() || "";
  const [q, setQ] = useState("");
  useEffect(() => {
    setQ(queryId(window.location.search));
  }, [path]);
  return q || segmentId(path, "rooms") || fallback || "";
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
  const execution = (action.artifacts?.execution ?? {}) as { pr_url?: string; flag?: string; value?: string };
  if (action.status === "executed") {
    return (
      <div className="my-5 max-w-[620px] rounded-2xl border border-border bg-[var(--elev)] p-5">
        <p className="text-[13px] text-[var(--dim)]">Done</p>
        <p className="mt-2 text-[16px] font-semibold leading-6 tracking-tight">This change already ran</p>
        {execution.flag ? (
          <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">
            {execution.flag} is {String(execution.value ?? "updated")}.
          </p>
        ) : null}
        {execution.pr_url ? (
          <p className="mt-2 text-[14px]">
            <a href={execution.pr_url} className="text-accent" target="_blank" rel="noreferrer">
              Open the pull request
            </a>
          </p>
        ) : null}
      </div>
    );
  }
  if (!["proposed", "awaiting_approval"].includes(action.status)) return null;
  return (
    <div className="my-5 max-w-[620px] rounded-2xl border border-border bg-[var(--elev)] p-5">
      <p className="text-[13px] text-[var(--dim)]">Needs a look · {action.risk_tier}</p>
      <p className="mt-2 text-[16px] font-semibold leading-6 tracking-tight">This change is waiting on you</p>
      <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">{action.consequence}</p>
      {action.gate ? <p className="mt-2 text-[13px] leading-5 text-[var(--dim)]">{action.gate}</p> : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={() => onDecide("approve")} disabled={busy}>
          {busy ? "Working…" : "Approve"}
        </Button>
        <Button variant="ghost" onClick={() => onDecide("deny")} disabled={busy}>
          Not yet
        </Button>
      </div>
    </div>
  );
}

export function RoomView({ initialId }: { initialId?: string }) {
  const id = useRoomId(initialId);
  const [data, setData] = useState<RoomDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [callPhone, setCallPhone] = useState("");
  const [callNote, setCallNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"work" | "transcript">("transcript");
  const [livePresence, setLivePresence] = useState<Record<string, string>>({});
  const [freshHandoff, setFreshHandoff] = useState<string | null>(null);
  const [seenMsgIds, setSeenMsgIds] = useState<Set<string>>(new Set());
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const [toolsOpen, setToolsOpen] = useState(false);
  const gateRef = useRef<HTMLDivElement | null>(null);

  async function load(target: string) {
    try {
      const d = await api.room(target);
      setData(d);
      const p: Record<string, string> = {};
      for (const row of d.presence ?? []) p[row.agentId] = row.status;
      setLivePresence(p);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  useEffect(() => {
    if (!id) return;
    setData(null);
    setErr(null);
    void load(id);
  }, [id]);

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
            const msg = e.message as RoomMessage;
            setSeenMsgIds((prev) => new Set(prev).add(msg.id));
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
            const art = e.artifact as { text?: string; kind?: string; payload?: Record<string, unknown>; id?: string };
            setData((r) => {
              if (!r) return r;
              const msg: RoomMessage = {
                id: String(art.id ?? `live-${Date.now()}`),
                room_id: id,
                author: "orchestrator",
                author_kind: "agent",
                kind: "artifact",
                text: String(art.text ?? art.kind ?? "artifact"),
                artifact_type: String(art.kind ?? "note"),
                artifact: (art.payload as Record<string, unknown>) ?? {},
                created_at: new Date().toISOString(),
              };
              return { ...r, messages: [...r.messages, msg] };
            });
          }
          if (e.type === "approval_required" || e.type === "approval_resolved") {
            setTab("work");
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
              const key = `${from}-${to}-${Date.now()}`;
              setFreshHandoff(key);
              window.setTimeout(() => setFreshHandoff(null), 800);
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
              if (to) {
                setLivePresence((prev) => ({ ...prev, [to]: "thinking" }));
              }
            }
          }
          if (e.type === "trace") {
            const step = (e.step ?? {}) as { agentId?: string; denial?: boolean };
            if (step.agentId) {
              setLivePresence((prev) => ({
                ...prev,
                [String(step.agentId)]: step.denial ? "idle" : "tool",
              }));
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
          /* ignore bad frames */
        }
      };
    } catch {
      /* runtime down */
    }
    return () => ws?.close();
  }, [id]);

  const working = useMemo(() => {
    const set = new Set<string>();
    if (!data) return set;
    for (const [agent, st] of Object.entries(livePresence)) {
      if (st && st !== "idle") set.add(agent);
    }
    for (const m of data.messages.slice(-8)) set.add(m.author);
    for (const call of data.bundle?.agent_calls ?? []) {
      set.add(String(call.to_agent ?? ""));
      set.add(String(call.from_agent ?? ""));
    }
    return set;
  }, [data, livePresence]);

  const activity = useMemo(() => {
    const map: Record<string, string> = {};
    if (!data) return map;
    for (const call of data.bundle?.agent_calls ?? []) {
      const to = String(call.to_agent ?? "");
      if (to) map[to] = String(call.summary ?? "working");
    }
    for (const [agent, st] of Object.entries(livePresence)) {
      if (st && st !== "idle") map[agent] = st;
    }
    for (const m of data.messages) {
      if (m.author && m.author !== "system") map[m.author] = m.text;
    }
    return map;
  }, [data, livePresence]);

  const thread = useMemo(() => {
    if (!data)
      return [] as Array<{
        key: string;
        at: string;
        kind: "msg" | "handoff";
        msg?: RoomMessage;
        handoff?: Record<string, unknown>;
      }>;
    const rows: Array<{
      key: string;
      at: string;
      kind: "msg" | "handoff";
      msg?: RoomMessage;
      handoff?: Record<string, unknown>;
    }> = [];
    for (const msg of data.messages) {
      rows.push({ key: msg.id, at: msg.created_at, kind: "msg", msg });
    }
    for (const call of data.bundle?.agent_calls ?? []) {
      rows.push({
        key: String(call.id ?? `${call.from_agent}-${call.to_agent}-${call.started_at}`),
        at: String(call.started_at ?? data.room.created_at),
        kind: "handoff",
        handoff: call,
      });
    }
    return rows.sort((a, b) => a.at.localeCompare(b.at));
  }, [data]);

  const artifacts = useMemo(
    () => (data?.messages ?? []).filter((m) => m.kind === "artifact"),
    [data],
  );

  if (err) return <ErrorState message={err} />;
  if (!id || !data) return <Loading label="Opening the room" />;

  const pending = data.bundle?.actions ?? [];
  const needsApproval = pending.some((a) => ["proposed", "awaiting_approval"].includes(a.status));
  const recalled = data.bundle?.investigation.recalled_lessons ?? [];
  const latestMsgId = data.messages.length ? data.messages[data.messages.length - 1]?.id : "";

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
    if (!callPhone.trim()) {
      setCallNote("Add a phone number first.");
      return;
    }
    setBusy(true);
    setCallNote(null);
    try {
      const out = await api.placeCall({
        to_number: callPhone.trim(),
        reason: data?.room.topic || data?.room.title || "customer follow-up",
        room_id: id,
        product: data?.tenant?.product || "Product",
      });
      setCallNote(out.report.detail);
      await load(id);
    } catch (e) {
      setCallNote(e instanceof Error ? e.message : "Call failed");
    } finally {
      setBusy(false);
    }
  }

  let lastAuthor = "";

  const members = data.room.members.filter((m) => m !== "system");
  const filteredThread = filterAgent
    ? thread.filter((row) => {
        if (row.kind === "handoff" && row.handoff) {
          const from = String(row.handoff.from_agent ?? "");
          const to = String(row.handoff.to_agent ?? "");
          return from === filterAgent || to === filterAgent;
        }
        return row.msg?.author === filterAgent;
      })
    : thread;

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--bg)]">
      <div className="flex items-start justify-between gap-3 border-b border-border bg-white px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <Link href="/" className="text-[12px] text-[var(--faint)] hover:text-foreground">
            ← Campus
          </Link>
          <h1 className="mt-1 truncate text-[18px] font-semibold tracking-tight sm:text-[20px]">{data.room.title}</h1>
          {data.funnel ? (
            <div className="mt-2">
              <FunnelChips steps={data.funnel.steps} current={data.funnel.current} presence={livePresence} />
            </div>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => setToolsOpen((o) => !o)}
            className="rounded-full border border-border px-3 py-1.5 text-[12px] font-medium text-[var(--dim)] hover:bg-[var(--elev)]"
          >
            Tools
          </button>
          {needsApproval ? (
            <button
              type="button"
              onClick={() => {
                setTab("work");
                gateRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
              }}
              className="rounded-full bg-accent px-3 py-1.5 text-[12px] font-medium text-white"
            >
              Approve
            </button>
          ) : null}
        </div>
      </div>

      {toolsOpen ? (
        <div className="border-b border-border bg-white px-4 py-3 sm:px-6">
          <div className="flex max-w-md flex-wrap items-end gap-2">
            <label className="min-w-[10rem] flex-1 text-[11px] text-[var(--faint)]">
              Call customer
              <input
                className="mt-1 w-full rounded-xl border border-border bg-white px-3 py-2 text-[14px] outline-none focus:border-accent"
                value={callPhone}
                onChange={(e) => setCallPhone(e.target.value)}
                placeholder="+1…"
                inputMode="tel"
              />
            </label>
            <Button type="button" onClick={() => void callCustomer()} disabled={busy}>
              {busy ? "…" : "Call"}
            </Button>
          </div>
          {callNote ? <p className="mt-2 text-[12px] text-[var(--dim)]">{callNote}</p> : null}
        </div>
      ) : null}

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <RoomAgentRail
          members={data.room.members}
          working={working}
          presence={livePresence}
          activity={activity}
          picked={filterAgent}
          onPick={setFilterAgent}
        />

        <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-white lg:bg-[var(--bg)]">
          <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2 sm:px-5">
            <div className="flex rounded-full border border-border bg-[var(--elev)] p-0.5 text-[12px]">
              <button
                type="button"
                className={cn(
                  "rounded-full px-3 py-1 font-medium",
                  tab === "transcript" ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)]"
                )}
                onClick={() => setTab("transcript")}
              >
                Chat
              </button>
              <button
                type="button"
                className={cn(
                  "rounded-full px-3 py-1 font-medium",
                  tab === "work" ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)]"
                )}
                onClick={() => setTab("work")}
              >
                Work
              </button>
            </div>
            {filterAgent ? (
              <button
                type="button"
                className="text-[11px] text-accent hover:underline"
                onClick={() => setFilterAgent(null)}
              >
                Clear filter · {shortName(filterAgent)}
              </button>
            ) : (
              <span className="text-[11px] text-[var(--faint)]">{members.length} agents</span>
            )}
          </div>

          <div className="chat-scroll flex-1 space-y-3 overflow-y-auto px-4 py-4 sm:px-5">
            {tab === "work" ? (
              <div ref={gateRef} className="grid gap-3 sm:grid-cols-2">
                {artifacts.map((m) => (
                  <ArtifactCard key={m.id} msg={m} />
                ))}
                {artifacts.length === 0 && !pending.length ? (
                  <p className="text-[13px] text-[var(--faint)]">Evidence lands here as agents work.</p>
                ) : null}
                {pending.map((action) => (
                  <Gate key={action.id} action={action} busy={busy} onDecide={(d) => void decide(action.id, d)} />
                ))}
                {data.bundle ? (
                  <div className="sm:col-span-2">
                    <WorkFlipbook
                      pages={pagesFromRoom(data.room, [], data).filter((p) => !p.id.endsWith("-open"))}
                    />
                  </div>
                ) : null}
                {recalled.length ? (
                  <div className="rounded-2xl bg-[var(--elev)] px-4 py-3 sm:col-span-2">
                    <p className="text-[11px] text-[var(--faint)]">Memory</p>
                    <p className="mt-1 text-[13px] leading-5">{recalled[0]}</p>
                  </div>
                ) : null}
              </div>
            ) : (
              <>
                {filteredThread.length === 0 ? (
                  <p className="py-8 text-center text-[13px] text-[var(--faint)]">Waiting for the fleet…</p>
                ) : null}
                {filteredThread.map((row) => {
                  if (row.kind === "handoff" && row.handoff) {
                    lastAuthor = "";
                    const hk = row.key;
                    return (
                      <HandoffPacket
                        key={hk}
                        from={String(row.handoff.from_agent ?? "")}
                        to={String(row.handoff.to_agent ?? "")}
                        summary={String(row.handoff.summary ?? "")}
                        at={when(row.at)}
                        fresh={freshHandoff !== null && hk.includes(String(row.handoff.to_agent ?? ""))}
                      />
                    );
                  }
                  const msg = row.msg;
                  if (!msg) return null;
                  const isYou = msg.author === "you" || msg.author_kind === "human";
                  const repeat = msg.author === lastAuthor;
                  lastAuthor = msg.author;
                  const href = msg.author_kind === "agent" ? `/agents/${msg.author}` : null;
                  if (msg.kind === "artifact") {
                    return (
                      <div key={msg.id} className="max-w-md">
                        <ArtifactCard msg={msg} />
                      </div>
                    );
                  }
                  if (repeat) {
                    return (
                      <div key={msg.id} className={cn("flex", isYou ? "justify-end pr-0" : "justify-start pl-9")}>
                        <ChatBubble
                          author={msg.author}
                          text={msg.text}
                          isYou={isYou}
                          compact
                          live={
                            msg.id === latestMsgId &&
                            msg.author_kind === "agent" &&
                            (seenMsgIds.has(msg.id) || Boolean(livePresence[msg.author]))
                          }
                          href={href}
                        />
                      </div>
                    );
                  }
                  return (
                    <div key={msg.id}>
                      <div className={cn("mb-1 flex items-center gap-2", isYou && "justify-end")}>
                        {!isYou && href ? (
                          <Link href={href} className="text-[12px] font-medium hover:text-accent">
                            {shortName(msg.author)}
                          </Link>
                        ) : !isYou ? (
                          <span className="text-[12px] font-medium">{shortName(msg.author)}</span>
                        ) : (
                          <span className="text-[12px] font-medium text-[var(--faint)]">You</span>
                        )}
                        {livePresence[msg.author] && livePresence[msg.author] !== "idle" ? (
                          <span className="text-[10px] text-accent">{livePresence[msg.author]}</span>
                        ) : null}
                      </div>
                      <div className={cn("flex", isYou ? "justify-end" : "justify-start")}>
                        <ChatBubble
                          author={msg.author}
                          text={msg.text}
                          isYou={isYou}
                          live={
                            msg.id === latestMsgId &&
                            msg.author_kind === "agent" &&
                            (seenMsgIds.has(msg.id) || Boolean(livePresence[msg.author]))
                          }
                          href={href}
                        />
                      </div>
                    </div>
                  );
                })}
                {pending.map((action) => (
                  <Gate key={action.id} action={action} busy={busy} onDecide={(d) => void decide(action.id, d)} />
                ))}
              </>
            )}
          </div>

          <form
            className="flex items-center gap-2 border-t border-border bg-white px-4 py-3 sm:px-5"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Message the room"
              className="h-11 min-w-0 flex-1 rounded-full bg-[var(--elev)] px-4 text-[15px] outline-none placeholder:text-[var(--faint)] focus:ring-2 focus:ring-accent/25"
            />
            <Button type="submit" disabled={busy || !text.trim()}>
              Send
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
