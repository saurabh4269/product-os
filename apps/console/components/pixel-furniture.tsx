"use client";

import { useLayoutEffect, useRef } from "react";
import { extrasOf, furnitureFor, type PixelGrid } from "@/lib/furniture";
import { cn } from "@/lib/utils";

function paint(ctx: CanvasRenderingContext2D, item: PixelGrid, scale: number) {
  const w = item.grid[0].length;
  const h = item.grid.length;
  ctx.clearRect(0, 0, w * scale, h * scale);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const ch = item.grid[y][x];
      if (ch === "." || ch === " ") continue;
      ctx.fillStyle = item.colors[ch] ?? "#2c2c2e";
      ctx.fillRect(x * scale, y * scale, scale, scale);
    }
  }
}

export function PixelItem({
  item,
  scale = 2,
  className,
}: {
  item: PixelGrid;
  scale?: number;
  className?: string;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const w = item.grid[0].length * scale;
  const h = item.grid.length * scale;

  useLayoutEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.imageSmoothingEnabled = false;
    paint(ctx, item, scale);
  }, [item, scale]);

  return (
    <canvas
      ref={ref}
      width={w}
      height={h}
      className={cn("pixelated block", className)}
      style={{ width: w, height: h }}
      aria-hidden
    />
  );
}

export function FurnitureSet({
  name,
  district,
  working = false,
  scale = 2,
  compact = false,
}: {
  name: string;
  district?: string;
  working?: boolean;
  scale?: number;
  compact?: boolean;
}) {
  const set = furnitureFor(name, district, working);
  const desk = set.items.find((i) => i.kind === "desk");
  const extras = extrasOf(set).slice(0, compact ? 1 : 2);

  return (
    <div className="flex items-end justify-center gap-0.5" aria-hidden>
      {extras[0] ? <PixelItem item={extras[0]} scale={Math.max(1, scale - 1)} /> : null}
      {desk ? <PixelItem item={desk} scale={scale} /> : null}
      {extras[1] ? <PixelItem item={extras[1]} scale={Math.max(1, scale - 1)} /> : null}
    </div>
  );
}
