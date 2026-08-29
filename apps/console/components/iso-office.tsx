"use client";

import type { Handoff, OfficeDesk, Room } from "@/lib/api";
import { DISTRICTS } from "@/lib/campus";
import { furnitureFor } from "@/lib/furniture";
import { PixelItem } from "@/components/pixel-furniture";
import { PixelSprite } from "@/components/pixel-office";
import { shortName } from "@/lib/names";
import { cn } from "@/lib/utils";

const TILE = { w: 72, h: 36 };
const CELL = { w: 110, h: 100 };

function iso(col: number, row: number) {
  return {
    left: (col - row) * (CELL.w / 2),
    top: (col + row) * (CELL.h / 2),
  };
}

const FLOOR: Record<string, string> = {
  Incidents: "#efe8df",
  Ideas: "#eef0e4",
  Reviews: "#eceaf0",
  Research: "#e6ecef",
  Ops: "#e9eee9",
  Office: "#ececec",
};

function layout(desks: OfficeDesk[], cols = 3) {
  return desks.map((desk, i) => ({
    desk,
    col: i % cols,
    row: Math.floor(i / cols),
  }));
}

function Tile({
  desk,
  col,
  row,
  active,
  onPick,
}: {
  desk: OfficeDesk;
  col: number;
  row: number;
  active: boolean;
  onPick: () => void;
}) {
  const pos = iso(col, row);
  const busy = desk.status !== "idle";
  const set = furnitureFor(desk.id, desk.district, busy);
  const extras = set.items.filter((i) => i.kind !== "desk" && i.kind !== "chair");
  const deskItem = set.items.find((i) => i.kind === "desk");

  return (
    <button
      type="button"
      onClick={onPick}
      className="absolute touch-manipulation"
      style={{ left: pos.left, top: pos.top, width: TILE.w, height: TILE.h + 54 }}
      aria-label={`${desk.display_name}${busy ? `, ${desk.doing}` : ""}`}
    >
      <span
        className={cn(
          "absolute left-0 top-8 block h-9 w-full transition",
          active ? "opacity-100" : "opacity-90"
        )}
        style={{
          background: FLOOR[desk.district] ?? FLOOR.Office,
          clipPath: "polygon(50% 0, 100% 50%, 50% 100%, 0 50%)",
          boxShadow: active ? "0 8px 18px rgba(29,29,31,0.12)" : "0 2px 0 rgba(29,29,31,0.04)",
          filter: active ? "brightness(1.04)" : undefined,
        }}
      />
      <span className="absolute left-1/2 top-1 flex -translate-x-1/2 flex-col items-center">
        <PixelSprite name={desk.id} scale={2} working={busy} />
        {deskItem ? <PixelItem item={deskItem} scale={2} className="-mt-1" /> : null}
        <span className="-mt-1 flex items-end">
          {extras.slice(0, 2).map((item) => (
            <PixelItem key={item.kind} item={item} scale={1} />
          ))}
        </span>
        <span className="mt-0.5 max-w-[72px] truncate text-[11px] font-medium leading-3 text-[#1d1d1f]">
          {shortName(desk.id)}
        </span>
      </span>
    </button>
  );
}

export function IsoOffice({
  desks,
  rooms,
  handoffs,
  focus,
  picked,
  onPickRoom,
  onPickDistrict,
}: {
  desks: OfficeDesk[];
  rooms: Room[];
  handoffs: Handoff[];
  focus?: string | null;
  picked?: string | null;
  onPickRoom: (roomId: string | null, district?: string) => void;
  onPickDistrict?: (district: string) => void;
}) {
  const shown = DISTRICTS.filter((d) => {
    if (focus && d !== focus) return false;
    return desks.some((desk) => desk.district === d);
  });

  return (
    <section className="rounded-[24px] border border-border bg-white">
      <div className="flex flex-col gap-1 px-5 pt-6 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <div>
          <p className="text-[13px] text-[var(--faint)]">Inside the buildings</p>
          <h2 className="mt-1 text-[22px] font-semibold tracking-tight">
            {focus ? focus : "A true floor"}
          </h2>
        </div>
        <p className="text-[13px] text-[var(--dim)]">
          {focus ? "Tap a desk to read the work." : "Each tile is a person. Tap one to go deeper."}
        </p>
      </div>

      <div className="flex gap-2 overflow-x-auto px-5 pt-4 sm:px-6">
        {DISTRICTS.filter((d) => desks.some((desk) => desk.district === d)).map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => onPickDistrict?.(d)}
            className={cn(
              "shrink-0 rounded-full px-3 py-1.5 text-[12px] touch-manipulation",
              focus === d ? "bg-[#1d1d1f] text-white" : "bg-[var(--elev)] text-[var(--dim)] hover:text-foreground"
            )}
          >
            {d}
          </button>
        ))}
        {focus ? (
          <button
            type="button"
            onClick={() => onPickDistrict?.("")}
            className="shrink-0 rounded-full px-3 py-1.5 text-[12px] text-[var(--faint)] touch-manipulation"
          >
            All buildings
          </button>
        ) : null}
      </div>

      <div className="overflow-x-auto overflow-y-visible px-4 pb-8 pt-6 sm:px-8">
        <div className="flex min-w-max items-start gap-16 pb-4 pt-2">
          {shown.map((district) => {
            const group = desks.filter((d) => d.district === district);
            const placed = layout(group, focus ? 4 : 3);
            const cols = Math.min(focus ? 4 : 3, group.length);
            const rows = Math.ceil(group.length / Math.max(cols, 1));
            const width = cols * CELL.w + rows * (CELL.w / 2) + 56;
            const height = (cols + rows) * (CELL.h / 2) + 96;

            return (
              <div key={district} className="relative shrink-0" style={{ width, height }}>
                <p className="absolute left-0 top-0 text-[12px] text-[var(--faint)]">{district}</p>
                <div className="absolute left-1/2 top-8" style={{ transform: "translateX(-30%)" }}>
                  {placed.map(({ desk, col, row }) => (
                    <Tile
                      key={desk.id}
                      desk={desk}
                      col={col}
                      row={row}
                      active={picked === desk.room_id}
                      onPick={() => onPickRoom(desk.room_id ?? null, district)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {handoffs.slice(-2).length ? (
        <p className="border-t border-border px-5 py-4 text-[13px] text-[var(--dim)] sm:px-6">
          Latest handoff · {handoffs.slice(-1)[0]?.summary}
          {rooms.find((r) => r.id === picked)?.title ? ` · ${rooms.find((r) => r.id === picked)?.title}` : ""}
        </p>
      ) : null}
    </section>
  );
}
