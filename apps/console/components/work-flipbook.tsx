"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { OfficeDesk, Room, RoomDetail } from "@/lib/api";
import { api } from "@/lib/api";
import { pagesFromRoom, type WorkPage } from "@/lib/work-pages";
import { PixelOffice, PixelSprite } from "@/components/pixel-office";
import { cn } from "@/lib/utils";

export function WorkFlipbook({
  pages,
  cover,
  onOpen,
  onInside,
  onPage,
  openLabel = "Open the room",
  insideLabel,
  className,
}: {
  pages: WorkPage[];
  cover?: ReactNode;
  onOpen?: () => void;
  onInside?: () => void;
  onPage?: (index: number) => void;
  openLabel?: string;
  insideLabel?: string;
  className?: string;
}) {
  const [i, setI] = useState(0);
  const total = Math.max(pages.length, 1);

  useEffect(() => {
    setI(0);
  }, [pages[0]?.id]);

  const page = pages[Math.min(i, total - 1)];
  const last = i >= total - 1;
  const depth = Math.min(total - 1, 3);

  function next() {
    if (last) {
      onOpen?.();
      return;
    }
    const nextI = Math.min(i + 1, total - 1);
    setI(nextI);
    onPage?.(nextI);
  }

  function back() {
    setI((n) => Math.max(0, n - 1));
  }

  return (
    <div className={cn("relative", className)}>
      <div className="relative mb-1 pb-3 pr-3" style={{ perspective: 1200 }}>
        {Array.from({ length: depth }).map((_, d) => (
          <div
            key={d}
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-[22px] border border-black/5 bg-white"
            style={{
              transform: `translateY(${(d + 1) * 5}px) translateX(${(d + 1) * 3}px) rotate(${(d + 1) * 0.7}deg)`,
              opacity: 0.55 - d * 0.12,
              zIndex: depth - d,
            }}
          />
        ))}

        <article
          className="relative z-10 overflow-hidden rounded-[22px] border border-border bg-white soft-card"
          style={{ transformOrigin: "left center" }}
        >
          {i === 0 && cover ? cover : null}

          {page ? (
            <button
              type="button"
              onClick={next}
              className="block w-full px-5 py-5 text-left touch-manipulation"
            >
              <p className="text-[12px] capitalize text-[var(--faint)]">{page.kicker}</p>
              <h3 className="mt-1 text-[17px] font-semibold leading-6 tracking-tight">{page.title}</h3>
              <p className="mt-2 line-clamp-4 text-[14px] leading-6 text-[var(--dim)]">{page.body}</p>
              {page.people?.length && i !== 0 ? (
                <span className="mt-3 flex gap-1">
                  {page.people.slice(0, 5).map((id) => (
                    <PixelSprite key={id} name={id} scale={1} />
                  ))}
                </span>
              ) : null}
              <p className="mt-4 text-[12px] text-[var(--faint)]">
                {last ? (onOpen ? "Tap to open" : `${i + 1} / ${total}`) : `Tap to go deeper · ${i + 1} / ${total}`}
              </p>
            </button>
          ) : null}
        </article>
      </div>

      <div className={cn("mt-3 flex flex-wrap items-center gap-2", !onOpen && !onInside && i === 0 && "hidden")}>
        {i > 0 ? (
          <button
            type="button"
            onClick={back}
            className="min-h-10 rounded-full px-3 text-[13px] text-[var(--dim)] hover:text-foreground touch-manipulation"
          >
            Back
          </button>
        ) : null}
        {onInside && i === 0 ? (
          <button
            type="button"
            onClick={onInside}
            className="min-h-11 rounded-full bg-[var(--elev)] px-4 text-[13px] font-medium text-foreground touch-manipulation"
          >
            {insideLabel ?? "Walk inside"}
          </button>
        ) : null}
        {onOpen ? (
          <button
            type="button"
            onClick={onOpen}
            className="min-h-11 rounded-full bg-[#1d1d1f] px-4 text-[13px] font-medium text-white touch-manipulation"
          >
            {openLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function RoomCard({
  room,
  desks,
}: {
  room: Room;
  desks: OfficeDesk[];
}) {
  const router = useRouter();
  const [detail, setDetail] = useState<RoomDetail | null>(null);
  const pages = pagesFromRoom(room, desks, detail);
  const working = new Set((desks.filter((d) => d.room_id === room.id && d.status !== "idle").map((d) => d.id)).concat(room.members.slice(0, 2)));

  return (
    <WorkFlipbook
      pages={pages}
      cover={<PixelOffice members={room.members} working={working} compact link={false} />}
      onOpen={() => router.push(`/rooms/${room.id}`)}
      onPage={() => {
        if (!detail) {
          api
            .room(room.id)
            .then(setDetail)
            .catch(() => setDetail(null));
        }
      }}
      openLabel="Open the room"
    />
  );
}
