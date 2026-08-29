"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { BookOpen, Gavel, Home, Library, Radio, Scale, Shield, Sparkles } from "lucide-react";
import { api, type Room } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Pixel } from "@/components/pixel-office";

const NAV = [
  { href: "/", label: "Home", icon: Home },
  { href: "/registry", label: "Registry", icon: Library },
  { href: "/memory", label: "Memory", icon: BookOpen },
  { href: "/traces", label: "Traces", icon: Radio },
  { href: "/approvals", label: "Approvals", icon: Gavel },
  { href: "/outcomes", label: "Outcomes", icon: Scale },
  { href: "/governance", label: "Governance", icon: Shield },
];

const KIND_TONE: Record<string, string> = {
  incident: "text-danger",
  opportunity: "text-ok",
  review: "text-warn",
  research: "text-copper",
  ops: "text-[var(--dim)]",
};

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [rooms, setRooms] = useState<Room[]>([]);

  useEffect(() => {
    api
      .rooms()
      .then((r) => setRooms(r.rooms))
      .catch(() => setRooms([]));
  }, [path]);

  const roomActive = path.startsWith("/rooms/");

  return (
    <div className="flex h-screen overflow-hidden">
      <nav className="flex w-14 shrink-0 flex-col items-center border-r border-border bg-[#0b0b0d] py-4">
        <Link href="/" className="mb-6 font-mono text-[10px] tracking-[0.24em] text-accent">
          OS
        </Link>
        {NAV.map((item) => {
          const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={cn(
                "mb-1 flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                active ? "bg-accent/15 text-accent" : "text-[var(--dim)] hover:bg-white/5 hover:text-foreground"
              )}
            >
              <Icon size={16} />
            </Link>
          );
        })}
        <div className="mt-auto pb-2">
          <Sparkles size={14} className="text-[var(--dim)]" />
        </div>
      </nav>

      <aside className="hidden w-72 shrink-0 flex-col border-r border-border bg-[#0c0c0e] md:flex">
        <div className="border-b border-border px-4 py-4">
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-accent">Product OS</p>
          <p className="mt-1 text-sm text-[var(--dim)]">Rooms · agents · humans</p>
        </div>
        <div className="flex-1 overflow-y-auto chat-scroll px-2 py-2">
          {(["incident", "opportunity", "review", "research", "ops"] as const).map((kind) => {
            const group = rooms.filter((r) => r.kind === kind);
            if (group.length === 0) return null;
            return (
              <div key={kind} className="mb-3">
                <p className={cn("px-2 pb-1 font-mono text-[10px] uppercase tracking-widest", KIND_TONE[kind])}>
                  {kind}
                </p>
                {group.map((room) => {
                  const href = `/rooms/${room.id}`;
                  const active = path === href;
                  return (
                    <Link
                      key={room.id}
                      href={href}
                      className={cn(
                        "mb-0.5 block rounded-lg px-2 py-2 transition-colors",
                        active ? "bg-white/8 text-foreground" : "text-[var(--dim)] hover:bg-white/5 hover:text-foreground"
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="truncate text-sm text-foreground">{room.title}</p>
                        {room.loop_type ? (
                          <span className="shrink-0 font-mono text-[9px] uppercase text-[var(--dim)]">
                            {room.loop_type === "type_a" ? "A" : "B"}
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-0.5 truncate font-mono text-[10px] text-[var(--dim)]">{room.preview ?? room.topic}</p>
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 shrink-0 items-center justify-between border-b border-border px-5">
          <p className="font-mono text-[11px] uppercase tracking-widest text-[var(--dim)]">
            Observe · investigate · coordinate · ship · verify
          </p>
          <div className="flex items-center gap-2">
            <Pixel name="orchestrator" />
            <span className="rounded-full bg-ok/15 px-2 py-0.5 font-mono text-[10px] text-ok">live</span>
          </div>
        </header>
        <main className={cn("min-h-0 flex-1", roomActive ? "overflow-hidden" : "overflow-y-auto px-6 py-8")}>
          {children}
        </main>
      </div>
    </div>
  );
}
