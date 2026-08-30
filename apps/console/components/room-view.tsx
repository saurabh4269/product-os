"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, roomSocket, type Action, type RoomDetail, type RoomMessage } from "@/lib/api";
import { shortName } from "@/lib/names";
import { queryId, segmentId } from "@/lib/route-id";
import { when } from "@/lib/utils";
import { Button, ErrorState, Loading } from "@/components/ui";
import { PixelOffice, PixelSprite } from "@/components/pixel-office";
import { RoomHandoff } from "@/components/office-floor";
import { WorkFlipbook } from "@/components/work-flipbook";
import { pagesFromRoom } from "@/lib/work-pages";
import { FunnelChips } from "@/components/funnel-chips";
import { ArtifactCard } from "@/components/artifact-card";

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
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"work" | "transcript">("work");
  const [livePresence, setLivePresence] = useState<Record<string, string>>({});

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
            void load(id);
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
  const recalled = data.bundle?.investigation.recalled_lessons ?? [];

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
      await load(id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  let lastAuthor = "";

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="px-5 pb-5 pt-6 sm:px-8 lg:px-12 lg:pt-8">
        <Link href="/" className="text-[13px] text-[var(--faint)] hover:text-foreground">
          ← Campus
        </Link>
        <p className="mt-3 text-[13px] text-[var(--faint)]">
          {data.room.kind === "incident" ? "Incident" : data.room.kind === "opportunity" ? "Idea" : "Room"}
        </p>
        <h1 className="mt-1 max-w-2xl text-[26px] font-semibold leading-8 tracking-tight">{data.room.title}</h1>
        <p className="mt-2 max-w-2xl text-[14px] leading-6 text-[var(--dim)]">{data.room.topic}</p>
        {data.funnel ? (
          <div className="mt-4">
            <FunnelChips
              steps={data.funnel.steps}
              current={data.funnel.current}
              presence={livePresence}
            />
          </div>
        ) : null}
      </div>

      <div className="mx-5 overflow-hidden rounded-[20px] border border-border sm:mx-8 lg:mx-12">
        <PixelOffice members={data.room.members} working={working} activity={activity} furniture={false} />
      </div>

      {data.bundle ? (
        <div className="mx-5 mt-4 sm:mx-8 lg:mx-12">
          <WorkFlipbook
            pages={pagesFromRoom(data.room, [], data).filter((p) => !p.id.endsWith("-open"))}
          />
        </div>
      ) : null}

      {recalled.length ? (
        <div className="mx-5 mt-4 rounded-2xl bg-[var(--elev)] px-5 py-4 sm:mx-8 lg:mx-12">
          <p className="text-[12px] text-[var(--faint)]">From last time</p>
          <p className="mt-1 text-[14px] leading-6 text-[var(--ink)]">{recalled[0]}</p>
        </div>
      ) : null}

      <div className="relative mx-5 mt-4 flex w-fit rounded-full border border-border bg-[var(--elev)] p-0.5 sm:mx-8 lg:mx-12">
        <button
          type="button"
          className={
            "rounded-full px-4 py-1.5 text-[13px] font-medium " +
            (tab === "work" ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)]")
          }
          onClick={() => setTab("work")}
        >
          Work
        </button>
        <button
          type="button"
          className={
            "rounded-full px-4 py-1.5 text-[13px] font-medium " +
            (tab === "transcript" ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)]")
          }
          onClick={() => setTab("transcript")}
        >
          Transcript
        </button>
      </div>

      <div className="chat-scroll flex-1 space-y-1 overflow-y-auto px-5 py-6 sm:px-8 lg:px-12">
        {tab === "work" ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {artifacts.map((m) => (
              <ArtifactCard key={m.id} msg={m} />
            ))}
            {artifacts.length === 0 ? (
              <p className="text-[14px] text-[var(--dim)]">No artifacts yet — the fleet posts evidence here.</p>
            ) : null}
            {pending.map((action) => (
              <Gate key={action.id} action={action} busy={busy} onDecide={(d) => void decide(action.id, d)} />
            ))}
          </div>
        ) : (
          <>
            {thread.map((row) => {
              if (row.kind === "handoff" && row.handoff) {
                lastAuthor = "";
                return (
                  <RoomHandoff
                    key={row.key}
                    from={String(row.handoff.from_agent ?? "")}
                    to={String(row.handoff.to_agent ?? "")}
                    summary={String(row.handoff.summary ?? "")}
                    at={when(row.at)}
                  />
                );
              }
              const msg = row.msg;
              if (!msg) return null;
              const repeat = msg.author === lastAuthor;
              lastAuthor = msg.author;
              const href = msg.author_kind === "agent" ? `/agents/${msg.author}` : null;
              return (
                <div key={msg.id} className={repeat ? "pt-1" : "pt-4"}>
                  {repeat ? null : (
                    <div className="mb-1 flex items-center gap-2">
                      {href ? (
                        <Link href={href} className="flex items-center gap-2 hover:opacity-80">
                          <PixelSprite name={msg.author} scale={2} />
                          <span className="text-[14px] font-medium">{shortName(msg.author)}</span>
                        </Link>
                      ) : (
                        <>
                          <PixelSprite name={msg.author} scale={2} />
                          <span className="text-[14px] font-medium">{shortName(msg.author)}</span>
                        </>
                      )}
                      <span className="text-[12px] text-[var(--faint)]">{when(msg.created_at)}</span>
                      {livePresence[msg.author] && livePresence[msg.author] !== "idle" ? (
                        <span className="text-[11px] text-accent">{livePresence[msg.author]}</span>
                      ) : null}
                    </div>
                  )}
                  <div className="pl-10">
                    {msg.kind === "artifact" ? (
                      <ArtifactCard msg={msg} />
                    ) : (
                      <p className="max-w-[620px] text-[14px] leading-6 text-[var(--ink)]">{msg.text}</p>
                    )}
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
        className="flex items-center gap-2 border-t border-border px-5 py-3 sm:px-8 lg:px-12"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Message the room"
          className="h-12 min-w-0 flex-1 rounded-full bg-[var(--elev)] px-5 text-[15px] outline-none placeholder:text-[var(--faint)] focus:ring-2 focus:ring-accent/25"
        />
        <Button type="submit" disabled={busy || !text.trim()}>
          Send
        </Button>
      </form>
    </div>
  );
}
