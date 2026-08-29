"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type AgentDetail } from "@/lib/api";
import { shortName } from "@/lib/names";
import { when } from "@/lib/utils";
import { ErrorState, Loading } from "@/components/ui";
import { PixelSprite } from "@/components/pixel-office";

export function AgentView() {
  const [id, setId] = useState("");
  const [data, setData] = useState<AgentDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const last = parts[parts.length - 1];
    if (last && last !== "agents" && last !== "_") setId(last);
    const q = new URLSearchParams(window.location.search).get("id");
    if (q) setId(q);
  }, []);

  useEffect(() => {
    if (!id) return;
    api
      .agent(id)
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, [id]);

  if (err) return <ErrorState message={err} />;
  if (!id || !data) return <Loading label="Finding this person" />;

  const desk = data.desk;

  return (
    <div className="flex h-full min-h-0 flex-col bg-white">
      <div className="flex items-start gap-4 px-8 pb-5 pt-8 lg:px-12">
        <PixelSprite name={data.agent.id} scale={4} working={desk?.status !== "idle"} />
        <div className="min-w-0">
          <Link href="/" className="text-[13px] text-[var(--faint)] hover:text-foreground">
            ← Campus
          </Link>
          <p className="mt-3 text-[13px] text-[var(--faint)]">Agent</p>
          <h1 className="mt-1 text-[26px] font-semibold tracking-tight">{data.agent.display_name}</h1>
          <p className="mt-2 max-w-xl text-[14px] leading-6 text-[var(--dim)]">{data.agent.role}</p>
          {desk ? (
            <p className="mt-3 text-[14px] text-foreground">
              {desk.status === "idle" ? "Between tasks" : desk.doing}
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
        <div className="mx-8 flex flex-wrap gap-2 lg:mx-12">
          {data.rooms.map((room) => (
            <Link
              key={room.id}
              href={`/rooms/${room.id}`}
              className="rounded-full bg-[var(--elev)] px-3 py-1 text-[13px] text-[var(--dim)] hover:text-foreground"
            >
              {room.title}
            </Link>
          ))}
        </div>
      ) : null}

      <div className="chat-scroll mt-6 flex-1 space-y-5 overflow-y-auto px-8 pb-10 lg:px-12">
        {data.handoffs.length ? (
          <section>
            <p className="text-[12px] text-[var(--faint)]">Handed across the room</p>
            <div className="mt-2 space-y-2">
              {data.handoffs.map((h) => (
                <p key={h.id} className="text-[14px] leading-6 text-[var(--dim)]">
                  <Link href={`/agents/${h.from_agent}`} className="font-medium text-foreground">
                    {shortName(h.from_agent)}
                  </Link>
                  <span className="mx-1.5 text-[var(--faint)]">→</span>
                  <Link href={`/agents/${h.to_agent}`} className="font-medium text-foreground">
                    {shortName(h.to_agent)}
                  </Link>
                  <span className="mx-2 text-[var(--faint)]">·</span>
                  {h.summary}
                </p>
              ))}
            </div>
          </section>
        ) : null}

        <section>
          <p className="text-[12px] text-[var(--faint)]">What {data.agent.display_name} said</p>
          <div className="mt-3 space-y-4">
            {data.messages.length === 0 ? (
              <p className="text-[14px] text-[var(--dim)]">Nothing posted yet.</p>
            ) : (
              data.messages.map((msg) => (
                <div key={msg.id}>
                  <p className="text-[12px] text-[var(--faint)]">
                    {msg.room_title} · {when(msg.created_at)}
                  </p>
                  <p className="mt-1 max-w-[640px] text-[14px] leading-6">{msg.text}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
