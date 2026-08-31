"use client";

import Link from "next/link";
import { useLayoutEffect, useMemo, useRef } from "react";
import { AgentBadge, AgentStack } from "@/components/agent-badge";
import { hashHue, shortName } from "@/lib/names";
import { cn } from "@/lib/utils";

type Palette = {
  k: string;
  s: string;
  h: string;
  t: string;
  n: string;
  b: string;
};

const SKIN = ["#f0c9a0", "#d9a57a", "#c68662", "#8d5524", "#f3d1b8"];
const HAIR = ["#2b1b12", "#4a2c14", "#1a1a1a", "#6b3a1f", "#c4a574", "#4a4a4c"];
const SHIRT = [
  "#5b7c99",
  "#8e8e93",
  "#a3b5c9",
  "#6b7c6e",
  "#c7c1b3",
  "#4a5568",
  "#d4d4d8",
  "#e8e4dc",
];
const PANTS = ["#3a3a3c", "#48484a", "#636366", "#2c2c2e"];

export function paletteFor(name: string): Palette {
  if (name === "you") {
    return { k: "#2c2c2e", s: "#f0c9a0", h: "#2b1b12", t: "#e8e4dc", n: "#3a3a3c", b: "#2c2c2e" };
  }
  const n = hashHue(name);
  return {
    k: "#2c2c2e",
    s: SKIN[n % SKIN.length],
    h: HAIR[(n >> 3) % HAIR.length],
    t: SHIRT[(n >> 5) % SHIRT.length],
    n: PANTS[(n >> 7) % PANTS.length],
    b: "#2c2c2e",
  };
}

/** Standing pose — campus people stay still (no walk cycle). */
const FRAME = [
  "................",
  ".....kkkk.......",
  "....khhhhk......",
  "....khsshk......",
  "....kssssk......",
  "....kskskk......",
  ".....kssk.......",
  "....kttttk......",
  "...kttttttk.....",
  "...ksttts k.....",
  "....kttttk......",
  "....knnnnk......",
  "....kn.knk......",
  "....kb.kbk......",
  "....kk.kkk......",
  "................",
];

function colorOf(ch: string, p: Palette) {
  if (ch === "." || ch === " ") return null;
  if (ch === "k") return p.k;
  if (ch === "s") return p.s;
  if (ch === "h") return p.h;
  if (ch === "t") return p.t;
  if (ch === "n") return p.n;
  if (ch === "b") return p.b;
  return p.k;
}

function paint(ctx: CanvasRenderingContext2D, grid: string[], scale: number, p: Palette) {
  ctx.clearRect(0, 0, grid[0].length * scale, grid.length * scale);
  for (let y = 0; y < grid.length; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const c = colorOf(grid[y][x], p);
      if (!c) continue;
      ctx.fillStyle = c;
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}

/** Little standing people for the campus map — static, no body animation. */
export function PixelSprite({
  name,
  scale = 2,
  working = false,
  className,
}: {
  name: string;
  scale?: number;
  working?: boolean;
  animate?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const pal = useMemo(() => paletteFor(name), [name]);
  const size = 16 * scale;

  useLayoutEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    paint(ctx, FRAME, scale, pal);
  }, [pal, scale]);

  return (
    <canvas
      ref={ref}
      width={size}
      height={size}
      className={cn("pixelated block drop-shadow-sm", working ? "opacity-100" : "opacity-80", className)}
      style={{ width: size, height: size }}
      aria-hidden
    />
  );
}

/** Soft avatar icons (rooms, rails, lists) — not the campus pixel people. */
export function Pixel({ name, size = 16 }: { name: string; size?: number }) {
  return <AgentBadge name={name} size={size} />;
}

export function PixelOffice({
  members,
  working,
  compact = false,
  activity,
  link = true,
}: {
  members: string[];
  working: Set<string>;
  compact?: boolean;
  activity?: Record<string, string>;
  link?: boolean;
  district?: string;
  furniture?: boolean;
}) {
  const shown = members.filter((m) => m !== "system").slice(0, compact ? 5 : 6);
  const workingList = shown.filter((m) => working.has(m));
  const idleList = shown.filter((m) => !working.has(m));
  const ordered = [...workingList, ...idleList];
  const avatarSize = compact ? 32 : 36;

  if (compact) {
    return (
      <div className="flex justify-center px-4 pb-4 pt-6">
        <AgentStack names={ordered} working={working} size={avatarSize} max={5} />
      </div>
    );
  }

  return (
    <div className="px-4 pb-5 pt-6">
      <div className="-mx-1 flex justify-center gap-3 overflow-x-auto px-1 py-2">
        {ordered.map((name) => {
          const isWork = working.has(name);
          const note = isWork ? activity?.[name] : undefined;
          const inner = (
            <div className="flex w-[72px] shrink-0 flex-col items-center gap-1.5">
              {note ? (
                <span className="max-w-full truncate rounded-full bg-white px-2 py-0.5 text-[10px] leading-4 text-[var(--dim)]">
                  {note}
                </span>
              ) : (
                <span className="h-5" aria-hidden />
              )}
              <AgentBadge name={name} working={isWork} size={avatarSize} variant="face" />
              <span className="max-w-full truncate text-center text-[12px] leading-4 text-[var(--dim)]">
                {shortName(name)}
              </span>
            </div>
          );
          return (
            <div key={name}>
              {!link || name === "you" ? (
                inner
              ) : (
                <Link href={`/agents/${name}`} className="hover:opacity-85">
                  {inner}
                </Link>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function HiveChamber({
  title,
  kind,
  preview,
  members,
  loop,
}: {
  title: string;
  kind: string;
  preview: string;
  members: string[];
  loop?: string | null;
}) {
  const label =
    kind === "incident" ? "Incident" : kind === "opportunity" ? "Idea" : kind === "review" ? "Review" : kind;
  return (
    <div className="chamber soft-card flex h-full flex-col overflow-hidden rounded-[22px] border border-border bg-white">
      <PixelOffice members={members} working={new Set()} compact link={false} />
      <div className="flex flex-1 flex-col px-5 py-5">
        <p className="text-[13px] text-[var(--faint)]">
          {label}
          {loop === "type_a" ? " · fix" : loop === "type_b" ? " · improve" : ""}
        </p>
        <h3 className="mt-1 text-[17px] font-semibold leading-6 tracking-tight">{title}</h3>
        <p className="mt-2 line-clamp-3 text-[14px] leading-6 text-[var(--dim)]">{preview}</p>
      </div>
    </div>
  );
}
