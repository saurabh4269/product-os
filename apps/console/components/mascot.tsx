"use client";

import { cn } from "@/lib/utils";

/** Bean — round cocoa bear. Sticker-soft like Bubu/Dudu, our own character. */

export function BeanMark({
  size = 32,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <picture>
      <source srcSet="/city/bean.webp" type="image/webp" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/city/bean.jpg"
        alt=""
        width={size}
        height={size}
        className={cn("shrink-0 rounded-[10px] object-cover", className)}
        style={{ width: size, height: size }}
      />
    </picture>
  );
}

export function CampusSticker({
  className,
  title = "Bean and Mochi",
}: {
  className?: string;
  title?: string;
}) {
  return (
    <picture>
      <source srcSet="/city/duo.webp" type="image/webp" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/city/duo.jpg" alt={title} className={cn("select-none", className)} />
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
