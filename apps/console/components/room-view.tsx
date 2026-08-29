"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Action, type RoomDetail, type RoomMessage } from "@/lib/api";
import { when } from "@/lib/utils";
import { Badge, Button, ErrorState, Loading } from "@/components/ui";
import { Pixel, PixelOffice } from "@/components/pixel-office";

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
  const type = msg.artifact_type ?? "note";
  const tone =
    type === "risk_decision"
      ? "warn"
      : type === "hypothesis"
        ? "accent"
        : type === "memory_card"
          ? "ok"
          : type === "prd" || type === "experiment_design"
            ? "accent"
            : "muted";
  return (
    <div className="rounded-xl border border-border bg-[#0e0e11] p-3">
      <div className="mb-2 flex items-center gap-2">
        <Badge tone={tone}>{type.replace("_", " ")}</Badge>
        <span className="font-mono text-[10px] text-[var(--dim)]">{msg.author}</span>
      </div>
      <p className="text-sm leading-relaxed">{msg.text}</p>
    </div>
  );
}

function ApprovalCard({
  action,
  onDecide,
  busy,
}: {
  action: Action;
  onDecide: (d: "approve" | "deny") => void;
  busy: boolean;
}) {
  if (!["proposed", "awaiting_approval"].includes(action.status)) return null;
  return (
    <div className="rounded-xl border border-warn/40 bg-warn/5 p-4">
      <div className="flex items-center gap-2">
        <Badge tone={action.risk_tier === "HIGH" ? "high" : "warn"}>{action.risk_tier}</Badge>
        <p className="text-sm font-medium">Risk gate · in-room approval</p>
      </div>
      <p className="mt-2 text-sm text-[var(--dim)]">{action.consequence}</p>
      <div className="mt-3 flex gap-2">
        <Button onClick={() => onDecide("approve")} disabled={busy}>
          Approve
        </Button>
        <Button variant="ghost" onClick={() => onDecide("deny")} disabled={busy}>
          Deny
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
    return set;
  }, [data]);

  if (err) return <div className="p-6"><ErrorState message={err} /></div>;
  if (!id || !data) return <div className="p-6"><Loading label="Opening room" /></div>;

  const pending = data.bundle?.actions ?? [];

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

  return (
    <div className="flex h-full min-h-0">
      <section className="flex min-w-0 flex-1 flex-col">
        <div className="border-b border-border px-5 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-lg font-medium tracking-tight">{data.room.title}</h1>
            <Badge tone={data.room.kind === "incident" ? "danger" : data.room.kind === "opportunity" ? "ok" : "muted"}>
              {data.room.kind}
            </Badge>
            {data.room.loop_type ? <Badge tone="accent">{data.room.loop_type === "type_a" ? "Type A" : "Type B"}</Badge> : null}
            {data.room.path ? <Badge>{data.room.path}</Badge> : null}
          </div>
          <p className="mt-1 text-sm text-[var(--dim)]">{data.room.topic}</p>
        </div>
        <div className="px-5 pt-4">
          <PixelOffice members={data.room.members} working={working} />
        </div>
        <div className="chat-scroll flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {data.messages.map((msg) => (
            <div key={msg.id} className="flex gap-3">
              <div className="mt-1 shrink-0">
                <Pixel name={msg.author} size={14} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-sm font-medium">{msg.author.replace(/_/g, " ")}</span>
                  <span className="font-mono text-[10px] text-[var(--dim)]">{when(msg.created_at)}</span>
                </div>
                {msg.kind === "artifact" ? (
                  <div className="mt-2">
                    <Artifact msg={msg} />
                  </div>
                ) : (
                  <p className="mt-1 text-sm leading-relaxed text-foreground/90">{msg.text}</p>
                )}
              </div>
            </div>
          ))}
          {pending.map((action) => (
            <ApprovalCard key={action.id} action={action} busy={busy} onDecide={(d) => void decide(action.id, d)} />
          ))}
        </div>
        <form
          className="flex gap-2 border-t border-border p-4"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Talk to the room — humans and agents share this thread"
            className="h-10 flex-1 rounded-lg border border-border bg-muted px-3 text-sm outline-none placeholder:text-[var(--dim)] focus:border-accent/50"
          />
          <Button type="submit" disabled={busy || !text.trim()}>
            Send
          </Button>
        </form>
      </section>
      <aside className="hidden w-80 shrink-0 overflow-y-auto border-l border-border bg-[#0c0c0e] p-4 lg:block">
        <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--dim)]">Artifacts</p>
        <div className="mt-3 space-y-2">
          {data.messages
            .filter((m) => m.kind === "artifact")
            .map((m) => (
              <div key={m.id} className="rounded-lg border border-border px-3 py-2">
                <p className="font-mono text-[10px] uppercase text-accent">{m.artifact_type}</p>
                <p className="mt-1 line-clamp-3 text-xs text-[var(--dim)]">{m.text}</p>
              </div>
            ))}
        </div>
        {data.bundle?.investigation.recalled_lessons?.length ? (
          <div className="mt-6">
            <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--dim)]">Recalled memory</p>
            <ul className="mt-2 space-y-2">
              {data.bundle.investigation.recalled_lessons.map((lesson) => (
                <li key={lesson} className="rounded-lg border border-ok/20 bg-ok/5 p-3 text-xs leading-relaxed">
                  {lesson}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </aside>
    </div>
  );
}
