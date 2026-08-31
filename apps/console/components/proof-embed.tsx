"use client";

import {
  ExternalLink,
  Github,
  Database,
  BarChart3,
  Mail,
  Phone,
  Flag,
  BookOpen,
  Shield,
  Rocket,
  Megaphone,
  ScrollText,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type ProofPayload = {
  kind?: string;
  status?: string;
  title?: string;
  subtitle?: string;
  detail?: string;
  source?: string;
  live?: boolean;
  project?: string;
  dataset?: string;
  table?: string;
  sql?: string;
  columns?: string[];
  rows?: Array<Record<string, unknown>>;
  console_url?: string | null;
  url?: string | null;
  repo?: string;
  number?: number;
  state?: string;
  draft?: boolean;
  merged?: boolean;
  additions?: number;
  deletions?: number;
  changed_files?: number;
  head?: string;
  base?: string;
  files?: Array<{
    filename?: string;
    status?: string;
    additions?: number;
    deletions?: number;
  }>;
  to?: string;
  channel?: string;
  property_id?: string;
  metric?: string;
  error?: string | null;
  phone?: string | null;
  found?: boolean;
  email?: string;
  reading?: { claim?: string; value?: number; source?: string } | null;
};

const BRAND: Record<string, { label: string; icon: typeof Database }> = {
  ga4: { label: "Google Analytics", icon: BarChart3 },
  warehouse: { label: "BigQuery", icon: Database },
  bq: { label: "BigQuery", icon: Database },
  logs: { label: "Logs", icon: ScrollText },
  deploys: { label: "Deploys", icon: Rocket },
  ads: { label: "Ads", icon: Megaphone },
  github: { label: "GitHub", icon: Github },
  gmail: { label: "Gmail", icon: Mail },
  contacts: { label: "Callback search", icon: Phone },
  flags: { label: "Flags", icon: Flag },
  memory: { label: "Memory", icon: BookOpen },
  workspace: { label: "Workspace", icon: Calendar },
  gateway: { label: "Gateway", icon: Shield },
};

function Shell({
  brand,
  icon: Icon,
  title,
  subtitle,
  href,
  children,
  className,
  lifecycle,
}: {
  brand: string;
  icon: typeof Database;
  title: string;
  subtitle?: string;
  href?: string | null;
  children: React.ReactNode;
  className?: string;
  lifecycle?: string | null;
}) {
  const life =
    lifecycle === "running" || lifecycle === "done" || lifecycle === "failed" || lifecycle === "applied"
      ? lifecycle === "applied"
        ? "done"
        : lifecycle
      : null;
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-[#fbfbfc] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]",
        life === "running" && "border-accent/35",
        life === "failed" && "border-danger/35",
        className
      )}
    >
      <div className="flex items-center gap-2 border-b border-border bg-white px-3 py-2">
        <Icon
          className={cn("h-3.5 w-3.5 text-accent", life === "running" && "animate-pulse")}
          strokeWidth={1.75}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-[11px] font-semibold tracking-wide text-[var(--faint)] uppercase">
              {brand}
            </p>
            {life ? (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
                  life === "running" && "bg-accent/10 text-accent",
                  life === "done" && "bg-ok/10 text-ok",
                  life === "failed" && "bg-danger/10 text-danger"
                )}
              >
                {life === "running" ? "Working" : life === "failed" ? "Failed" : "Done"}
              </span>
            ) : null}
          </div>
          <p className="truncate text-[12px] font-medium text-foreground">{title}</p>
          {subtitle ? <p className="truncate text-[10px] text-[var(--faint)]">{subtitle}</p> : null}
        </div>
        {href ? (
          <a
            href={href}
            target={href.startsWith("http") ? "_blank" : undefined}
            rel="noreferrer"
            className="inline-flex shrink-0 items-center gap-1 rounded-full border border-border bg-white px-2 py-0.5 text-[10px] font-medium text-accent hover:bg-[var(--elev)]"
            onClick={(e) => e.stopPropagation()}
          >
            Open
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : null}
      </div>
      <div className="px-3 py-2.5">{children}</div>
    </div>
  );
}

function TableBlock({ proof }: { proof: ProofPayload }) {
  const cols = proof.columns?.length ? proof.columns : [];
  const rows = proof.rows || [];
  if (!cols.length) {
    return <p className="text-[11px] text-[var(--faint)]">{proof.error || proof.detail || "No rows"}</p>;
  }
  if (!rows.length) {
    return <p className="text-[11px] text-[var(--faint)]">{proof.error || proof.detail || "No rows"}</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-white">
      <table className="min-w-full text-left text-[11px]">
        <thead className="bg-[var(--elev)] text-[var(--faint)]">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-2 py-1.5 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 6).map((row, i) => (
            <tr key={i} className="border-t border-border/70">
              {cols.map((c) => (
                <td key={c} className="px-2 py-1 font-mono tabular-nums text-foreground">
                  {formatCell(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DataProof({ proof }: { proof: ProofPayload }) {
  const meta = BRAND[proof.kind || ""] || BRAND.warehouse;
  return (
    <Shell
      brand={meta.label}
      icon={meta.icon}
      title={proof.title || "Query results"}
      subtitle={[
        proof.live ? "live" : proof.source === "file_warehouse" ? "demo tables" : proof.source,
        proof.subtitle || proof.detail,
      ]
        .filter(Boolean)
        .join(" · ")}
      href={proof.console_url || proof.url}
      lifecycle={proof.status}
    >
      {proof.project ? (
        <p className="mb-2 font-mono text-[10px] text-[var(--faint)]">
          {proof.project}
          {proof.dataset ? `.${proof.dataset}` : ""}
          {proof.table ? `.${proof.table}` : ""}
        </p>
      ) : null}
      {proof.sql ? (
        <pre className="mb-2 max-h-16 overflow-auto rounded-lg bg-[#1d1d1f] px-2.5 py-2 font-mono text-[10px] leading-4 text-[#f5f5f7]">
          {proof.sql}
        </pre>
      ) : null}
      <TableBlock proof={proof} />
      {proof.reading?.claim ? (
        <p className="mt-2 text-[11px] text-[var(--dim)]">{proof.reading.claim}</p>
      ) : null}
    </Shell>
  );
}

/** Resolve a rich receipt/proof from a room message artifact. */
export function proofFromArtifact(
  artifact?: Record<string, unknown> | null,
  artifactType?: string | null
): ProofPayload | null {
  if (!artifact) return null;
  const nested = artifact.proof;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    const p = nested as ProofPayload;
    if (p.kind) {
      // Carry receipt lifecycle onto the nested proof for the status chip.
      if (typeof artifact.status === "string" && !p.status) {
        return { ...p, status: artifact.status };
      }
      if (artifact.status === "running" || artifact.status === "failed") {
        return { ...p, status: String(artifact.status) };
      }
      return p;
    }
  }
  if (typeof artifact.kind === "string" && BRAND[artifact.kind]) {
    return artifact as ProofPayload;
  }

  const type = (artifactType || "").toLowerCase();
  const url = String(artifact.pr_url || artifact.url || artifact.html_url || artifact.open_url || "");

  if (
    type === "pr" ||
    type === "code_fix" ||
    type === "code" ||
    /github\.com\/[^/]+\/[^/]+\/pull\/\d+/.test(url)
  ) {
    if (url.includes("github.com")) {
      const m = url.match(/github\.com\/([^/]+)\/([^/]+)\/pull\/(\d+)/);
      return {
        kind: "github",
        status: typeof artifact.status === "string" ? artifact.status : "applied",
        title:
          (typeof artifact.title === "string" && artifact.title) ||
          (m ? `PR #${m[3]}` : "Pull request"),
        subtitle: m ? `${m[1]}/${m[2]}#${m[3]}` : undefined,
        detail: typeof artifact.detail === "string" ? artifact.detail : undefined,
        url,
        console_url: url,
        repo: m ? `${m[1]}/${m[2]}` : undefined,
        number: m ? Number(m[3]) : undefined,
        state: typeof artifact.state === "string" ? artifact.state : "open",
        live: false,
        source: "message",
      };
    }
  }

  if (type === "mail_outreach" || type === "mail" || type === "gmail" || type === "mail_reply") {
    return {
      kind: "gmail",
      status: typeof artifact.status === "string" ? artifact.status : "applied",
      title: (typeof artifact.subject === "string" && artifact.subject) || (typeof artifact.title === "string" && artifact.title) || "Mail",
      subtitle: String(artifact.to || artifact.subtitle || ""),
      detail: typeof artifact.detail === "string" ? artifact.detail : undefined,
      to: typeof artifact.to === "string" ? artifact.to : undefined,
      url: String(artifact.gmail_url || url || "") || null,
      console_url: String(artifact.gmail_url || url || "") || null,
      channel: typeof artifact.channel === "string" ? artifact.channel : undefined,
    };
  }

  if (type === "call" || type === "call_feedback" || type === "contact_lookup" || type === "contacts") {
    return {
      kind: "contacts",
      status: typeof artifact.status === "string" ? artifact.status : "applied",
      title: (typeof artifact.title === "string" && artifact.title) || "Customer call",
      subtitle: String(artifact.to_number || artifact.phone || artifact.subtitle || ""),
      detail: typeof artifact.detail === "string" ? artifact.detail : typeof artifact.reason === "string" ? artifact.reason : undefined,
      phone: (artifact.to_number || artifact.phone) as string | undefined,
      found: typeof artifact.found === "boolean" ? artifact.found : undefined,
    };
  }

  if (type === "memory_card" || type === "memory") {
    const lesson = artifact.lesson && typeof artifact.lesson === "object" ? (artifact.lesson as Record<string, unknown>) : artifact;
    return {
      kind: "memory",
      status: "applied",
      title: "Lesson written",
      subtitle: String(lesson.id || "Memory Bank"),
      detail: String(lesson.statement || artifact.detail || artifact.text || ""),
    };
  }

  if (type === "receipt" && typeof artifact.title === "string") {
    const kind = typeof artifact.kind === "string" && BRAND[artifact.kind] ? artifact.kind : "gateway";
    return {
      kind,
      status: typeof artifact.status === "string" ? artifact.status : "done",
      title: artifact.title,
      subtitle: typeof artifact.detail === "string" ? artifact.detail : undefined,
      detail: typeof artifact.detail === "string" ? artifact.detail : undefined,
      url: url || null,
      console_url: url || null,
    };
  }

  if (type === "coordination" && (artifact.gmail_url || artifact.calendar || artifact.meet_url)) {
    const cal = artifact.calendar && typeof artifact.calendar === "object" ? (artifact.calendar as Record<string, unknown>) : {};
    const meet = String(artifact.meet_url || cal.meet_url || "");
    const gmail = String(artifact.gmail_url || "");
    if (meet || cal.create) {
      return {
        kind: "workspace",
        status: "applied",
        title: String(cal.summary || artifact.title || "Calendar hold"),
        subtitle: String(cal.start || ""),
        detail: "Workspace calendar",
        url: meet || gmail || null,
        console_url: meet || gmail || null,
      };
    }
    if (gmail) {
      return {
        kind: "gmail",
        status: "applied",
        title: "Coordination mail",
        url: gmail,
        console_url: gmail,
      };
    }
  }

  return null;
}

function GitHubProof({ proof }: { proof: ProofPayload }) {
  const href = proof.console_url || proof.url;
  const empty = proof.status === "empty" && !href;
  const state = proof.merged ? "merged" : proof.draft ? "draft" : proof.state || (href ? "open" : "");
  return (
    <Shell
      brand="GitHub"
      icon={Github}
      title={proof.title || (proof.number ? `PR #${proof.number}` : "Pull request")}
      subtitle={proof.subtitle || (proof.repo ? `${proof.repo}${proof.number ? `#${proof.number}` : ""}` : undefined)}
      href={href}
      lifecycle={proof.status}
    >
      {empty ? (
        <p className="text-[11px] text-[var(--faint)]">{proof.detail || "No PR yet"}</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 font-semibold uppercase tracking-wide",
                proof.merged
                  ? "bg-ok/10 text-ok"
                  : state === "open"
                    ? "bg-accent/10 text-accent"
                    : "bg-[var(--elev)] text-[var(--faint)]"
              )}
            >
              {proof.merged ? "Merged" : proof.draft ? "Draft" : state || "PR"}
            </span>
            {proof.head && proof.base ? (
              <span className="font-mono text-[var(--faint)]">
                {proof.head} → {proof.base}
              </span>
            ) : null}
            {typeof proof.additions === "number" ? <span className="text-ok">+{proof.additions}</span> : null}
            {typeof proof.deletions === "number" ? <span className="text-danger">−{proof.deletions}</span> : null}
            {typeof proof.changed_files === "number" && !proof.files?.length ? (
              <span className="text-[var(--faint)]">{proof.changed_files} files</span>
            ) : null}
          </div>
          {proof.files && proof.files.length > 0 ? (
            <ul className="mt-2 space-y-1">
              {proof.files.slice(0, 5).map((f) => (
                <li key={f.filename} className="flex items-center justify-between gap-2 font-mono text-[10px]">
                  <span className="truncate text-foreground">{f.filename}</span>
                  <span className="shrink-0 text-[var(--faint)]">
                    {typeof f.additions === "number" ? `+${f.additions}` : ""}
                    {typeof f.deletions === "number" ? ` −${f.deletions}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          ) : proof.detail ? (
            <p className="mt-2 line-clamp-3 text-[11px] text-[var(--dim)]">{proof.detail}</p>
          ) : href ? (
            <p className="mt-2 text-[11px] text-[var(--dim)]">Pull request opened on GitHub.</p>
          ) : null}
        </>
      )}
    </Shell>
  );
}

function GmailProof({ proof }: { proof: ProofPayload }) {
  return (
    <Shell
      brand="Gmail"
      icon={Mail}
      title={proof.title || "Mail"}
      subtitle={proof.to || proof.subtitle}
      href={proof.console_url || proof.url}
      lifecycle={proof.status}
    >
      <p className="text-[11px] text-[var(--dim)]">{proof.detail || proof.channel}</p>
    </Shell>
  );
}

function BrandProof({ proof }: { proof: ProofPayload }) {
  const meta = BRAND[proof.kind || ""] || BRAND.gateway;
  return (
    <Shell
      brand={meta.label}
      icon={meta.icon}
      title={proof.title || meta.label}
      subtitle={proof.subtitle || proof.phone || undefined}
      href={proof.console_url || proof.url}
      lifecycle={proof.status}
    >
      {proof.detail ? <p className="text-[11px] leading-4 text-[var(--dim)]">{proof.detail}</p> : null}
      {proof.phone ? <p className="mt-1 font-mono text-[12px] text-foreground">{proof.phone}</p> : null}
    </Shell>
  );
}

function formatCell(v: unknown) {
  if (v == null) return "—";
  if (typeof v === "number") {
    if (v > 0 && v < 1) return `${(v * 100).toFixed(1)}%`;
    return String(v);
  }
  return String(v);
}

/** Mini console for BQ / GA4 / GitHub / Gmail / contacts / … — real data, not a fake iframe. */
export function ProofEmbed({
  proof,
  className,
  compact,
}: {
  proof?: ProofPayload | null;
  className?: string;
  compact?: boolean;
}) {
  if (!proof || !proof.kind) return null;
  const wrap = cn(compact ? "mt-2" : "mt-3", className);
  if (proof.kind === "github")
    return (
      <div className={wrap}>
        <GitHubProof proof={proof} />
      </div>
    );
  if (proof.kind === "gmail")
    return (
      <div className={wrap}>
        <GmailProof proof={proof} />
      </div>
    );
  if (
    proof.kind === "flags" ||
    proof.kind === "memory" ||
    proof.kind === "workspace" ||
    proof.kind === "contacts" ||
    proof.kind === "gateway"
  )
    return (
      <div className={wrap}>
        <BrandProof proof={proof} />
      </div>
    );
  return (
    <div className={wrap}>
      <DataProof proof={proof} />
    </div>
  );
}

/** Responsive grid of live resource cards. */
export function ProofGrid({
  cards,
  className,
  compact,
}: {
  cards?: Array<ProofPayload | null | undefined> | null;
  className?: string;
  compact?: boolean;
}) {
  const items = (cards || []).filter((p): p is ProofPayload => Boolean(p && p.kind));
  if (!items.length) return null;
  return (
    <div className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-3", className)}>
      {items.map((p, i) => (
        <ProofEmbed
          key={`${p.kind}-${p.source || ""}-${p.title || i}-${i}`}
          proof={p}
          className="mt-0"
          compact={compact}
        />
      ))}
    </div>
  );
}

/** Homepage strip — prefer full cards list; fall back to classic trio. */
export function ProofStrip({
  warehouse,
  github,
  ga4,
  cards,
  className,
}: {
  warehouse?: ProofPayload | null;
  github?: ProofPayload | null;
  ga4?: ProofPayload | null;
  cards?: Array<ProofPayload | null | undefined> | null;
  className?: string;
}) {
  if (cards && cards.length) {
    return <ProofGrid cards={cards} className={className} />;
  }
  const analytics =
    ga4 && (ga4.live || (ga4.rows && ga4.rows.length > 0) || ga4.source === "ga4_export")
      ? ga4
      : warehouse && warehouse.source === "file_warehouse" && ga4
        ? ga4
        : warehouse || ga4;
  const items = [analytics, github].filter(Boolean) as ProofPayload[];
  if (!items.length) return null;
  return (
    <div className={cn("grid gap-3 lg:grid-cols-2", className)}>
      {items.map((p, i) => (
        <ProofEmbed key={`${p.kind}-${p.source || i}-${i}`} proof={p} className="mt-0" />
      ))}
    </div>
  );
}
