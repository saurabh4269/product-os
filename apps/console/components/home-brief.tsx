"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { dismissBriefSession, dismissWelcome, isBriefDismissedSession, isFirstVisit } from "@/lib/first-visit";
import type { HomePulse, PulseAction } from "@/lib/home-pulse";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function runAction(action: PulseAction) {
  if (action === "pipeline" || action === "approvals") {
    scrollTo("work");
    return;
  }
  if (action === "connect") {
    window.location.assign("/connect");
    return;
  }
  if (action === "explore") {
    scrollTo("rooms");
    return;
  }
}

export function HomeBrief({
  pulse,
  className,
  onDismiss,
}: {
  pulse: HomePulse | null;
  className?: string;
  onDismiss?: () => void;
}) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!pulse?.brief) {
      setShow(false);
      return;
    }
    if (pulse.brief.full) {
      setShow(isFirstVisit());
      return;
    }
    if (pulse.campusHot) {
      setShow(true);
      return;
    }
    setShow(!isBriefDismissedSession());
  }, [pulse]);

  if (!show || !pulse?.brief) return null;

  const { brief } = pulse;

  function close() {
    if (brief.full) dismissWelcome();
    else dismissBriefSession();
    onDismiss?.();
    setShow(false);
  }

  function primary() {
    if (brief.full) dismissWelcome();
    else dismissBriefSession();
    onDismiss?.();
    setShow(false);
    runAction(brief.primary.action);
  }

  function exploreOwn() {
    dismissWelcome();
    onDismiss?.();
    setShow(false);
    window.location.assign("/outcomes");
  }

  return (
    <div
      className={cn(
        "pointer-events-auto absolute left-4 right-4 top-16 z-40 mx-auto max-w-md sm:left-8 sm:top-20 sm:right-auto",
        brief.full ? "" : "max-w-sm",
        className
      )}
    >
      <div
        className={cn(
          "rounded-2xl border bg-white/95 shadow-[0_12px_40px_rgba(0,0,0,0.1)] backdrop-blur-md",
          pulse.campusHot ? "border-accent/30" : "border-black/8",
          brief.full ? "p-4 sm:p-5" : "p-4"
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">{brief.kicker}</p>
          {!brief.full && !pulse.campusHot ? (
            <button
              type="button"
              onClick={close}
              className="shrink-0 rounded-lg px-2 py-0.5 text-[11px] text-[var(--faint)] hover:bg-[var(--elev)] hover:text-foreground"
            >
              Dismiss
            </button>
          ) : null}
        </div>
        <h2 className={cn("mt-1 font-semibold tracking-tight text-foreground", brief.full ? "text-[20px]" : "text-[17px]")}>
          {brief.title}
        </h2>
        {brief.body ? (
          <p className={cn("mt-2 leading-6 text-[var(--dim)]", brief.full ? "text-[14px]" : "text-[13px]")}>{brief.body}</p>
        ) : null}

        {brief.steps?.length ? (
          <ol className="mt-4 flex gap-2">
            {brief.steps.map((s) => (
              <li key={s.n} className="flex-1 rounded-xl bg-[var(--floor)] px-3 py-2 text-center">
                <p className="text-[11px] font-semibold text-accent">{s.n}</p>
                <p className="mt-0.5 text-[12px] font-medium">{s.label}</p>
              </li>
            ))}
          </ol>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={primary} className={cn(brief.full && "cta-pulse px-5")}>
            {brief.primary.label}
          </Button>
          {brief.full ? (
            <Button variant="ghost" onClick={exploreOwn}>
              Outcomes
            </Button>
          ) : brief.secondary ? (
            brief.secondary.href.startsWith("#") ? (
              <Button variant="ghost" onClick={() => scrollTo(brief.secondary!.href.slice(1))}>
                {brief.secondary.label}
              </Button>
            ) : (
              <Link
                href={brief.secondary.href}
                onClick={close}
                className="inline-flex items-center rounded-xl px-4 py-2 text-[13px] font-medium text-[var(--dim)] hover:bg-[var(--elev)] hover:text-foreground"
              >
                {brief.secondary.label}
              </Link>
            )
          ) : null}
        </div>
      </div>
    </div>
  );
}
