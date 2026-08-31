"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, type AgentDetail, type RoomMessage } from "@/lib/api";
import { canonicalAgentId, shortName } from "@/lib/names";
import { queryId, segmentId } from "@/lib/route-id";
import { ErrorState, Loading } from "@/components/ui";
import { AgentBadge } from "@/components/agent-badge";
import { WorkChatThread, type ChatThreadEvent } from "@/components/work-chat-thread";
import { ProofGrid, type ProofPayload } from "@/components/proof-embed";

export function AgentView() {
  const path = usePathname() || "";
  const [q, setQ] = useState("");
  const [data, setData] = useState<AgentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [filterRoom, setFilterRoom] = useState<string | null>(null);
  const rawId = q || segmentId(path, "agents");
  const id = rawId ? canonicalAgentId(rawId) : "";

  useEffect(() => {
    setQ(queryId(window.location.search));
  }, [path]);

  useEffect(() => {
    if (!id) return;
    setData(null);
    setErr(null);
    setFilterRoom(null);
    api
      .agent(id)
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, [id]);

  const events = useMemo(() => {
    if (!data) return [] as ChatThreadEvent[];
    const rows: ChatThreadEvent[] = [];
    for (const msg of data.messages) {
      if (filterRoom && msg.room_id !== filterRoom) continue;
      rows.push({
        kind: "message",
        id: msg.id,
        at: msg.created_at,
        msg: msg as RoomMessage,
        roomHint: msg.room_title,
      });
    }
    for (const h of data.handoffs) {
      if (filterRoom && h.room_id && h.room_id !== filterRoom) continue;
      rows.push({
        kind: "handoff",
        id: h.id,
        at: h.started_at,
        from_agent: h.from_agent,
        to_agent: h.to_agent,
        summary: h.summary,
      });
    }
    return rows.sort((a, b) => a.at.localeCompare(b.at));
  }, [data, filterRoom]);

  const resources = useMemo(
    () => ((data?.resources || []) as ProofPayload[]).filter((p) => p && p.kind),
    [data]
  );

  if (err) return <ErrorState message={err} />;
  if (!id || !data) return <Loading label="Loading" />;

  const desk = data.desk;

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--bg)]">
      <div className="border-b border-border bg-white px-5 pb-4 pt-6 sm:px-8 lg:px-12 lg:pt-8">
        <div className="flex items-start gap-4">
          <AgentBadge
            name={data.agent.id}
            status={
              desk?.status === "handing_off"
                ? "handing_off"
                : desk && desk.status !== "idle"
                  ? "working"
                  : "idle"
            }
            size={52}
            variant="face"
          />
          <div className="min-w-0">
            <Link href="/registry" className="text-[13px] text-[var(--faint)] hover:text-foreground">
              ← Agents
            </Link>
            <h1 className="mt-2 text-[26px] font-semibold tracking-tight">{data.agent.display_name}</h1>
            <p className="mt-1 max-w-xl text-[14px] text-[var(--dim)]">{data.agent.role}</p>
            {desk ? (
              <p className="mt-3 text-[14px] text-foreground">
                {desk.status === "idle" ? "Idle" : desk.doing}
                {desk.room_id ? (
                  <>
                    <span className="mx-2 text-[var(--faint)]">·</span>
                    <Link href={`/rooms/${desk.room_id}`} className="text-accent">
                      {desk.room_title}
                    </Link>
                  </>
                ) : null}
              </p>
            ) : null}
          </div>
        </div>

        {data.rooms.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setFilterRoom(null)}
              className={
                "rounded-full px-3 py-1 text-[13px] " +
                (!filterRoom
                  ? "bg-accent text-white"
                  : "bg-[var(--elev)] text-[var(--dim)] hover:text-foreground")
              }
            >
              All rooms
            </button>
            {data.rooms.map((room) => (
              <button
                key={room.id}
                type="button"
                onClick={() => setFilterRoom(filterRoom === room.id ? null : room.id)}
                className={
                  "rounded-full px-3 py-1 text-[13px] " +
                  (filterRoom === room.id
                    ? "bg-accent text-white"
                    : "bg-[var(--elev)] text-[var(--dim)] hover:text-foreground")
                }
              >
                {room.title}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="chat-scroll flex-1 overflow-y-auto px-5 py-5 sm:px-8 lg:px-12">
        <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,22rem)]">
          <div className="min-w-0">
            <WorkChatThread
              events={events}
              showRoomHints={!filterRoom}
              variant="group"
              empty={`No messages from ${shortName(data.agent.id)} yet.`}
            />
            {filterRoom ? (
              <p className="mt-6 text-center text-[13px]">
                <Link href={`/rooms/${filterRoom}`} className="text-accent hover:underline">
                  Open room
                </Link>
              </p>
            ) : null}
          </div>

          <aside className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--faint)]">
              Live sources
            </p>
            <p className="mt-1 text-[13px] text-[var(--dim)]">
              What this agent reads — same connectors, live when datasets exist.
            </p>
            {resources.length ? (
              <ProofGrid cards={resources} className="mt-4 sm:grid-cols-1 xl:grid-cols-1" compact />
            ) : (
              <p className="mt-4 text-[13px] text-[var(--faint)]">No connector cards for this agent yet.</p>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}
