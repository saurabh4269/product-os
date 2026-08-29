"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type Action, type RoomDetail, type RoomMessage } from "@/lib/api";
import { shortName } from "@/lib/names";
import { when } from "@/lib/utils";
import { Button, ErrorState, Loading } from "@/components/ui";
import { PixelOffice, PixelSprite } from "@/components/pixel-office";

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

function artifactTone(type: string) {
  if (type === "risk_decision") return "var(--warn)";
  if (type === "memory_card") return "var(--ok)";
  if (type === "hypothesis" || type === "prd" || type === "experiment_design") return "var(--accent)";
  if (type === "evidence") return "var(--accent-2)";
  return "var(--dim)";
}

function Artifact({ msg }: { msg: RoomMessage }) {
  const type = (msg.artifact_type ?? "note").replace(/_/g, " ");
  return (
    <div className="mt-2 max-w-[640px] border-l-2 pl-4" style={{ borderColor: artifactTone(msg.artifact_type ?? "") }}>
      <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--faint)]">{type}</p>
      <p className="mt-1 text-[15px] leading-6 text-[var(--ink)]">{msg.text}</p>
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
    <div className="hard-shadow my-4 max-w-[640px] border border-[var(--warn)] bg-[var(--paper)] p-5">
      <p className="text-[11px] uppercase tracking-[0.16em] text-warn">
        {action.risk_tier} gate
      </p>
      <p className="font-display mt-2 text-[26px] leading-8">This change needs you.</p>
      <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">{action.consequence}</p>
      <div className="mt-4 flex gap-2">
        <Button onClick={() => onDecide("approve")} disabled={busy}>
          Approve
        </Button>
        <Button variant="ghost" onClick={() => onDecide("deny")} disabled={busy}>
          Hold
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
    <div className="flex h-full min-h-0 flex-col">
      <div className="px-8 pb-4 pt-7 lg:px-12">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--faint)]">
          {data.room.kind}
          {data.room.loop_type === "type_a" ? " · something broke" : data.room.loop_type === "type_b" ? " · something could be better" : ""}
        </p>
        <h1 className="font-display mt-2 max-w-3xl text-[40px] leading-[1.1] tracking-tight">{data.room.title}</h1>
        <p className="mt-2 max-w-2xl text-[15px] leading-6 text-[var(--dim)]">{data.room.topic}</p>
      </div>

      <PixelOffice members={data.room.members} working={working} />

      {recalled.length ? (
        <div className="border-b border-border px-8 py-3 lg:px-12">
          <p className="text-[11px] uppercase tracking-[0.16em] text-ok">Remembered</p>
          <p className="mt-1 max-w-2xl text-[14px] leading-6 text-[var(--ink)]/90">{recalled[0]}</p>
        </div>
      ) : null}

      <div className="chat-scroll flex-1 space-y-1 overflow-y-auto px-8 py-6 lg:px-12">
        {data.messages.map((msg) => {
          const repeat = msg.author === lastAuthor;
          lastAuthor = msg.author;
          return (
            <div key={msg.id} className={repeat ? "pt-1" : "pt-5"}>
              {repeat ? null : (
                <div className="mb-1 flex items-center gap-2">
                  <PixelSprite name={msg.author} scale={2} />
                  <span className="text-[14px] font-medium">{shortName(msg.author)}</span>
                  <span className="text-[11px] text-[var(--faint)]">{when(msg.created_at)}</span>
                </div>
              )}
              <div className={repeat ? "pl-10" : "pl-10"}>
                {msg.kind === "artifact" ? <Artifact msg={msg} /> : (
                  <p className="max-w-[640px] text-[15px] leading-6 text-[var(--ink)]/92">{msg.text}</p>
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
        className="border-t border-border px-8 py-4 lg:px-12"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write in the room"
          className="h-12 w-full bg-transparent text-[16px] outline-none placeholder:text-[var(--faint)]"
        />
      </form>
    </div>
  );
}
