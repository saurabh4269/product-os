"use client";

import Link from "next/link";
import { StreamBody } from "@/components/stream-body";
import { AgentBadge } from "@/components/agent-badge";
import { agentHref, hashHue, shortName } from "@/lib/names";
import { cn } from "@/lib/utils";

const STATUS_DOT: Record<string, string> = {
  thinking: "bg-accent animate-pulse",
  tool: "bg-warn",
  speaking: "bg-ok",
  working: "bg-accent",
  idle: "bg-[var(--faint)]/40",
};

export function RoomAgentRail({
  members,
  working,
  presence,
  activity,
  picked,
  onPick,
  className,
}: {
  members: string[];
  working: Set<string>;
  presence: Record<string, string>;
  activity: Record<string, string>;
  picked?: string | null;
  onPick?: (id: string | null) => void;
  className?: string;
}) {
  const shown = members.filter((m) => m !== "system");
  return (
    <aside
      className={cn(
        "flex w-full shrink-0 flex-col border-b border-border bg-[var(--floor)] lg:w-52 lg:min-h-0 lg:border-b-0 lg:border-r",
        className
      )}
    >
      <div className="hidden px-3 py-3 lg:block">
        <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">In this room</p>
      </div>
      <div className="flex gap-1 overflow-x-auto px-2 py-2 lg:max-h-full lg:flex-1 lg:flex-col lg:gap-0.5 lg:overflow-x-hidden lg:overflow-y-auto lg:px-2 lg:pb-3">
        {shown.map((id) => {
          const st = presence[id] || (working.has(id) ? "thinking" : "idle");
          const hot = picked === id;
          const dot = STATUS_DOT[st] || STATUS_DOT.idle;
          const inner = (
            <>
              <span className="relative shrink-0">
                <AgentBadge name={id} size={28} variant="face" />
                <span className={cn("absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full ring-2 ring-white", dot)} />
              </span>
              <span className="min-w-0 flex-1 lg:block">
                <span className="block truncate text-[13px] font-medium">{shortName(id)}</span>
                {activity[id] ? (
                  <span className="hidden max-w-[9rem] truncate text-[10px] text-[var(--faint)] lg:block">
                    {activity[id]}
                  </span>
                ) : null}
              </span>
            </>
          );
          const cls = cn(
            "flex shrink-0 items-center gap-2 rounded-xl px-2 py-2 text-left transition-colors lg:w-full",
            hot ? "bg-white shadow-sm ring-1 ring-accent/25" : "hover:bg-white/80"
          );
          if (onPick) {
            return (
              <button key={id} type="button" className={cls} onClick={() => onPick(hot ? null : id)}>
                {inner}
              </button>
            );
          }
          return (
            <Link key={id} href={agentHref(id)} className={cls}>
              {inner}
            </Link>
          );
        })}
      </div>
    </aside>
  );
}

export function ChatBubble({
  author,
  text,
  time,
  live,
  isYou,
  artifact,
  href,
  compact,
  showName,
  tone = "room",
}: {
  author: string;
  text: string;
  time?: string;
  live?: boolean;
  isYou?: boolean;
  artifact?: boolean;
  href?: string | null;
  /** Follow-up in a run — no avatar */
  compact?: boolean;
  /** Colored display name above the body (group-chat style) */
  showName?: boolean;
  /** messenger = soft group chat like colleagues texting */
  tone?: "room" | "messenger";
}) {
  const hue = hashHue(author);
  const name = shortName(author);
  const messenger = tone === "messenger";
  const bubble = (
    <div
      className={cn(
        "max-w-[min(100%,36rem)] break-words text-[14px] leading-5",
        messenger
          ? "max-w-[min(100%,42rem)] rounded-2xl rounded-bl-md bg-[#ebebed] px-3 py-2"
          : cn(
              "rounded-2xl px-3.5 py-2.5 leading-6 shadow-sm",
              isYou ? "rounded-br-md bg-accent text-white" : "rounded-bl-md border border-border bg-white text-foreground"
            )
      )}
      style={
        !isYou && !messenger
          ? { borderLeftColor: `hsl(${hue} 45% 48%)`, borderLeftWidth: 3 }
          : undefined
      }
    >
      {!isYou && showName && !compact ? (
        <p
          className={cn("font-semibold", messenger ? "mb-0.5 text-[13px]" : "mb-0.5 text-[12px]")}
          style={{ color: `hsl(${hue} 58% 36%)` }}
        >
          {name}
        </p>
      ) : null}
      {artifact ? (
        <p className="text-[13px] font-medium opacity-90">{text}</p>
      ) : (
        <StreamBody
          text={text}
          live={live}
          className={cn(isYou && !messenger ? "text-white" : undefined, messenger && "text-[15px] leading-5")}
        />
      )}
      {time ? (
        <p
          className={cn(
            "mt-1 text-right text-[10px]",
            isYou && !messenger ? "text-white/70" : "text-[var(--faint)]"
          )}
        >
          {time}
        </p>
      ) : null}
    </div>
  );

  return (
    <div className={cn("flex gap-2", isYou ? "flex-row-reverse" : "flex-row")}>
      {!isYou && !compact ? (
        href ? (
          <Link href={href} className="shrink-0 self-end hover:opacity-80">
            <AgentBadge name={author} size={messenger ? 30 : 28} variant="face" />
          </Link>
        ) : (
          <AgentBadge
            name={author}
            size={messenger ? 30 : 28}
            variant="face"
            className="shrink-0 self-end"
          />
        )
      ) : (
        !isYou && compact ? <span className="w-[30px] shrink-0" /> : null
      )}
      {bubble}
    </div>
  );
}

export function ChatDayDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="h-px flex-1 bg-border" />
      <span className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">{label}</span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}
