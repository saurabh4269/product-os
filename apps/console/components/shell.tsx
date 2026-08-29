"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Room } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PixelSprite } from "@/components/pixel-office";

const SYSTEM = [
  { href: "/", label: "Hive" },
  { href: "/registry", label: "Registry" },
  { href: "/memory", label: "Memory" },
  { href: "/traces", label: "Traces" },
  { href: "/approvals", label: "Approvals" },
];

const KINDS = ["incident", "opportunity", "review", "research", "ops"] as const;

function kindLabel(kind: string) {
  if (kind === "incident") return "Broke";
  if (kind === "opportunity") return "Better";
  return kind;
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [rooms, setRooms] = useState<Room[]>([]);

  useEffect(() => {
    api
      .rooms()
      .then((r) => setRooms(r.rooms))
      .catch(() => setRooms([]));
  }, [path]);

  const inRoom = path.startsWith("/rooms/");

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden w-[272px] shrink-0 flex-col border-r border-border bg-[var(--paper)] md:flex">
        <div className="px-5 pb-5 pt-6">
          <Link href="/" className="block">
            <p className="font-display text-[28px] leading-none tracking-tight">Product OS</p>
            <p className="mt-2 text-[12px] text-[var(--dim)]">The office is the product.</p>
          </Link>
        </div>

        <nav className="px-3 pb-3">
          {SYSTEM.map((item) => {
            const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "block px-2 py-1.5 text-[13px] transition-colors",
                  active ? "text-accent" : "text-[var(--dim)] hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex-1 overflow-y-auto chat-scroll px-3 pb-6">
          {KINDS.map((kind) => {
            const group = rooms.filter((r) => r.kind === kind);
            if (!group.length) return null;
            return (
              <div key={kind} className="mb-5">
                <p className="px-2 pb-1 text-[11px] uppercase tracking-[0.18em] text-[var(--faint)]">{kindLabel(kind)}</p>
                {group.map((room) => {
                  const href = `/rooms/${room.id}`;
                  const active = path === href;
                  return (
                    <Link
                      key={room.id}
                      href={href}
                      className={cn(
                        "mb-0.5 flex items-start gap-2 px-2 py-2 transition-colors",
                        active ? "bg-[var(--elev)] text-foreground" : "text-[var(--dim)] hover:text-foreground"
                      )}
                    >
                      <span
                        className="mt-1.5 h-1.5 w-1.5 shrink-0"
                        style={{
                          background:
                            kind === "incident"
                              ? "var(--danger)"
                              : kind === "opportunity"
                                ? "var(--ok)"
                                : kind === "review"
                                  ? "var(--warn)"
                                  : "var(--accent-2)",
                        }}
                      />
                      <span className="min-w-0">
                        <span className="block truncate text-[13px] leading-5 text-foreground">{room.title}</span>
                        <span className="mt-0.5 block truncate text-[11px] leading-4 text-[var(--faint)]">
                          {room.preview ?? room.topic}
                        </span>
                      </span>
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-2 border-t border-border px-4 py-3">
          <PixelSprite name="you" scale={3} />
          <div>
            <p className="text-[12px] leading-4">You</p>
            <p className="text-[11px] text-ok">in the rooms</p>
          </div>
        </div>
      </aside>

      <main className={cn("min-w-0 flex-1", inRoom ? "overflow-hidden" : "overflow-y-auto chat-scroll")}>
        {children}
      </main>
    </div>
  );
}
