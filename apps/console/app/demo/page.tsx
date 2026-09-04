"use client";

import Link from "next/link";

const DEMO_SRC = "/demo/product-os-demo.mp4";
const HANG_ROOM = "room_f627763ea9";

export default function DemoPage() {
  return (
    <div className="min-h-full bg-[#f5f5f7]">
      <div className="page-pad mx-auto max-w-5xl pb-16 pt-8">
        <Link href="/" className="text-[13px] font-medium text-accent hover:underline">
          ← Campus
        </Link>
        <header className="mt-4 max-w-2xl">
          <p className="text-[13px] font-medium uppercase tracking-[0.14em] text-[var(--faint)]">
            Product film
          </p>
          <h1 className="mt-2 font-serif text-[clamp(2rem,4vw,2.75rem)] font-medium leading-tight tracking-tight text-foreground">
            One loop, end to end.
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-[var(--dim)]">
            Real hosted UI — campus, a live incident room, diagnosis, human gate, and a tenant flags PR.
            Cove is the demo tenant only; Product OS never merges tenant PRs.
          </p>
        </header>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border bg-black shadow-[0_24px_80px_rgba(0,0,0,0.12)]">
          <video
            className="aspect-video w-full bg-[#eef2ee]"
            src={DEMO_SRC}
            controls
            playsInline
            preload="metadata"
            poster="/city/campus.webp"
          >
            <track kind="captions" />
          </video>
        </div>

        <p className="mt-3 text-[12px] text-[var(--faint)]">
          Muted autoplay on the campus embeds the same clip. Illustrative metrics use the hosted hang demo.
        </p>

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/connect"
            className="inline-flex items-center rounded-full bg-accent px-5 py-2.5 text-[14px] font-medium text-white hover:opacity-90"
          >
            Connect Product Y
          </Link>
          <Link
            href={`/rooms/${HANG_ROOM}`}
            className="inline-flex items-center rounded-full border border-border bg-white px-5 py-2.5 text-[14px] font-medium text-foreground hover:bg-[#fafafa]"
          >
            Open the hang room
          </Link>
          <Link
            href="/"
            className="inline-flex items-center rounded-full px-5 py-2.5 text-[14px] font-medium text-accent hover:underline"
          >
            Start on campus
          </Link>
        </div>
      </div>
    </div>
  );
}
