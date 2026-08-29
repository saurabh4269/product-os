"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Handoff, type OfficeDesk, type Room } from "@/lib/api";
import { PixelSprite } from "@/components/pixel-office";

const LQIP =
  "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAFA3PEY8MlBGQUZaVVBfeMi7g8CnJ1dXVy8+Qz5UVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRU/2wBDAVVaWldsY2JsbVRfeMi7g8CnJ1dXVy8+Qz5UVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRU/wAARCAAEAAYDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAwT/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGdAf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAQUCf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8Bf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8Bf//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEABj8Cf//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAT8hf//Z";

const SLOTS: Record<string, { x: number; y: number }> = {
  Incidents: { x: 26, y: 47 },
  Ideas: { x: 55, y: 63 },
  Reviews: { x: 41.5, y: 40 },
  Research: { x: 78, y: 34 },
  Ops: { x: 71.5, y: 43 },
  Office: { x: 48, y: 52 },
};

const LANDMARKS = [
  { href: "/memory", label: "Memory", x: 37.5, y: 67 },
  { href: "/approvals", label: "Approvals", x: 52, y: 77 },
];

function districtOf(title: string | null | undefined, fallback = "Ops") {
  const t = (title || "").toLowerCase();
  if (t.includes("safari") || t.includes("3ds") || t.includes("timeout") || t.includes("denied")) return "Incidents";
  if (t.includes("review") || t.includes("activation") || t.includes("onboarding")) return "Reviews";
  if (t.includes("research")) return "Research";
  if (t.includes("android") || t.includes("apple pay") || t.includes("shipping")) return "Ideas";
  return fallback;
}

function slotFor(desk: OfficeDesk | undefined, rooms: Room[]) {
  if (desk?.district && SLOTS[desk.district]) return SLOTS[desk.district];
  const room = rooms.find((r) => r.id === desk?.room_id);
  return SLOTS[districtOf(room?.title ?? desk?.room_title, "Ops")] || SLOTS.Ops;
}

function cluster(desks: OfficeDesk[], rooms: Room[]) {
  const groups = new Map<string, OfficeDesk[]>();
  for (const d of desks) {
    if (!d.room_id) continue;
    groups.set(d.room_id, [...(groups.get(d.room_id) || []), d]);
  }
  return [...groups.entries()].map(([key, people]) => {
    const s = slotFor(people[0], rooms);
    return { key, people, x: s.x, y: s.y };
  });
}

function useImageBox(frame: HTMLElement | null, img: HTMLImageElement | null) {
  const [box, setBox] = useState({ left: 0, top: 0, width: 0, height: 0, ready: false });

  useEffect(() => {
    if (!frame || !img) return;

    const measure = () => {
      const fw = frame.clientWidth;
      const fh = frame.clientHeight;
      const nw = img.naturalWidth || 1350;
      const nh = img.naturalHeight || 900;
      if (!fw || !fh) return;
      const scale = Math.min(fw / nw, fh / nh);
      const width = nw * scale;
      const height = nh * scale;
      setBox({
        left: (fw - width) / 2,
        top: (fh - height) / 2,
        width,
        height,
        ready: width > 8 && height > 8,
      });
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(frame);
    img.addEventListener("load", measure);
    return () => {
      ro.disconnect();
      img.removeEventListener("load", measure);
    };
  }, [frame, img]);

  return box;
}

export function CityMap({
  rooms: roomsIn,
  desks: desksIn,
  handoffs: handoffsIn,
}: {
  rooms: Room[];
  desks: OfficeDesk[];
  handoffs: Handoff[];
}) {
  const router = useRouter();
  const [rooms, setRooms] = useState(roomsIn);
  const [desks, setDesks] = useState(desksIn);
  const [handoffs, setHandoffs] = useState(handoffsIn);
  const [picked, setPicked] = useState<string | null>(null);
  const [fly, setFly] = useState<string | null>(null);
  const [imgReady, setImgReady] = useState(false);
  const [frameEl, setFrameEl] = useState<HTMLDivElement | null>(null);
  const [imgEl, setImgEl] = useState<HTMLImageElement | null>(null);
  const box = useImageBox(frameEl, imgEl);

  useEffect(() => {
    setRooms(roomsIn);
    setDesks(desksIn);
    setHandoffs(handoffsIn);
  }, [roomsIn, desksIn, handoffsIn]);

  const load = useCallback(async () => {
    try {
      const [office, listed] = await Promise.all([api.office(), api.rooms()]);
      setDesks(office.desks);
      setHandoffs(office.handoffs);
      setRooms(listed.rooms);
    } catch {
      /* keep last snapshot */
    }
  }, []);

  useEffect(() => {
    const t = setInterval(() => void load(), 4000);
    return () => clearInterval(t);
  }, [load]);

  const enter = (href: string) => {
    setFly(href);
    window.setTimeout(() => router.push(href), 420);
  };

  const groups = cluster(desks, rooms);
  const selected = rooms.find((r) => r.id === picked);
  const inside = desks.filter((d) => d.room_id === picked);

  return (
    <section className="relative flex min-h-0 flex-col bg-[#eef2ee] lg:h-full">
      <header className="relative z-20 px-5 pb-1 pt-4 text-[#1d1d1f] sm:px-8 lg:pointer-events-none lg:absolute lg:left-8 lg:top-7 lg:max-w-md lg:px-0 lg:pt-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#86868b]">Campus</p>
        <h1 className="mt-1 font-display text-[1.65rem] leading-[1.08] tracking-tight sm:text-3xl lg:text-[2.6rem]">
          The work has a place.
        </h1>
        <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-[#6e6e73]">
          {desks.filter((d) => d.status !== "idle").length} people are already in the buildings. Tap a pin, or
          scroll for the office.
        </p>
      </header>

      <div className="relative mx-auto w-full max-w-[1100px] lg:absolute lg:inset-0 lg:max-w-none">
        <div
          ref={setFrameEl}
          className="relative mx-auto aspect-[3/2] w-full max-h-[min(56vh,400px)] sm:max-h-[min(64vh,560px)] md:max-h-[min(70vh,680px)] lg:absolute lg:inset-0 lg:mx-0 lg:aspect-auto lg:h-full lg:max-h-none"
        >
          <picture>
            <source srcSet="/city/campus.webp" type="image/webp" />
            {/* campus art is object-contain + measured; next/image fights that box */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={setImgEl}
              src="/city/campus.jpg"
              alt="LOOP campus"
              width={1350}
              height={900}
              decoding="async"
              fetchPriority="high"
              onLoad={() => setImgReady(true)}
              onClick={() => setPicked(null)}
              className={`absolute inset-0 h-full w-full object-contain object-center transition-opacity duration-300 ${
                imgReady ? "opacity-100" : "opacity-0"
              }`}
            />
          </picture>
          {!imgReady && (
            <img src={LQIP} alt="" aria-hidden className="absolute inset-0 h-full w-full scale-105 object-contain blur-md" />
          )}

          {box.ready && (
            <div
              className="absolute overflow-visible"
              style={{ left: box.left, top: box.top, width: box.width, height: box.height }}
            >
              <svg className="pointer-events-none absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                {handoffs.slice(-8).map((h, i) => {
                  const a = slotFor(desks.find((d) => d.id === h.from_agent), rooms);
                  const b = slotFor(desks.find((d) => d.id === h.to_agent), rooms);
                  if (a.x === b.x && a.y === b.y) return null;
                  return (
                    <g key={`${h.id}-${i}`}>
                      <path
                        id={`road-${i}`}
                        d={`M ${a.x} ${a.y} C ${(a.x + b.x) / 2} ${a.y - 8}, ${(a.x + b.x) / 2} ${b.y - 8}, ${b.x} ${b.y}`}
                        fill="none"
                        stroke="rgba(29,29,31,0.16)"
                        strokeWidth="0.35"
                        strokeDasharray="1.2 0.8"
                      />
                      <circle r="0.85" fill="#1d1d1f">
                        <animateMotion dur="3.6s" repeatCount="indefinite">
                          <mpath href={`#road-${i}`} />
                        </animateMotion>
                      </circle>
                    </g>
                  );
                })}
              </svg>

              {LANDMARKS.map((m) => (
                <button
                  key={m.href}
                  type="button"
                  onClick={() => enter(m.href)}
                  className={`absolute z-20 -translate-x-1/2 -translate-y-full rounded-full border border-black/10 bg-white/95 px-2.5 py-1.5 text-[12px] font-medium text-[#1d1d1f] shadow-sm transition touch-manipulation ${
                    fly === m.href ? "scale-125" : "hover:scale-105"
                  }`}
                  style={{ left: `${m.x}%`, top: `${m.y}%` }}
                >
                  {m.label}
                </button>
              ))}

              {groups.map((g) => {
                const room = rooms.find((r) => r.id === g.key);
                const on = picked === g.key;
                const zooming = fly === `/rooms/${g.key}`;
                return (
                  <div
                    key={g.key}
                    className="absolute z-10"
                    style={{
                      left: `${g.x}%`,
                      top: `${g.y}%`,
                      transform: `translate(-50%, -88%) scale(${zooming ? 2.05 : on ? 1.18 : 1})`,
                      transformOrigin: "50% 90%",
                      transition: "transform 420ms cubic-bezier(.2,.8,.2,1)",
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setPicked(g.key)}
                      className="relative flex min-h-11 min-w-11 flex-col items-center touch-manipulation"
                      aria-label={room?.title ?? "Open building"}
                    >
                      {on && room && (
                        <span className="mb-1 hidden max-w-[160px] truncate rounded-full border border-black/10 bg-white px-2.5 py-1 text-[11px] font-medium shadow-sm sm:block">
                          {room.title}
                        </span>
                      )}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src="/city/pin.webp" alt="" width={28} height={36} className="h-8 w-auto drop-shadow-md sm:h-9" />
                      <span className="absolute -bottom-1 flex gap-0.5">
                        {g.people.slice(0, 3).map((p) => (
                          <PixelSprite key={p.id} name={p.id} scale={1} working={p.status !== "idle"} />
                        ))}
                      </span>
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {selected && (
        <aside className="relative z-30 mx-4 mb-4 mt-2 rounded-2xl border border-black/10 bg-white/95 p-4 shadow-xl backdrop-blur sm:absolute sm:bottom-6 sm:right-6 sm:mx-0 sm:mb-0 sm:mt-0 sm:w-[300px]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#86868b]">Building</p>
          <h2 className="mt-1 text-[17px] font-semibold leading-snug">{selected.title}</h2>
          <p className="mt-2 text-[13px] text-[#6e6e73]">
            {inside.length} {inside.length === 1 ? "person" : "people"} inside
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {inside.slice(0, 6).map((d) => (
              <span key={d.id} className="inline-flex items-center gap-1.5 rounded-full bg-[#f5f5f7] px-2 py-1 text-[11px]">
                <PixelSprite name={d.id} scale={1} working={d.status !== "idle"} />
                {d.display_name.split(" ")[0]}
              </span>
            ))}
          </div>
          <button
            type="button"
            onClick={() => enter(`/rooms/${selected.id}`)}
            className="mt-4 min-h-11 w-full rounded-full bg-[#1d1d1f] text-[13px] font-medium text-white touch-manipulation"
          >
            Open the room
          </button>
        </aside>
      )}
    </section>
  );
}
