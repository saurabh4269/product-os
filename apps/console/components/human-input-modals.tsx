"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useHumanInput } from "@/lib/human-input-context";
import { useToast } from "@/lib/toast-context";
import { Button } from "@/components/ui";

export function OAuthModal() {
  const hitl = useHumanInput();
  const pending = hitl?.pendingOAuth;
  const [copied, setCopied] = useState(false);

  if (!pending) return null;

  const authorize = pending.authorize_url.startsWith("http")
    ? pending.authorize_url
    : `${typeof window !== "undefined" ? window.location.origin : ""}${pending.authorize_url}`;

  async function copyRedirect() {
    if (!pending?.redirect_uri) return;
    try {
      await navigator.clipboard.writeText(pending.redirect_uri);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="fixed inset-0 z-[65] flex items-end justify-center bg-black/20 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-xl" role="dialog">
        <p className="text-[13px] text-[var(--faint)]">Google</p>
        <h2 className="mt-1 text-[20px] font-semibold tracking-tight">Connect Calendar and Gmail</h2>
        <p className="mt-3 text-[14px] leading-6 text-[var(--dim)]">
          {pending.reason || "One-time Google consent. Calendar holds, and mail only to your inbox."}
        </p>
        {pending.redirect_uri ? (
          <div className="mt-4 rounded-xl border border-border bg-[#eef2ee] px-3 py-2">
            <p className="text-[11px] text-[var(--faint)]">Redirect URI (add on your Web client)</p>
            <p className="mt-1 break-all font-mono text-[11px] text-foreground">{pending.redirect_uri}</p>
            <button type="button" className="mt-2 text-[12px] text-accent hover:underline" onClick={() => void copyRedirect()}>
              {copied ? "Copied" : "Copy redirect URI"}
            </button>
          </div>
        ) : null}
        <div className="mt-5 flex flex-wrap gap-2">
          <a href={authorize} className="inline-flex">
            <Button type="button">Authorize in Google</Button>
          </a>
          <Button variant="ghost" onClick={() => hitl?.dismissOAuth()}>
            Not now
          </Button>
          <a href="/settings" className="self-center text-[13px] text-accent hover:underline">
            Connect desk
          </a>
        </div>
      </div>
    </div>
  );
}

export function CalendarSlotModal() {
  const hitl = useHumanInput();
  const toast = useToast();
  const pending = hitl?.pendingCalendar;
  const [pick, setPick] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  if (!pending?.slots?.length) return null;

  const selected = pending.slots.find((s) => s.start === pick) || pending.slots[0];

  async function confirm() {
    if (!selected) return;
    setBusy(true);
    setErr(null);
    try {
      const out = await api.coordinate({
        kind: "review_request",
        title: pending!.title,
        room_id: pending!.room_id,
        action_id: pending!.action_id,
        risk_tier: "HIGH",
        apply_calendar: true,
        dimensions: { forced_slot: selected },
        notify_channels: ["gmail_draft", "room"],
      });
      const coord = out.coordination as { slot?: { event_url?: string; start?: string } } | undefined;
      const url = coord?.slot?.event_url;
      const when = coord?.slot?.start;
      toast?.push("Calendar hold placed", { href: url, hot: true });
      setDone(url || when || "Scheduled");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Schedule failed");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    const isUrl = done.startsWith("http");
    return (
      <div className="fixed inset-0 z-[65] flex items-end justify-center bg-black/20 p-4 sm:items-center">
        <div className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-xl">
          <p className="text-[13px] text-[var(--faint)]">Calendar</p>
          <h2 className="mt-1 text-[20px] font-semibold tracking-tight">Hold placed</h2>
          <p className="mt-3 text-[14px] text-[var(--dim)]">
            {isUrl ? "Open in Google Calendar or Meet." : done}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {isUrl ? (
              <a href={done} target="_blank" rel="noreferrer">
                <Button type="button">Open Calendar / Meet</Button>
              </a>
            ) : null}
            <Button variant={isUrl ? "ghost" : undefined} onClick={() => hitl?.dismissCalendar()}>
              Done
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[65] flex items-end justify-center bg-black/20 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-xl" role="dialog">
        <p className="text-[13px] text-[var(--faint)]">Pick a time</p>
        <h2 className="mt-1 text-[20px] font-semibold tracking-tight">{pending.title}</h2>
        <p className="mt-2 text-[14px] text-[var(--dim)]">Confirm to create a calendar hold when Google is connected.</p>
        <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
          {pending.slots.map((s) => (
            <li key={s.start}>
              <button
                type="button"
                onClick={() => setPick(s.start)}
                className={
                  "w-full rounded-xl border px-3 py-2 text-left text-[13px] transition-colors " +
                  ((pick || pending.slots[0]?.start) === s.start
                    ? "border-accent bg-[color-mix(in_srgb,var(--accent)_8%,white)]"
                    : "border-border hover:border-accent/30")
                }
              >
                {new Date(s.start).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                {" → "}
                {new Date(s.end).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => void confirm()} disabled={busy}>
            {busy ? "Scheduling…" : "Confirm slot"}
          </Button>
          <Button variant="ghost" onClick={() => hitl?.dismissCalendar()} disabled={busy}>
            Skip
          </Button>
        </div>
        {err ? <p className="mt-3 text-[13px] text-red-600">{err}</p> : null}
      </div>
    </div>
  );
}

/** Both HITL modals — mount once in shell. */
export function HumanInputModals() {
  return (
    <>
      <OAuthModal />
      <CalendarSlotModal />
    </>
  );
}
