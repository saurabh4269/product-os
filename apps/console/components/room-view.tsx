"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type Action, type RoomDetail, type RoomMessage } from "@/lib/api";
import { shortName } from "@/lib/names";
import { when } from "@/lib/utils";
import { Button, ErrorState, Loading } from "@/components/ui";
import { PixelOffice, PixelSprite } from "@/components/pixel-office";
import { RoomHandoff } from "@/components/office-floor";

function useRoomId(fallback?: string) {
  const [id, setId] = useState(fallback ?? "");
  useEffect(() => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const last = parts[parts.length - 1];
    if (last && last !== "rooms" && last !== "_") setId(last);
    const q = new URLSearchParams(window.location.search).get("id");
    if (q) setId(q);
  }, []);
  return id;
}

function Artifact({ msg }: { msg: RoomMessage }) {
  const type = (msg.artifact_type ?? "note").replace(/_/g, " ");
  return (
    <div className="mt-2 max-w-[620px] rounded-xl bg-[var(--elev)] px-4 py-3">
      <p className="text-[12px] font-medium capitalize text-[var(--faint)]">{type}</p>
      <p className="mt-1 text-[14px] leading-6 text-[var(--ink)]">{msg.text}</p>
    </div>
  );
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
  if (!["proposed", "awaiting_approval"].includes(action.status)) return null;
  return (
    <div className="my-5 max-w-[620px] rounded-2xl border border-border bg-[var(--elev)] p-5">
      <p className="text-[13px] text-[var(--dim)]">Needs a look · {action.risk_tier}</p>
      <p className="mt-2 text-[16px] font-semibold leading-6 tracking-tight">This change is waiting on you</p>
      <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">{action.consequence}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={() => onDecide("approve")} disabled={busy}>
          Approve
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

  async function load(target: string) {
    try {
      setData(await api.room(target));
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  useEffect(() => {
    if (id) void load(id);
  }, [id]);

  const working = useMemo(() => {
    const set = new Set<string>();
    if (!data) return set;
    for (const m of data.messages.slice(-8)) set.add(m.author);
    for (const call of data.bundle?.agent_calls ?? []) {
      set.add(String(call.to_agent ?? ""));
      set.add(String(call.from_agent ?? ""));
    }
    return set;
  }, [data]);

  const activity = useMemo(() => {
    const map: Record<string, string> = {};
    if (!data) return map;
    for (const call of data.bundle?.agent_calls ?? []) {
      const to = String(call.to_agent ?? "");
      if (to) map[to] = String(call.summary ?? "working");
    }
    for (const m of data.messages) {
      if (m.author && m.author !== "system") map[m.author] = m.text;
    }
    return map;
  }, [data]);

  const thread = useMemo(() => {
    if (!data) return [] as Array<{ key: string; at: string; kind: "msg" | "handoff"; msg?: RoomMessage; handoff?: Record<string, unknown> }>;
    const rows: Array<{ key: string; at: string; kind: "msg" | "handoff"; msg?: RoomMessage; handoff?: Record<string, unknown> }> = [];
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
    } finally {
      setBusy(false);
    }
  }

  async function decide(actionId: string, decision: "approve" | "deny") {
    setBusy(true);
    try {
      await api.approve(actionId, decision);
      await load(id);
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
      </div>

      <div className="mx-5 overflow-hidden rounded-[20px] border border-border sm:mx-8 lg:mx-12">
        <PixelOffice members={data.room.members} working={working} activity={activity} />
      </div>

      {recalled.length ? (
        <div className="mx-5 mt-4 rounded-2xl bg-[var(--elev)] px-5 py-4 sm:mx-8 lg:mx-12">
          <p className="text-[12px] text-[var(--faint)]">From last time</p>
          <p className="mt-1 text-[14px] leading-6 text-[var(--ink)]">{recalled[0]}</p>
        </div>
      ) : null}

      <div className="chat-scroll flex-1 space-y-1 overflow-y-auto px-5 py-6 sm:px-8 lg:px-12">
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
                </div>
              )}
              <div className="pl-10">
                {msg.kind === "artifact" ? (
                  <Artifact msg={msg} />
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
      </div>

      <form
        className="border-t border-border px-5 py-3 sm:px-8 lg:px-12"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Message the room"
          className="h-12 w-full rounded-full bg-[var(--elev)] px-5 text-[15px] outline-none placeholder:text-[var(--faint)] focus:ring-2 focus:ring-accent/25"
        />
      </form>
    </div>
  );
}
