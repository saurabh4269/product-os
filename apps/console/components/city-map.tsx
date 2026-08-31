"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type Handoff, type OfficeDesk, type Room, type RoomDetail } from "@/lib/api";
import { BUILDINGS, LANDMARKS, busiestRoom, cluster, districtPods, slotFor } from "@/lib/campus";
import { pagesFromDistrict, pagesFromRoom } from "@/lib/work-pages";
import { AgentBadge } from "@/components/agent-badge";
import { PixelSprite } from "@/components/pixel-office";
import { WorkFlipbook } from "@/components/work-flipbook";
import { cn } from "@/lib/utils";

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
    if (img.complete && img.naturalWidth > 0) measure();
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

/** Cached campus art often loads before React attaches onLoad — check img.complete. */
function useCampusImage(img: HTMLImageElement | null) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!img) {
      setReady(false);
      return;
    }
    if (img.complete && img.naturalWidth > 0) {
      setReady(true);
      return;
    }
    setReady(false);
    const onLoad = () => setReady(true);
    const onError = () => setReady(true);
    img.addEventListener("load", onLoad);
    img.addEventListener("error", onError);
    return () => {
      img.removeEventListener("load", onLoad);
      img.removeEventListener("error", onError);
    };
  }, [img]);

  const onLoad = useCallback(() => setReady(true), []);

  return { ready, onLoad };
}

export function CityMap({
  rooms: roomsIn,
  desks: desksIn,
  handoffs: handoffsIn,
  picked,
  onPick,
  onWalkInside,
  hero = false,
  compactHero = false,
  showTapHint = false,
  campusLine,
  campusHot = false,
  liveMotion = false,
}: {
  rooms: Room[];
  desks: OfficeDesk[];
  handoffs: Handoff[];
  picked: string | null;
  onPick: (roomId: string | null, district?: string) => void;
  onWalkInside: (district: string) => void;
  /** Full-bleed homepage hero — minimal copy, agents on buildings. */
  hero?: boolean;
  /** Shorter hero when manager panel is primary. */
  compactHero?: boolean;
  /** First visit — hint that buildings are tappable */
  showTapHint?: boolean;
  /** Contextual campus subtitle (return visits, approvals, quiet). */
  campusLine?: string;
  campusHot?: boolean;
  /** Demo-only — moving dots on handoff paths. */
  liveMotion?: boolean;
}) {
  const router = useRouter();
  const [rooms, setRooms] = useState(roomsIn);
  const [desks, setDesks] = useState(desksIn);
  const [handoffs, setHandoffs] = useState(handoffsIn);
  const [district, setDistrict] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [fly, setFly] = useState<string | null>(null);
  const [peek, setPeek] = useState<RoomDetail | null>(null);
  const [frameEl, setFrameEl] = useState<HTMLDivElement | null>(null);
  const [imgEl, setImgEl] = useState<HTMLImageElement | null>(null);
  const { ready: imgReady, onLoad: onCampusLoad } = useCampusImage(imgEl);
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
  const pods = districtPods(desks);
  const workingCount = desks.filter((d) => d.status !== "idle").length;
  const selected = rooms.find((r) => r.id === picked);
  const inside = desks.filter((d) => (picked ? d.room_id === picked : d.district === district));
  const pages = selected
    ? pagesFromRoom(selected, desks, peek)
    : district
      ? pagesFromDistrict(district, rooms, desks)
      : [];

  return (
    <section className={cn("relative flex h-full min-h-[inherit] flex-col bg-[#eef2ee]", hero && (compactHero ? "min-h-[min(52vh,480px)] pb-24 sm:pb-28" : "min-h-[min(78vh,680px)] pb-28 sm:pb-32"))}>
      {!hero ? (
        <header className="relative z-20 px-5 pb-1 pt-4 text-[#1d1d1f] sm:px-8 lg:pointer-events-none lg:absolute lg:left-8 lg:top-7 lg:max-w-md lg:px-0 lg:pt-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#86868b]">Campus</p>
        </header>
      ) : (
        <div className="pointer-events-none absolute left-5 top-4 z-20 sm:left-8 sm:top-6">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#86868b]">Campus</p>
          {campusLine ? (
            <p className={cn("mt-1 text-[13px]", campusHot ? "font-medium text-[#0071e3]" : "text-[#6e6e73]")}>
              {campusLine}
            </p>
          ) : workingCount > 0 ? (
            <p className="mt-1 text-[13px] font-medium text-[#1d1d1f]">
              {workingCount} active
            </p>
          ) : null}
        </div>
      )}

      <div className="relative mx-auto w-full max-w-[1100px] lg:absolute lg:inset-0 lg:max-w-none">
        <div
          ref={setFrameEl}
          className="relative mx-auto aspect-[3/2] w-full max-h-[min(62vh,480px)] sm:max-h-[min(68vh,560px)] md:max-h-[min(72vh,640px)] lg:absolute lg:inset-0 lg:mx-0 lg:aspect-auto lg:h-full lg:max-h-none"
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
              loading="eager"
              onLoad={onCampusLoad}
              onClick={() => {
                onPick(null);
                setDistrict(null);
              }}
              className={cn(
                "absolute inset-0 h-full w-full object-contain object-center transition-opacity duration-300",
                imgReady ? "opacity-100" : "opacity-0"
              )}
            />
          </picture>
          {!imgReady ? (
            <img
              src={LQIP}
              alt=""
              aria-hidden
              className="absolute inset-0 h-full w-full scale-105 object-contain blur-md"
            />
          ) : null}

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
                {handoffs.slice(-5).map((h, i) => {
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
                      <circle r="0.65" fill="#1d1d1f" opacity={liveMotion ? 0.55 : 0}>
                        {liveMotion ? (
                          <animateMotion dur="5.2s" repeatCount="indefinite">
                            <mpath href={`#road-${i}`} />
                          </animateMotion>
                        ) : null}
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

              {pods.map((pod) => {
                const hot = hover === pod.id || district === pod.id;
                const folk = pod.working.slice(0, 3);
                if (!folk.length) return null;
                return (
                  <div
                    key={`pod-${pod.id}`}
                    className={cn(
                      "pointer-events-none absolute z-[8] flex -translate-x-1/2 -translate-y-1/2 items-end gap-0.5 transition-opacity duration-300",
                      hot ? "opacity-100" : "opacity-90"
                    )}
                    style={{ left: `${pod.x}%`, top: `${pod.y}%` }}
                  >
                    {folk.map((p) => (
                      <PixelSprite key={p.id} name={p.id} scale={2} working={p.status !== "idle"} />
                    ))}
                  </div>
                );
              })}

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
                      {on && room ? (
                        <span className="mb-1 hidden max-w-[160px] truncate rounded-full border border-black/10 bg-white px-2.5 py-1 text-[11px] font-medium shadow-sm sm:block">
                          {room.title}
                        </span>
                      ) : null}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src="/city/pin.webp" alt="" width={28} height={36} className="h-8 w-auto drop-shadow-md sm:h-9" />
                      {g.people.length ? (
                        <span className="absolute -bottom-1 flex items-end gap-0.5">
                          {g.people.slice(0, 3).map((p) => (
                            <PixelSprite key={p.id} name={p.id} scale={2} working={p.status !== "idle"} />
                          ))}
                        </span>
                      ) : null}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {pages.length ? (
        <aside
          className={cn(
            "relative z-30 mx-4 mb-4 mt-2 sm:absolute sm:mx-0 sm:mb-0 sm:mt-0 sm:w-[280px] sm:max-h-[min(50vh,420px)] sm:overflow-y-auto",
            hero ? "sm:right-6 sm:top-6 sm:mb-0" : "sm:bottom-6 sm:right-6 sm:max-h-[min(72vh,540px)]"
          )}
        >
          <WorkFlipbook
            pages={pages}
            cover={
              inside.length ? (
                <div className="flex flex-wrap gap-2 px-5 pt-5">
                  {inside.slice(0, 6).map((d) => (
                    <span key={d.id} className="inline-flex items-center gap-1.5 rounded-full bg-[#f5f5f7] px-2 py-1 text-[11px]">
                      <AgentBadge name={d.id} working={d.status !== "idle"} size={18} variant="initial" />
                      {d.display_name.split(" ")[0]}
                    </span>
                  ))}
                </div>
              ) : null
            }
            onOpen={selected ? () => enter(`/rooms/${selected.id}`) : undefined}
            onPage={(index) => {
              const page = pages[index];
              const room = page ? rooms.find((r) => r.id === page.id) : undefined;
              if (room) onPick(room.id, district ?? undefined);
            }}
            onInside={
              district || selected
                ? () => onWalkInside(district || desks.find((d) => d.room_id === selected?.id)?.district || "Office")
                : undefined
            }
            openLabel="Open"
            insideLabel="Inside"
          />
        </aside>
      ) : null}
    </section>
  );
}
