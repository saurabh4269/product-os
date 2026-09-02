"use client";

import Link from "next/link";
import { ArtifactCard } from "@/components/artifact-card";
import { ChatBubble } from "@/components/room-chat";
import { HandoffPacket } from "@/components/handoff-packet";
import { ProofEmbed, proofFromArtifact } from "@/components/proof-embed";
import { StructuredEvidenceCard, structuredFromArtifact } from "@/components/structured-evidence-card";
import type { RoomMessage } from "@/lib/api";
import { agentHref, hashHue, shortName } from "@/lib/names";
import { narrateHandoff } from "@/lib/chat-narrate";
import { when, clock, cn } from "@/lib/utils";

export type ChatThreadEvent =
  | {
      kind: "handoff";
      id: string;
      at: string;
      from_agent: string;
      to_agent: string;
      summary: string;
    }
  | {
      kind: "chat";
      id: string;
      at: string;
      author: string;
      author_kind?: string;
      text: string;
      artifact_type?: string | null;
      artifact?: Record<string, unknown>;
      msg_kind?: string;
      roomHint?: string | null;
    }
  | {
      kind: "system";
      id: string;
      at: string;
      text: string;
    }
  | {
      kind: "message";
      id: string;
      at: string;
      msg: RoomMessage;
      roomHint?: string | null;
    };

function SystemPill({ text }: { text: string }) {
  const soft = text.toLowerCase() === "today";
  return (
    <div className="flex justify-center py-2">
      <span
        className={cn(
          "rounded-full px-3 py-1 text-[11px] font-medium",
          soft ? "bg-white/80 text-[var(--dim)] shadow-sm" : "bg-[#d8d8dc] text-[#3a3a3c]"
        )}
      >
        {text}
      </span>
    </div>
  );
}

/** Room chat (handoff packets) or group workflow chat (Traces). */
export function WorkChatThread({
  events,
  empty = "Nothing here yet.",
  showRoomHints,
  variant = "room",
  className,
}: {
  events: ChatThreadEvent[];
  empty?: string;
  showRoomHints?: boolean;
  /** group = natural end-to-end workflow chat (no handoff cards) */
  variant?: "room" | "group";
  className?: string;
}) {
  if (events.length === 0) {
    return <p className="py-10 text-center text-[13px] text-[var(--faint)]">{empty}</p>;
  }

  const group = variant === "group";
  let lastAuthor = "";

  return (
    <div className={cn(group ? "space-y-1.5" : "space-y-2.5", className)}>
      {events.map((row) => {
        if (row.kind === "system") {
          lastAuthor = "";
          return <SystemPill key={row.id} text={row.text} />;
        }

        if (row.kind === "handoff") {
          if (group) {
            const ask = narrateHandoff(row.from_agent, row.to_agent, row.summary);
            const repeat = row.from_agent === lastAuthor;
            lastAuthor = row.from_agent;
            return (
              <div key={row.id} className={cn("flex justify-start", repeat ? "pl-0" : "")}>
                <ChatBubble
                  author={row.from_agent}
                  text={ask}
                  isYou={false}
                  compact={repeat}
                  showName
                  tone="messenger"
                  href={repeat ? null : agentHref(row.from_agent)}
                  time={clock(row.at)}
                />
              </div>
            );
          }
          lastAuthor = "";
          return (
            <HandoffPacket
              key={row.id}
              from={row.from_agent}
              to={row.to_agent}
              summary={narrateHandoff(row.from_agent, row.to_agent, row.summary)}
              at={when(row.at)}
            />
          );
        }

        if (row.kind === "chat") {
          const isYou = row.author === "you" || row.author_kind === "human";
          const repeat = !isYou && row.author === lastAuthor;
          lastAuthor = row.author;
          const href = row.author_kind !== "human" ? agentHref(row.author) : null;
          const proof = proofFromArtifact(row.artifact, row.artifact_type);
          const structured = structuredFromArtifact(row.artifact);
          if (structured) {
            lastAuthor = "";
            return (
              <div key={row.id} className={cn("flex", isYou ? "justify-end" : "justify-start")}>
                <div className="w-full max-w-[min(100%,28rem)]">
                  {!isYou && group ? (
                    <p
                      className="mb-1 pl-1 text-[13px] font-semibold"
                      style={{ color: `hsl(${hashHue(row.author)} 58% 36%)` }}
                    >
                      {shortName(row.author)}
                    </p>
                  ) : null}
                  <StructuredEvidenceCard structured={structured} />
                </div>
              </div>
            );
          }
          if (proof) {
            lastAuthor = "";
            return (
              <div key={row.id} className={cn("flex", isYou ? "justify-end" : "justify-start")}>
                <div className="w-full max-w-[min(100%,28rem)]">
                  {!isYou && group ? (
                    <p
                      className="mb-1 pl-1 text-[13px] font-semibold"
                      style={{ color: `hsl(${hashHue(row.author)} 58% 36%)` }}
                    >
                      {shortName(row.author)}
                    </p>
                  ) : null}
                  <ProofEmbed proof={proof} compact className="mt-0 fade-in" />
                  {row.text && !row.text.startsWith("Opened PR") ? (
                    <p className="mt-1 px-1 text-[11px] text-[var(--faint)]">{row.text}</p>
                  ) : null}
                </div>
              </div>
            );
          }
          if (!group && row.msg_kind === "artifact" && row.artifact_type) {
            lastAuthor = "";
            const msg: RoomMessage = {
              id: row.id,
              room_id: "",
              author: row.author,
              author_kind: (row.author_kind as RoomMessage["author_kind"]) || "agent",
              kind: "artifact",
              text: row.text,
              artifact_type: row.artifact_type || undefined,
              artifact: row.artifact || {},
              created_at: row.at,
            };
            return (
              <div key={row.id} className="max-w-md">
                <ArtifactCard msg={msg} />
              </div>
            );
          }
          return (
            <div key={row.id} className={cn("flex", isYou ? "justify-end" : "justify-start")}>
              <ChatBubble
                author={row.author}
                text={row.text}
                isYou={isYou}
                compact={repeat}
                showName={group && !isYou}
                tone={group ? "messenger" : "room"}
                href={repeat ? null : href}
                time={group ? clock(row.at) : when(row.at)}
              />
            </div>
          );
        }

        const msg = row.msg;
        const isYou = msg.author === "you" || msg.author_kind === "human";
        const repeat = msg.author === lastAuthor;
        lastAuthor = msg.author;
        const href = msg.author_kind === "agent" ? agentHref(msg.author) : null;
        const hint =
          showRoomHints && row.roomHint ? (
            <p className="mb-1 pl-9 text-[11px] text-[var(--faint)]">{row.roomHint}</p>
          ) : null;
        const proof = proofFromArtifact(msg.artifact, msg.artifact_type);
        const structured = structuredFromArtifact(msg.artifact);

        if (structured) {
          lastAuthor = "";
          return (
            <div key={msg.id} className="max-w-md">
              {hint}
              <StructuredEvidenceCard structured={structured} />
            </div>
          );
        }

        if (proof) {
          lastAuthor = "";
          return (
            <div key={msg.id} className="max-w-md">
              {hint}
              <ProofEmbed proof={proof} compact className="mt-0 fade-in" />
            </div>
          );
        }

        if (!group && msg.kind === "artifact") {
          lastAuthor = "";
          return (
            <div key={msg.id} className="max-w-md">
              {hint}
              <ArtifactCard msg={msg} />
            </div>
          );
        }

        return (
          <div key={msg.id}>
            {hint}
            <div className={cn("flex", isYou ? "justify-end" : "justify-start")}>
              <ChatBubble
                author={msg.author}
                text={msg.text}
                isYou={isYou}
                compact={repeat}
                showName={group && !isYou}
                tone={group ? "messenger" : "room"}
                href={repeat ? null : href}
                time={group ? clock(msg.created_at) : when(msg.created_at)}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ThreadRoomHeader({
  title,
  href,
  kind,
  members,
}: {
  title: string;
  href?: string | null;
  kind?: string | null;
  members?: string[];
}) {
  const names = members?.length ? members.map(shortName).join(", ") : null;
  const inner = (
    <>
      <div className="min-w-0">
        <span className="block truncate text-[16px] font-semibold tracking-tight">{title}</span>
        {names ? <span className="mt-0.5 block truncate text-[12px] text-[var(--faint)]">{names}</span> : null}
      </div>
      {kind ? (
        <span className="shrink-0 text-[11px] uppercase tracking-wide text-[var(--faint)]">{kind}</span>
      ) : null}
    </>
  );
  if (href) {
    return (
      <Link href={href} className="flex items-start justify-between gap-3 hover:text-accent">
        {inner}
      </Link>
    );
  }
  return <div className="flex items-start justify-between gap-3">{inner}</div>;
}
