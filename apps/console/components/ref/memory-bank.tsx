"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Investigation, type Room } from "@/lib/api";
import { PageHeader, PageStatPill } from "@/components/page-header";
import { useGlobalWs } from "@/lib/use-global-ws";
import { cn, when } from "@/lib/utils";
import { Empty, ErrorState, Loading } from "@/components/ui";
import { MIcon } from "./icon";

const KINDS = ["customer", "product", "engineering", "organizational"] as const;
type MemoryKind = (typeof KINDS)[number];

const CLUSTER_META: Record<MemoryKind, { label: string; icon: string }> = {
  customer: { label: "Customer Memory", icon: "groups" },
  product: { label: "Product Memory", icon: "inventory_2" },
  engineering: { label: "Engineering Memory", icon: "terminal" },
  organizational: { label: "Organizational Memory", icon: "menu_book" },
};

function memoryLine(card: Record<string, unknown>): string {
  if (typeof card.statement === "string" && card.statement.trim()) return card.statement;
  if (typeof card.title === "string" && card.title.trim()) {
    const body = typeof card.body === "string" ? card.body.trim() : "";
    return body ? `${card.title} — ${body}` : card.title;
  }
  if (typeof card.text === "string" && card.text.trim()) return card.text;
  const structured = card.structured;
  if (structured && typeof structured === "object") {
    const o = structured as Record<string, unknown>;
    if (typeof o.statement === "string") return o.statement;
    if (typeof o.reason === "string") return o.reason.replace(/_/g, " ");
  }
  if (typeof card.reason === "string") return card.reason.replace(/_/g, " ");
  return "";
}

function memoryLabel(card: Record<string, unknown>): string {
  const family = card.root_cause_family;
  if (typeof family === "string" && family.trim()) return family.replace(/_/g, " ");
  if (typeof card.provenance === "string" && card.provenance.trim()) return card.provenance;
  if (typeof card.title === "string" && card.title.trim()) return card.title;
  return "entry";
}

function matchesQuery(text: string, q: string): boolean {
  return text.toLowerCase().includes(q.trim().toLowerCase());
}

function humanizeToken(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  return value.replace(/_/g, " ");
}

type RecallRow = {
  id: string;
  at?: string;
  title: string;
  body: string;
  kind: "recall" | "lesson" | "activity";
  roomId?: string;
  icon: string;
};

function MemorySector({
  kind,
  cards,
  highlight,
}: {
  kind: MemoryKind;
  cards: Array<Record<string, unknown>>;
  highlight?: boolean;
}) {
  const meta = CLUSTER_META[kind];

  return (
    <section
      className={cn(
        "flex min-h-[220px] flex-col rounded-xl border border-outline-variant/80 bg-white p-4 shadow-[0_1px_2px_rgba(29,29,31,0.04)]",
        highlight && "ring-1 ring-accent/20"
      )}
    >
      <div className="mb-3 flex items-center gap-2 border-b border-outline-variant/60 pb-2">
        <div className="flex h-6 w-6 items-center justify-center rounded bg-[#131b2e] text-white">
          <MIcon name={meta.icon} className="text-[16px]" />
        </div>
        <h3 className="text-headline-sm font-semibold text-text-primary">{meta.label}</h3>
        <span className="ml-auto font-mono text-[11px] text-text-secondary">{cards.length}</span>
      </div>
      <div className="custom-scrollbar flex flex-1 flex-col gap-2 overflow-y-auto pr-1">
        {cards.length === 0 ? (
          <p className="py-6 text-center text-body-sm text-text-secondary">No entries yet</p>
        ) : (
          cards.slice(0, 6).map((card, i) => {
            const text = memoryLine(card);
            const label = memoryLabel(card);
            const conf = typeof card.confidence === "number" ? card.confidence : null;
            const hot = kind === "engineering" && /safari|sdk|regression/i.test(text);
            return (
              <article
                key={String(card.id ?? i)}
                className={cn(
                  "rounded-lg border border-outline-variant/70 p-3 transition-colors hover:bg-surface-container-low",
                  hot && "border-secondary/30 bg-[#EEF2FF]"
                )}
              >
                <div className="mb-1 flex items-start justify-between gap-2">
                  <span
                    className={cn(
                      "text-[10px] font-bold uppercase tracking-wide",
                      hot ? "text-secondary" : "text-text-secondary"
                    )}
                  >
                    {label}
                  </span>
                  {conf != null ? (
                    <span className="shrink-0 font-mono text-[10px] text-text-secondary">
                      {Math.round(conf * 100)}%
                    </span>
                  ) : null}
                </div>
                <p className="text-body-sm leading-snug text-text-primary">{text || "—"}</p>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}

function RecallPanel({ rows }: { rows: RecallRow[] }) {
  return (
    <aside className="relative flex flex-col overflow-hidden rounded-xl border border-outline-variant/80 bg-white shadow-[0_1px_2px_rgba(29,29,31,0.04)] xl:min-h-[480px]">
      <div className="relative z-10 flex items-center justify-between border-b border-outline-variant/60 px-4 py-3">
        <div className="flex items-center gap-2">
          <MIcon name="history" className="text-secondary" />
          <h3 className="text-headline-sm font-semibold text-text-primary">Recall</h3>
        </div>
        <span className="text-[10px] font-bold uppercase tracking-wide text-text-secondary">
          {rows.length} events
        </span>
      </div>
      <div className="custom-scrollbar relative flex-1 overflow-y-auto p-4">
        {rows.length === 0 ? (
          <p className="py-8 text-center text-body-sm text-text-secondary">No recall events yet</p>
        ) : (
          <div className="relative space-y-4 pl-8">
            <div className="absolute bottom-2 left-[11px] top-2 border-l border-dashed border-outline-variant" />
            {rows.map((row) => (
              <div key={row.id} className="relative">
                <div
                  className={cn(
                    "absolute -left-8 top-2 flex h-6 w-6 items-center justify-center rounded-full border-2 border-white shadow-sm",
                    row.kind === "recall" ? "bg-secondary-container text-white" : "bg-surface-variant text-on-surface-variant"
                  )}
                >
                  <MIcon name={row.icon} className="text-[14px]" />
                </div>
                <div className="rounded-lg border border-outline-variant/70 bg-white p-3 shadow-sm">
                  {row.at ? (
                    <p className="mb-1 font-mono text-[10px] uppercase tracking-wide text-text-secondary">
                      {when(row.at)}
                    </p>
                  ) : null}
                  <p className="text-body-sm font-medium text-text-primary">{row.title}</p>
                  <p className="mt-1 text-body-sm leading-snug text-text-secondary">{row.body}</p>
                  {row.roomId ? (
                    <Link
                      href={`/rooms/${row.roomId}`}
                      className="mt-2 inline-flex items-center gap-1 text-[12px] font-medium text-accent hover:underline"
                    >
                      Open room
                      <MIcon name="arrow_forward" className="text-[14px]" />
                    </Link>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

/** Memory bank — four clusters + live recall from lessons, investigations, activity. */
export function MemoryBank() {
  const { tick } = useGlobalWs();
  const [data, setData] = useState<Awaited<ReturnType<typeof api.memory>> | null>(null);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [activity, setActivity] = useState<Awaited<ReturnType<typeof api.activity>>["events"]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    Promise.all([api.memory(), api.investigations(), api.rooms(), api.activity()])
      .then(([mem, inv, r, act]) => {
        setData(mem);
        setInvestigations(inv.investigations);
        setRooms(r.rooms);
        setActivity(act.events ?? []);
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, [tick]);

  const filtered = useMemo(() => {
    if (!data) return null;
    const q = query.trim();
    if (!q) return data;

    const lessons = data.lessons.filter((lesson) => {
      const blob = [
        lesson.statement,
        lesson.root_cause_family,
        ...(Array.isArray(lesson.applicable_conditions) ? lesson.applicable_conditions : []),
        lesson.linked_playbook_skill,
      ]
        .filter(Boolean)
        .join(" ");
      return matchesQuery(blob, q);
    });

    const memory = Object.fromEntries(
      KINDS.map((kind) => [
        kind,
        (data.memory[kind] ?? []).filter((card) => matchesQuery(memoryLine(card), q)),
      ])
    ) as Record<MemoryKind, Array<Record<string, unknown>>>;

    return { lessons, memory };
  }, [data, query]);

  const roomByInv = useMemo(() => {
    const m: Record<string, Room> = {};
    for (const room of rooms) {
      if (room.investigation_id) m[room.investigation_id] = room;
    }
    return m;
  }, [rooms]);

  const recallRows = useMemo(() => {
    if (!filtered) return [] as RecallRow[];
    const rows: RecallRow[] = [];

    for (const inv of investigations) {
      for (const stmt of inv.recalled_lessons ?? []) {
        if (!stmt.trim()) continue;
        if (query.trim() && !matchesQuery(stmt, query)) continue;
        const room = roomByInv[inv.id];
        rows.push({
          id: `recall-${inv.id}-${stmt.slice(0, 24)}`,
          at: inv.opened_at,
          title: "Memory recalled during investigation",
          body: stmt,
          kind: "recall",
          roomId: room?.id ?? inv.room_id ?? undefined,
          icon: "memory",
        });
      }
    }

    for (const lesson of filtered.lessons.slice(0, 8)) {
      const statement = String(lesson.statement ?? "");
      if (!statement) continue;
      rows.push({
        id: `lesson-${String(lesson.id)}`,
        title: humanizeToken(lesson.root_cause_family) ?? "Lesson committed",
        body: statement,
        kind: "lesson",
        icon: "library_add_check",
      });
    }

    for (const ev of activity) {
      const msg = String(ev.message ?? "");
      if (!/memory|recall|lesson/i.test(msg)) continue;
      if (query.trim() && !matchesQuery(msg, query)) continue;
      rows.push({
        id: `act-${ev.ts}-${ev.agent_id}`,
        at: ev.ts,
        title: ev.agent_id ? String(ev.agent_id).replace(/_agent$/, "") : "activity",
        body: msg,
        kind: "activity",
        roomId: ev.room_id || undefined,
        icon: "search_insights",
      });
    }

    return rows.slice(0, 12);
  }, [filtered, investigations, roomByInv, activity, query]);

  if (err) return <ErrorState message={err} />;
  if (!data || !filtered) return <Loading label="Memory" />;

  const totalAll = KINDS.reduce((sum, kind) => sum + (filtered.memory[kind]?.length ?? 0), 0);
  const isEmpty = filtered.lessons.length === 0 && totalAll === 0;

  return (
    <div className="mx-auto max-w-container-max space-y-margin-lg">
      <PageHeader title="Memory">
        <PageStatPill>
          <span className="font-semibold text-text-primary">{totalAll}</span> entries
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-text-primary">{filtered.lessons.length}</span> lessons
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-text-primary">{recallRows.length}</span> recalls
        </PageStatPill>
      </PageHeader>

      {data.mirror?.enabled && !data.mirror.operational ? (
        <div className="rounded-xl border border-amber-200/80 bg-amber-50 px-4 py-3 text-body-sm text-amber-950">
          <p className="font-medium">Cloud Firestore mirror is off</p>
          <p className="mt-1 text-[13px] leading-5 text-amber-900/90">
            Lessons stay in hosted SQLite for this deploy. Firestore is not mirroring (
            {data.mirror.skipped_reason || data.mirror.last_error || "API unavailable"}).
          </p>
        </div>
      ) : null}

      <div className="relative max-w-md">
        <MIcon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search memory…"
          className="w-full rounded-full border border-border bg-white py-2 pl-10 pr-4 text-body-md outline-none placeholder:text-text-secondary focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {isEmpty ? (
        <Empty
          title={query.trim() ? "No matches" : "Memory is empty"}
          hint={query.trim() ? undefined : "Verified lessons and recall cards land here after investigations."}
          className="mt-8"
        />
      ) : (
        <div className="grid grid-cols-1 gap-gutter xl:grid-cols-12">
          <div className="grid grid-cols-1 gap-gutter md:grid-cols-2 xl:col-span-8">
            {KINDS.map((kind) => (
              <MemorySector
                key={kind}
                kind={kind}
                cards={filtered.memory[kind] ?? []}
                highlight={Boolean(query.trim()) && (filtered.memory[kind]?.length ?? 0) > 0}
              />
            ))}
          </div>
          <div className="xl:col-span-4">
            <RecallPanel rows={recallRows} />
          </div>
        </div>
      )}
    </div>
  );
}
