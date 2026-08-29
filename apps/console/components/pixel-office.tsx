"use client";

import Link from "next/link";
import { useLayoutEffect, useMemo, useRef } from "react";
import { FurnitureSet } from "@/components/pixel-furniture";
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

const FRAME_A = [
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

const FRAME_B = [
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
  "...kkn..knk.....",
  "...kbk..kbk.....",
  "...kkk..kkk.....",
  "................",
];

function colorOf(ch: string, p: Palette, extra?: Record<string, string>) {
  if (ch === "." || ch === " ") return null;
  if (ch === "k") return p.k;
  if (ch === "s") return p.s;
  if (ch === "h") return p.h;
  if (ch === "t") return p.t;
  if (ch === "n") return p.n;
  if (ch === "b") return p.b;
  if (extra && extra[ch]) return extra[ch];
  return p.k;
}

function paint(
  ctx: CanvasRenderingContext2D,
  grid: string[],
  scale: number,
  p: Palette,
  extra?: Record<string, string>
) {
  ctx.clearRect(0, 0, grid[0].length * scale, grid.length * scale);
  for (let y = 0; y < grid.length; y++) {
    for (let x = 0; x < grid[y].length; x++) {
      const c = colorOf(grid[y][x], p, extra);
      if (!c) continue;
      ctx.fillStyle = c;
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}

export function PixelSprite({
  name,
  scale = 3,
  working = false,
  className,
}: {
  name: string;
  scale?: number;
  working?: boolean;
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
    let frame = 0;
    const tick = () => {
      paint(ctx, frame % 2 === 0 ? FRAME_A : FRAME_B, scale, pal);
      frame += 1;
    };
    tick();
    const ms = working ? 180 : 520;
    const id = window.setInterval(tick, ms);
    return () => window.clearInterval(id);
  }, [pal, scale, working]);

  return (
    <canvas
      ref={ref}
      width={size}
      height={size}
      className={cn("pixelated agent-bob block", working && "is-working", className)}
      style={{ width: size, height: size }}
      aria-hidden
    />
  );
}

export function Pixel({ name, size = 16 }: { name: string; size?: number }) {
  const scale = Math.max(1, Math.round(size / 16));
  return <PixelSprite name={name} scale={scale} />;
}

export function PixelOffice({
  members,
  working,
  compact = false,
  activity,
  link = true,
  district,
}: {
  members: string[];
  working: Set<string>;
  compact?: boolean;
  activity?: Record<string, string>;
  link?: boolean;
  district?: string;
}) {
  const shown = members.filter((m) => m !== "system").slice(0, compact ? 4 : 8);
  return (
    <div className={cn("bg-[var(--floor)]", compact ? "px-4 pb-4 pt-6" : "px-4 pb-5 pt-6")}>
      <div className="-mx-1 flex justify-center gap-4 overflow-x-auto overflow-y-visible px-1 py-2">
        {shown.map((name, i) => {
          const isWork = working.has(name);
          const note = compact ? undefined : activity?.[name];
          const inner = (
            <>
              {note ? (
                <span className="mb-1.5 max-w-[92px] truncate rounded-full bg-white px-2 py-0.5 font-sans text-[10px] leading-4 text-[var(--dim)]">
                  {note}
                </span>
              ) : null}
              <PixelSprite name={name} scale={3} working={isWork} />
              {compact ? null : <FurnitureSet name={name} district={district} working={isWork} scale={2} />}
              <span className="mt-1.5 max-w-[84px] truncate text-center text-[12px] leading-4 text-[var(--dim)]">
                {shortName(name)}
              </span>
            </>
          );
          return (
            <div
              key={name}
              className="flex shrink-0 flex-col items-center"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              {!link || name === "you" || name === "system" ? (
                inner
              ) : (
                <Link href={`/agents/${name}`} className="flex flex-col items-center hover:opacity-80">
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
  const working = new Set(members.slice(0, 3));
  const label =
    kind === "incident" ? "Incident" : kind === "opportunity" ? "Idea" : kind === "review" ? "Review" : kind;
  return (
    <div className="chamber soft-card flex h-full flex-col overflow-hidden rounded-[22px] border border-border bg-white">
      <PixelOffice members={members} working={working} compact link={false} />
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
