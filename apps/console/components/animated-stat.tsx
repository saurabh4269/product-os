"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function AnimatedStat({
  label,
  value,
  hot,
  flash,
}: {
  label: string;
  value: number | string;
  hot?: boolean;
  flash?: boolean;
}) {
  const [display, setDisplay] = useState<number | string>(value);
  const prev = useRef<number | string>(value);

  useEffect(() => {
    const from = typeof prev.current === "number" ? prev.current : Number(prev.current) || 0;
    const to = typeof value === "number" ? value : Number(value);
    if (Number.isNaN(to) || typeof value !== "number") {
      setDisplay(value);
      prev.current = value;
      return;
    }
    if (from === to) {
      setDisplay(to);
      prev.current = to;
      return;
    }
    const steps = Math.min(Math.abs(to - from), 24);
    if (steps === 0) {
      setDisplay(to);
      prev.current = to;
      return;
    }
    const stepMs = Math.max(20, Math.floor(300 / steps));
    let cur = from;
    const sign = to > from ? 1 : -1;
    const id = window.setInterval(() => {
      cur += sign;
      setDisplay(cur);
      if (cur === to) {
        window.clearInterval(id);
        prev.current = to;
      }
    }, stepMs);
    return () => window.clearInterval(id);
  }, [value]);

  return (
    <div
      className={cn(
        "min-w-[4.5rem] rounded-xl px-1 py-0.5 transition-colors duration-300",
        flash && "bg-accent/10",
        hot && "text-accent"
      )}
    >
      <p className="text-[11px] text-[var(--faint)]">{label}</p>
      <p className={cn("text-[15px] font-semibold tracking-tight text-foreground", hot && "text-accent")}>
        {display}
      </p>
    </div>
  );
}
