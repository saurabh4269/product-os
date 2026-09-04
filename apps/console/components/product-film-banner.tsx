"use client";

import Link from "next/link";

const DEMO_SRC = "/demo/product-os-demo.mp4";

/** Campus embed — muted film teaser; full controls on /demo. */
export function ProductFilmBanner({ className = "" }: { className?: string }) {
  return (
    <section
      className={`overflow-hidden rounded-2xl border border-border bg-white shadow-sm ${className}`}
      aria-label="Product film preview"
    >
      <div className="flex flex-col gap-0 sm:flex-row sm:items-stretch">
        <div className="relative min-h-[140px] flex-1 bg-[#eef2ee] sm:min-h-0 sm:max-w-[52%]">
          <video
            className="absolute inset-0 h-full w-full object-cover"
            src={DEMO_SRC}
            muted
            autoPlay
            loop
            playsInline
            preload="metadata"
            poster="/city/campus.webp"
          />
        </div>
        <div className="flex flex-1 flex-col justify-center gap-3 p-5 sm:p-6">
          <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[var(--faint)]">
            Product film · ~80s
          </p>
          <p className="text-[17px] font-semibold leading-snug tracking-tight text-foreground">
            Watch the loop once, then walk the same path.
          </p>
          <p className="text-[13px] leading-relaxed text-[var(--dim)]">
            Campus → room → diagnose → approve → tenant PR. Silent, real pixels.
          </p>
          <Link href="/demo" className="text-[14px] font-medium text-accent hover:underline">
            Full film with controls →
          </Link>
        </div>
      </div>
    </section>
  );
}
