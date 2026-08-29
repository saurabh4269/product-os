"use client";

import { cn } from "@/lib/utils";

/** Mochi — cream bear. She's the face of the product. Bean (cocoa) sits with her on campus. */

export function BeanMark({
  size = 32,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <picture>
      <source srcSet="/city/mochi.webp" type="image/webp" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/city/mochi.png"
        alt=""
        width={size}
        height={size}
        className={cn("shrink-0 object-contain drop-shadow-sm", className)}
        style={{ width: size, height: size }}
      />
    </picture>
  );
}

export function CampusSticker({
  className,
  title = "Mochi and Bean",
}: {
  className?: string;
  title?: string;
}) {
  return (
    <picture>
      <source srcSet="/city/duo.webp" type="image/webp" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/city/duo.png" alt={title} className={cn("select-none object-contain", className)} />
    </picture>
  );
}

export function BeanWave({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex origin-bottom animate-[bob_2.2s_ease-in-out_infinite]", className)}>
      <BeanMark size={36} />
    </span>
  );
}

/** @deprecated use BeanMark */
export const PipMark = BeanMark;
/** @deprecated use CampusSticker */
export const PipSticker = CampusSticker;
/** @deprecated use BeanWave */
export const PipWave = BeanWave;
