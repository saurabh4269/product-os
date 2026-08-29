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
const HAIR = ["#2b1b12", "#4a2c14", "#1a1a1a", "#6b3a1f", "#c4a574", "#3d2a5c"];
const SHIRT = [
  "#ff7a45",
  "#6fbf93",
  "#7aa2ff",
  "#e8c36a",
  "#c084fc",
  "#5ec8c8",
  "#ff5a6a",
  "#f6f0e6",
];
const PANTS = ["#2a2438", "#3d3450", "#1c1826", "#40352a"];

export function paletteFor(name: string): Palette {
  if (name === "you") {
    return { k: "#1a1210", s: "#f0c9a0", h: "#2b1b12", t: "#f6f0e6", n: "#2a2438", b: "#1a1210" };
  }
  const n = hashHue(name);
  return {
    k: "#1a1210",
    s: SKIN[n % SKIN.length],
    h: HAIR[(n >> 3) % HAIR.length],
    t: SHIRT[(n >> 5) % SHIRT.length],
    n: PANTS[(n >> 7) % PANTS.length],
    b: "#1a1210",
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
      { k: "#2a1c14", s: "#d9a57a", h: "#2b1b12", t: "#8b5e3c", n: "#2a2438", b: "#1a1210" },
      { o: "#141018", g: "#7dcea0", w: "#8b5e3c" }
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
    <div className={cn("tile-floor relative overflow-hidden", compact ? "h-[88px]" : "h-[120px]")}>
      <div className="absolute inset-0 flex items-end justify-center gap-3 px-4 pb-2">
        {shown.map((name, i) => {
          const isWork = working.has(name);
          return (
            <div key={name} className="relative flex flex-col items-center" style={{ animationDelay: `${i * 80}ms` }}>
              {isWork ? (
                <span className="absolute -top-3 rounded-sm bg-[var(--ink)] px-1 font-sans text-[9px] leading-4 text-[var(--bg)]">
                  …
                </span>
              ) : null}
              <PixelSprite name={name} scale={compact ? 2 : 3} working={isWork} />
              <Desk scale={compact ? 2 : 2} />
              <span className="mt-0.5 max-w-[72px] truncate text-[10px] tracking-wide text-[var(--ink)]/70">
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
  const tone =
    kind === "incident" ? "var(--danger)" : kind === "opportunity" ? "var(--ok)" : kind === "review" ? "var(--warn)" : "var(--accent-2)";
  return (
    <div className="chamber hard-shadow flex h-full flex-col overflow-hidden border border-[var(--line)] bg-[var(--paper)]">
      <PixelOffice members={members} working={working} compact />
      <div className="flex flex-1 flex-col px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 shrink-0" style={{ background: tone }} />
          <p className="text-[11px] uppercase tracking-[0.16em] text-[var(--dim)]">
            {kind}
            {loop === "type_a" ? " · broke" : loop === "type_b" ? " · better" : ""}
          </p>
        </div>
        <h3 className="font-display mt-1 text-[22px] leading-7 tracking-tight">{title}</h3>
        <p className="mt-2 line-clamp-2 text-[13px] leading-5 text-[var(--dim)]">{preview}</p>
      </div>
    </div>
  );
}
