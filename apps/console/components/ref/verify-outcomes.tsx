"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Investigation, type Room } from "@/lib/api";
import { dedupeSignals, signalSegmentLabel } from "@/lib/signals";
import { useGlobalWs } from "@/lib/use-global-ws";
import { cn, pct, when } from "@/lib/utils";
import { Empty, ErrorState, Loading } from "@/components/ui";
import { PageHeader, PageStatPill } from "@/components/page-header";
import { MIcon } from "./icon";

type OutcomeRow = {
  id: string;
  investigation_id: string;
  metric: string;
  pre_value: number;
  post_value: number;
  delta: number;
  verdict: string;
  measured_at?: string;
  control_comparison?: number | null;
};

type LessonRow = {
  id: string;
  investigation_id: string;
  statement: string;
  root_cause_family?: string;
  confidence?: number;
  linked_playbook_skill?: string | null;
};

function magLabel(raw: unknown) {
  const n = Number(raw);
  if (Number.isNaN(n)) return "—";
  return Math.abs(n) > 1 ? String(Math.round(n)) : pct(n);
}

function parseMetric(metric: string) {
  const dot = metric.indexOf(".");
  if (dot === -1) return { name: metric.replace(/_/g, " "), segment: null as string | null };
  return {
    name: metric.slice(0, dot).replace(/_/g, " "),
    segment: metric.slice(dot + 1),
  };
}

function verdictMeta(verdict: string) {
  const v = verdict.toUpperCase();
  if (v === "RESOLVED") {
    return { label: "Resolved", tone: "bg-ok/10 text-ok border-ok/25", icon: "check_circle" as const };
  }
  if (v === "PARTIALLY_RESOLVED") {
    return { label: "Partial", tone: "bg-amber-50 text-amber-900 border-amber-200", icon: "adjust" as const };
  }
  if (v === "NOT_RESOLVED") {
    return { label: "Not resolved", tone: "bg-red-50 text-red-800 border-red-200", icon: "cancel" as const };
  }
  return { label: verdict.replace(/_/g, " "), tone: "bg-[var(--elev)] text-[var(--dim)] border-border", icon: "help" as const };
}

function investigationTitle(
  inv: Investigation | undefined,
  room: Room | undefined,
  metric: string
) {
  if (room?.title) return room.title;
  const hyp = (inv as Investigation & { hypothesis?: string })?.hypothesis;
  if (hyp) return hyp;
  if (inv?.scenario_id) return inv.scenario_id.replace(/_/g, " ");
  const { name, segment } = parseMetric(metric);
  return segment ? `${name} · ${segment}` : name;
}

function OpenSignals({ signals }: { signals: Array<Record<string, unknown>> }) {
  const cards = dedupeSignals(signals);
  if (cards.length === 0) return null;

  return (
    <section className="space-y-3">
      <h2 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--dim)]">Watching</h2>
      <div className="flex flex-wrap gap-2">
        {cards.map((s) => {
          const magnitude = Number(s.magnitude);
          const negative = !Number.isNaN(magnitude) && magnitude < 0;
          return (
            <div
              key={String(s.id)}
              className="rounded-xl border border-border bg-white px-3.5 py-2.5 shadow-[0_1px_2px_rgba(29,29,31,0.04)]"
            >
              <p className="text-[11px] text-[var(--faint)]">
                {String(s.metric).replace(/_/g, " ")} · {signalSegmentLabel(s)}
              </p>
              <p
                className={cn(
                  "mt-0.5 text-[17px] font-semibold tabular-nums tracking-tight",
                  negative ? "text-red-600" : "text-ok"
                )}
              >
                {magLabel(s.magnitude)}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function OutcomeCard({
  outcome,
  lesson,
  inv,
  room,
}: {
  outcome: OutcomeRow;
  lesson?: LessonRow;
  inv?: Investigation;
  room?: Room;
}) {
  const { name, segment } = parseMetric(outcome.metric);
  const verdict = verdictMeta(outcome.verdict);
  const pre = outcome.pre_value;
  const post = outcome.post_value;
  const delta = outcome.delta;
  const roomHref = room ? `/rooms/${room.id}?view=lab` : inv?.room_id ? `/rooms/${inv.room_id}?view=lab` : null;
  const improved = Number.isFinite(delta) && delta > 0;

  return (
    <article className="rounded-2xl border border-border bg-white p-5 shadow-[0_1px_2px_rgba(29,29,31,0.04)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                verdict.tone
              )}
            >
              <MIcon name={verdict.icon} className="text-[14px]" />
              {verdict.label}
            </span>
            {inv?.scenario_id ? (
              <span className="font-mono text-[11px] text-[var(--faint)]">{inv.scenario_id}</span>
            ) : null}
          </div>
          <h3 className="mt-2 text-[17px] font-semibold leading-snug tracking-tight text-foreground">
            {investigationTitle(inv, room, outcome.metric)}
          </h3>
          <p className="mt-1 text-[13px] text-[var(--dim)]">
            {name}
            {segment ? ` · ${segment}` : ""}
          </p>
        </div>
        {outcome.measured_at ? (
          <time className="shrink-0 text-[12px] text-[var(--faint)]" dateTime={outcome.measured_at}>
            {when(outcome.measured_at)}
          </time>
        ) : null}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <div className="space-y-3">
          <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">Before</p>
              <p className="text-[28px] font-semibold tabular-nums tracking-tight text-foreground">
                {Number.isFinite(pre) ? pct(pre) : "—"}
              </p>
            </div>
            <MIcon name="arrow_forward" className="hidden text-[20px] text-[var(--faint)] sm:block" />
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wide text-primary">After</p>
              <p className="text-[28px] font-semibold tabular-nums tracking-tight text-primary">
                {Number.isFinite(post) ? pct(post) : "—"}
              </p>
            </div>
            {Number.isFinite(delta) ? (
              <div className="sm:ml-2">
                <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">Delta</p>
                <p
                  className={cn(
                    "text-[20px] font-semibold tabular-nums",
                    improved ? "text-ok" : delta < 0 ? "text-red-600" : "text-[var(--dim)]"
                  )}
                >
                  {delta > 0 ? "+" : ""}
                  {pct(delta)}
                </p>
              </div>
            ) : null}
          </div>

          {Number.isFinite(pre) && Number.isFinite(post) ? (
            <div className="h-2 overflow-hidden rounded-full bg-[var(--elev)]">
              <div
                className="h-full rounded-full bg-primary/25 transition-all"
                style={{ width: `${Math.min(100, Math.max(4, post * 100))}%` }}
              />
            </div>
          ) : null}

          {outcome.control_comparison != null && Number.isFinite(outcome.control_comparison) ? (
            <p className="text-[12px] text-[var(--faint)]">
              Control segment held at {pct(outcome.control_comparison)}
            </p>
          ) : null}
        </div>

        {lesson ? (
          <div className="rounded-xl border border-border/80 bg-[#f8fafc] p-4 sm:max-w-sm">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--faint)]">Lesson</p>
            <p className="mt-2 text-[13px] leading-5 text-foreground">{lesson.statement}</p>
            {lesson.linked_playbook_skill ? (
              <p className="mt-2 font-mono text-[11px] text-[var(--dim)]">{lesson.linked_playbook_skill}</p>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border/70 pt-4">
        {roomHref ? (
          <Link href={roomHref} className="inline-flex items-center gap-1 text-[13px] font-medium text-accent hover:underline">
            Open investigation
            <MIcon name="arrow_forward" className="text-[16px]" />
          </Link>
        ) : null}
        {lesson ? (
          <Link href="/memory" className="text-[13px] text-[var(--dim)] hover:text-foreground">
            Memory bank
          </Link>
        ) : null}
      </div>
    </article>
  );
}

export function VerifyOutcomes() {
  const { tick } = useGlobalWs();
  const [outcomes, setOutcomes] = useState<OutcomeRow[]>([]);
  const [lessons, setLessons] = useState<LessonRow[]>([]);
  const [signals, setSignals] = useState<Array<Record<string, unknown>>>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.outcomes(), api.memory(), api.signals(), api.investigations(), api.rooms()])
      .then(([o, m, sig, inv, r]) => {
        setOutcomes(
          (o.outcomes as OutcomeRow[]).map((row) => ({
            ...row,
            pre_value: Number(row.pre_value),
            post_value: Number(row.post_value),
            delta: Number(row.delta),
          }))
        );
        setLessons((m.lessons ?? []) as LessonRow[]);
        setSignals(sig.signals ?? []);
        setInvestigations(inv.investigations);
        setRooms(r.rooms);
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"))
      .finally(() => setReady(true));
  }, [tick]);

  const lessonByInv = useMemo(
    () => Object.fromEntries(lessons.map((l) => [l.investigation_id, l])),
    [lessons]
  );
  const invById = useMemo(
    () => Object.fromEntries(investigations.map((i) => [i.id, i])),
    [investigations]
  );
  const roomByInv = useMemo(() => {
    const m: Record<string, Room> = {};
    for (const room of rooms) {
      if (room.investigation_id) m[room.investigation_id] = room;
    }
    return m;
  }, [rooms]);

  const sortedOutcomes = useMemo(
    () =>
      [...outcomes].sort((a, b) =>
        String(b.measured_at ?? "").localeCompare(String(a.measured_at ?? ""))
      ),
    [outcomes]
  );

  const resolvedCount = useMemo(
    () => outcomes.filter((o) => o.verdict.toUpperCase() === "RESOLVED").length,
    [outcomes]
  );

  if (err) return <ErrorState message={err} />;
  if (!ready) return <Loading label="Outcomes" />;

  const hasOutcomes = sortedOutcomes.length > 0;
  const hasSignals = dedupeSignals(signals).length > 0;

  return (
    <div className="mx-auto max-w-container-max space-y-margin-lg">
      <PageHeader title="Outcomes">
        <PageStatPill>
          <span className="font-semibold text-text-primary">{outcomes.length}</span> verified
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-ok">{resolvedCount}</span> resolved
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-text-primary">{lessons.length}</span> lessons
        </PageStatPill>
      </PageHeader>

      <OpenSignals signals={signals} />

      {hasOutcomes ? (
        <section className="space-y-4">
          <h2 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--dim)]">Verified</h2>
          <div className="space-y-4">
            {sortedOutcomes.map((outcome) => (
              <OutcomeCard
                key={outcome.id}
                outcome={outcome}
                lesson={lessonByInv[outcome.investigation_id]}
                inv={invById[outcome.investigation_id]}
                room={roomByInv[outcome.investigation_id]}
              />
            ))}
          </div>
        </section>
      ) : hasSignals ? (
        <Empty title="No verified outcomes yet" className="mt-4" />
      ) : (
        <Empty title="No outcomes yet" className="mt-4" />
      )}
    </div>
  );
}
