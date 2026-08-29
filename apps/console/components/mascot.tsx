"use client";

import { cn } from "@/lib/utils";

/** Pip — campus host. Inspired by Grok companion cuteness (round animal, hoodie, big eyes), not a copy. */
export function PipMark({
  size = 32,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      className={cn("shrink-0", className)}
      aria-hidden
    >
      <circle cx="32" cy="32" r="32" fill="#eef2ee" />
      <ellipse cx="32" cy="54" rx="20" ry="9" fill="#1d1d1f" />
      <path d="M14 50c2-10 8-16 18-16s16 6 18 16" fill="#2c2c2e" />
      <ellipse cx="20" cy="22" rx="8" ry="7" fill="#8d6b4a" />
      <ellipse cx="44" cy="22" rx="8" ry="7" fill="#8d6b4a" />
      <ellipse cx="20" cy="23" rx="4.5" ry="3.8" fill="#c4a574" />
      <ellipse cx="44" cy="23" rx="4.5" ry="3.8" fill="#c4a574" />
      <ellipse cx="32" cy="34" rx="20" ry="18" fill="#b08968" />
      <ellipse cx="32" cy="38" rx="15" ry="13" fill="#f3e6d0" />
      <ellipse cx="24" cy="33" rx="4.2" ry="5" fill="#1d1d1f" />
      <ellipse cx="40" cy="33" rx="4.2" ry="5" fill="#1d1d1f" />
      <circle cx="22.6" cy="31.2" r="1.3" fill="#fff" />
      <circle cx="38.6" cy="31.2" r="1.3" fill="#fff" />
      <ellipse cx="23" cy="40" rx="3.2" ry="1.6" fill="#e8b4b8" opacity="0.85" />
      <ellipse cx="41" cy="40" rx="3.2" ry="1.6" fill="#e8b4b8" opacity="0.85" />
      <ellipse cx="32" cy="40" rx="1.6" ry="1.2" fill="#3a2a22" />
      <path d="M28 44c2.2 2 5.8 2 8 0" fill="none" stroke="#3a2a22" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function PipSticker({
  className,
  title = "Pip, the campus host",
}: {
  className?: string;
  title?: string;
}) {
  return (
    <picture>
      <source srcSet="/city/pip.webp" type="image/webp" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/city/pip.jpg" alt={title} className={cn("select-none", className)} />
    </picture>
  );
}

export function PipWave({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex origin-bottom animate-[bob_2.2s_ease-in-out_infinite]", className)}>
      <PipMark size={36} />
    </span>
  );
}
