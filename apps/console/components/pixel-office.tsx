"use client";

import { useLayoutEffect, useMemo, useRef } from "react";
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

const DESK = [
  "................",
  "......oooo......",
  ".....okggko.....",
  ".....okggko.....",
  ".....okkkko.....",
  "..owwwwwwwwwwo..",
  ".owwwwwwwwwwwwo.",
  ".ow..........wo.",
  ".ow..........wo.",
  ".owwwwwwwwwwwwo.",
  "................",
  "................",
  "................",
  "................",
  "................",
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

function Desk({ scale = 2 }: { scale?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    paint(
      ctx,
      DESK,
      scale,
      { k: "#8e8e93", s: "#d9a57a", h: "#2b1b12", t: "#c9b29a", n: "#3a3a3c", b: "#2c2c2e" },
      { o: "#c7c7cc", g: "#dce3ea", w: "#c9b29a" }
    );
  }, [scale]);
  return (
    <canvas
      ref={ref}
      width={16 * scale}
      height={16 * scale}
      className="pixelated block"
      style={{ width: 16 * scale, height: 16 * scale }}
      aria-hidden
    />
  );
}

export function PixelOffice({
  members,
  working,
  compact = false,
}: {
  members: string[];
  working: Set<string>;
  compact?: boolean;
}) {
  const shown = members.filter((m) => m !== "system").slice(0, compact ? 6 : 10);
  return (
    <div className={cn("relative overflow-hidden bg-[var(--floor)]", compact ? "h-[80px]" : "h-[108px]")}>
      <div className="absolute inset-0 flex items-end justify-center gap-4 px-4 pb-2">
        {shown.map((name, i) => {
          const isWork = working.has(name);
          return (
            <div key={name} className="relative flex flex-col items-center" style={{ animationDelay: `${i * 80}ms` }}>
              {isWork ? (
                <span className="absolute -top-3 rounded-full bg-white px-2 font-sans text-[10px] leading-4 text-[var(--dim)]">
                  …
                </span>
              ) : null}
              <PixelSprite name={name} scale={compact ? 2 : 3} working={isWork} />
              <Desk scale={compact ? 2 : 2} />
              <span className="mt-0.5 max-w-[72px] truncate text-[11px] text-[var(--dim)]">
                {shortName(name)}
              </span>
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
    <div className="chamber soft-card flex h-full flex-col overflow-hidden rounded-[20px] border border-border bg-white">
      <PixelOffice members={members} working={working} compact />
      <div className="flex flex-1 flex-col px-5 py-4">
        <p className="text-[12px] text-[var(--faint)]">
          {label}
          {loop === "type_a" ? " · fix" : loop === "type_b" ? " · improve" : ""}
        </p>
        <h3 className="mt-1 text-[17px] font-semibold leading-6 tracking-tight">{title}</h3>
        <p className="mt-1 line-clamp-2 text-[13px] leading-5 text-[var(--dim)]">{preview}</p>
      </div>
    </div>
  );
}
