"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Calendar, Mail, Video, Github, ExternalLink, Plug } from "lucide-react";

export type WorkflowLink = {
  kind: string;
  label: string;
  url: string;
  room_id?: string | null;
  detail?: string;
  simulated?: boolean;
};

const KIND_ICON: Record<string, typeof Calendar> = {
  calendar: Calendar,
  meet: Video,
  gmail: Mail,
  github: Github,
};

function LinkRow({ item }: { item: WorkflowLink }) {
  const Icon = KIND_ICON[item.kind] || ExternalLink;
  return (
    <div className="interactive row-link flex items-start gap-3 rounded-xl px-3 py-2.5">
      <a href={item.url} target="_blank" rel="noreferrer" className="flex min-w-0 flex-1 items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-accent" strokeWidth={1.75} />
        <span className="min-w-0 flex-1">
          <span className="block text-[13px] font-medium leading-5 text-foreground">{item.label}</span>
          {item.detail ? <span className="mt-0.5 block text-[11px] text-[var(--faint)]">{item.detail}</span> : null}
          {item.simulated ? (
            <span className="mt-0.5 block text-[11px] text-[var(--faint)]">Simulated</span>
          ) : null}
        </span>
        <ExternalLink className="h-3.5 w-3.5 shrink-0 text-[var(--faint)]" />
      </a>
      {item.room_id ? (
        <Link href={`/rooms/${item.room_id}`} className="shrink-0 self-center text-[11px] text-accent">
          →
        </Link>
      ) : null}
    </div>
  );
}

/** Calendar · Meet · Gmail · PR links from coordination workflow. */
export function WorkflowLinksPanel({ compact, className }: { compact?: boolean; className?: string }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.workflowLinks>> | null>(null);

  useEffect(() => {
    api
      .workflowLinks()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) {
    return (
      <div className={cn("surface-lg p-4 sm:p-5", className)}>
        <p className="text-[13px] text-[var(--faint)]">Loading workflow links…</p>
      </div>
    );
  }

  const connected = data.oauth?.connected;

  return (
    <div className={cn("surface-lg p-4 sm:p-5", className)}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">Workflows</p>
          <h2 className={cn("font-semibold tracking-tight text-foreground", compact ? "text-[16px]" : "text-[18px]")}>
            Calendar · Gmail · Meet
          </h2>
          {connected && data.oauth.email ? (
            <p className="mt-1 text-[13px] text-[var(--faint)]">{data.oauth.email}</p>
          ) : null}
        </div>
        {!connected ? (
          <a
            href={data.oauth.authorize_path?.startsWith("http") ? data.oauth.authorize_path : `/api/oauth/google/start`}
            className="interactive inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-white px-3 py-1.5 text-[12px] font-medium text-accent press"
          >
            <Plug className="h-3.5 w-3.5" />
            Connect
          </a>
        ) : null}
      </div>

      {data.links.length > 0 ? (
        <ul className={cn("space-y-1.5", compact ? "mt-3" : "mt-4")}>
          {data.links.slice(0, compact ? 4 : 12).map((item) => (
            <li key={`${item.kind}-${item.url}`}>
              <LinkRow item={item} />
            </li>
          ))}
        </ul>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2 border-t border-border/60 pt-4">
        {data.shortcuts.map((s) => {
          const Icon = KIND_ICON[s.kind] || ExternalLink;
          return (
            <a
              key={s.url}
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="interactive inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1.5 text-[12px] font-medium text-[var(--dim)] press hover:text-foreground"
            >
              <Icon className="h-3.5 w-3.5" />
              {s.label}
            </a>
          );
        })}
        <Link href="/connect" className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] text-[var(--dim)] hover:text-foreground">
          Connect
        </Link>
      </div>
    </div>
  );
}

/** Inline chips for pipeline cards. */
export function WorkflowLinkChips({
  calendar_url,
  meet_url,
  gmail_url,
  pr_url,
}: {
  calendar_url?: string | null;
  meet_url?: string | null;
  gmail_url?: string | null;
  pr_url?: string | null;
}) {
  const chips: Array<{ label: string; url: string; kind: string }> = [];
  if (meet_url) chips.push({ label: "Meet", url: meet_url, kind: "meet" });
  else if (calendar_url) chips.push({ label: "Calendar", url: calendar_url, kind: "calendar" });
  if (gmail_url) chips.push({ label: "Gmail", url: gmail_url, kind: "gmail" });
  if (pr_url) chips.push({ label: "PR", url: pr_url, kind: "github" });
  if (!chips.length) return null;

  return (
    <div className="flex flex-wrap gap-1 px-2 pb-1.5 pt-0">
      {chips.map((c) => (
        <a
          key={c.url}
          href={c.url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="rounded-full bg-[var(--elev)] px-2 py-0.5 text-[10px] font-medium text-accent hover:underline"
        >
          {c.label} ↗
        </a>
      ))}
    </div>
  );
}
