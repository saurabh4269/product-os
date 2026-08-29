"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Handoff, type OfficeDesk, type Room, type RoomDetail } from "@/lib/api";
import { BUILDINGS, LANDMARKS, busiestRoom, cluster, slotFor } from "@/lib/campus";
import { pagesFromDistrict, pagesFromRoom } from "@/lib/work-pages";
import { PixelSprite } from "@/components/pixel-office";
import { WorkFlipbook } from "@/components/work-flipbook";

const LQIP =
  "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAFA3PEY8MlBGQUZaVVBfeMi7g8CnJ1dXVy8+Qz5UVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRU/2wBDAVVaWldsY2JsbVRfeMi7g8CnJ1dXVy8+Qz5UVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRUVFRU/wAARCAAEAAYDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAwT/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAGdAf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAQUCf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQMBAT8Bf//EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQIBAT8Bf//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEABj8Cf//EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAT8hf//Z";

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
  picked,
  onPick,
  onWalkInside,
}: {
  rooms: Room[];
  desks: OfficeDesk[];
  handoffs: Handoff[];
  picked: string | null;
  onPick: (roomId: string | null, district?: string) => void;
  onWalkInside: (district: string) => void;
}) {
  const router = useRouter();
  const [rooms, setRooms] = useState(roomsIn);
  const [desks, setDesks] = useState(desksIn);
  const [handoffs, setHandoffs] = useState(handoffsIn);
  const [district, setDistrict] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [fly, setFly] = useState<string | null>(null);
  const [imgReady, setImgReady] = useState(false);
  const [peek, setPeek] = useState<RoomDetail | null>(null);
  const [frameEl, setFrameEl] = useState<HTMLDivElement | null>(null);
  const [imgEl, setImgEl] = useState<HTMLImageElement | null>(null);
  const box = useImageBox(frameEl, imgEl);

  useEffect(() => {
    setRooms(roomsIn);
    setDesks(desksIn);
    setHandoffs(handoffsIn);
  }, [roomsIn, desksIn, handoffsIn]);

  useEffect(() => {
    if (!picked) {
      setPeek(null);
      return;
    }
    let live = true;
    api
      .room(picked)
      .then((d) => {
        if (live) setPeek(d);
      })
      .catch(() => {
        if (live) setPeek(null);
      });
    return () => {
      live = false;
    };
  }, [picked]);

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

  const pickBuilding = (id: string) => {
    setDistrict(id);
    const roomId = busiestRoom(id, desks, rooms);
    onPick(roomId, id);
  };

  const groups = cluster(desks, rooms);
  const selected = rooms.find((r) => r.id === picked);
  const inside = desks.filter((d) => (picked ? d.room_id === picked : d.district === district));
  const pages = selected
    ? pagesFromRoom(selected, desks, peek)
    : district
      ? pagesFromDistrict(district, rooms, desks)
      : [];

  return (
    <section className="relative flex min-h-0 flex-col bg-[#eef2ee] lg:h-full">
      <header className="relative z-20 px-5 pb-1 pt-4 text-[#1d1d1f] sm:px-8 lg:pointer-events-none lg:absolute lg:left-8 lg:top-7 lg:max-w-md lg:px-0 lg:pt-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#86868b]">Campus</p>
        <h1 className="mt-1 font-display text-[1.65rem] leading-[1.08] tracking-tight sm:text-3xl lg:text-[2.6rem]">
          The work has a place.
        </h1>
        <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-[#6e6e73]">
          {desks.filter((d) => d.status !== "idle").length} people are already in the buildings. Tap a
          building, then flip the work.
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
              onClick={() => {
                onPick(null);
                setDistrict(null);
              }}
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
              <svg className="absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                {BUILDINGS.map((b) => {
                  const on = hover === b.id || district === b.id;
                  return (
                    <ellipse
                      key={b.id}
                      cx={b.x}
                      cy={b.y}
                      rx={b.rx}
                      ry={b.ry}
                      fill={on ? "rgba(255,255,255,0.32)" : "rgba(255,255,255,0.01)"}
                      stroke={on ? "rgba(29,29,31,0.2)" : "transparent"}
                      strokeWidth="0.4"
                      className="cursor-pointer"
                      onMouseEnter={() => setHover(b.id)}
                      onMouseLeave={() => setHover(null)}
                      onClick={(e) => {
                        e.stopPropagation();
                        pickBuilding(b.id);
                      }}
                    >
                      <title>{b.label}</title>
                    </ellipse>
                  );
                })}
              </svg>

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

              {hover && !district ? (
                <span
                  className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-full rounded-full border border-black/10 bg-white/95 px-2.5 py-1 text-[12px] font-medium shadow-sm"
                  style={{
                    left: `${BUILDINGS.find((b) => b.id === hover)?.x ?? 50}%`,
                    top: `${(BUILDINGS.find((b) => b.id === hover)?.y ?? 50) - 8}%`,
                  }}
                >
                  {hover}
                </span>
              ) : null}

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
                      onClick={() => {
                        const d = desks.find((desk) => desk.room_id === g.key)?.district;
                        setDistrict(d ?? null);
                        onPick(g.key, d);
                      }}
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

      {pages.length ? (
        <aside className="relative z-30 mx-4 mb-4 mt-2 sm:absolute sm:bottom-6 sm:right-6 sm:mx-0 sm:mb-0 sm:mt-0 sm:w-[300px] sm:max-h-[min(72vh,540px)] sm:overflow-y-auto">
          <WorkFlipbook
            pages={pages}
            cover={
              inside.length ? (
                <div className="flex flex-wrap gap-2 px-5 pt-5">
                  {inside.slice(0, 6).map((d) => (
                    <span key={d.id} className="inline-flex items-center gap-1.5 rounded-full bg-[#f5f5f7] px-2 py-1 text-[11px]">
                      <PixelSprite name={d.id} scale={1} working={d.status !== "idle"} />
                      {d.display_name.split(" ")[0]}
                    </span>
                  ))}
                </div>
              ) : null
            }
            onOpen={selected ? () => enter(`/rooms/${selected.id}`) : undefined}
            onInside={
              district || selected
                ? () => onWalkInside(district || desks.find((d) => d.room_id === selected?.id)?.district || "Office")
                : undefined
            }
            openLabel="Open the room"
            insideLabel="Walk inside"
          />
        </aside>
      ) : null}
    </section>
  );
}
