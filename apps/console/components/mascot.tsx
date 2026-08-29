"use client";

import { cn } from "@/lib/utils";

/** Mochi — cream bear. She's the face. Bean (cocoa) sits with her and they watch the work. */

export type MascotMood = "idle" | "watch" | "yay";

function SitBear({
  who,
  look = 0,
  mood = "idle",
  late,
  className,
}: {
  who: "mochi" | "bean";
  look?: number;
  mood?: MascotMood;
  late?: boolean;
  className?: string;
}) {
  const src = who === "mochi" ? "/city/mochi" : "/city/bean-sit";
  const tilt = Math.max(-1, Math.min(1, look)) * (who === "mochi" ? 8 : 6);
  return (
    <span className={cn("mascot-sit", `is-${mood}`, late && "is-late", className)}>
      <picture>
        <source srcSet={`${src}.webp`} type="image/webp" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${src}.png`}
          alt=""
          className={cn("h-full w-full object-contain drop-shadow-sm", who === "mochi" ? "who-mochi" : "who-bean")}
          style={{ transform: `rotate(${tilt}deg)` }}
        />
      </picture>
    </span>
  );
}

export function BeanMark({
  size = 32,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <span className={cn("mascot-mark inline-flex shrink-0", className)} style={{ width: size, height: size }}>
      <picture>
        <source srcSet="/city/mochi.webp" type="image/webp" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/city/mochi.png" alt="" width={size} height={size} className="h-full w-full object-contain drop-shadow-sm" />
      </picture>
    </span>
  );
}

export function CampusSticker({
  className,
  title = "Mochi and Bean",
  look = 0,
  mood = "idle",
}: {
  className?: string;
  title?: string;
  look?: number;
  mood?: MascotMood;
}) {
  return (
    <div
      role="img"
      aria-label={title}
      className={cn("mascot-pair inline-flex items-end justify-center", `is-${mood}`, className)}
    >
      <SitBear who="bean" look={look} mood={mood} className="h-full w-[54%] -mr-[9%]" />
      <SitBear who="mochi" look={look} mood={mood} late className="h-full w-[54%] -ml-[9%]" />
    </div>
  );
}

export function BeanWave({ className }: { className?: string }) {
  return <BeanMark size={36} className={cn("is-wave", className)} />;
}

/** @deprecated use BeanMark */
export const PipMark = BeanMark;
/** @deprecated use CampusSticker */
export const PipSticker = CampusSticker;
/** @deprecated use BeanWave */
export const PipWave = BeanWave;
