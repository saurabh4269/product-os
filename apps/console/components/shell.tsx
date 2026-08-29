"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Room } from "@/lib/api";
import { cn } from "@/lib/utils";
import { PixelSprite } from "@/components/pixel-office";

const SYSTEM = [
  { href: "/", label: "Home" },
  { href: "/registry", label: "Agents" },
  { href: "/memory", label: "Memory" },
  { href: "/approvals", label: "Approvals" },
];

const KINDS = ["incident", "opportunity", "review", "research", "ops"] as const;

function kindLabel(kind: string) {
  if (kind === "incident") return "Incidents";
  if (kind === "opportunity") return "Ideas";
  if (kind === "review") return "Reviews";
  if (kind === "research") return "Research";
  return "Ops";
}

function kindColor(kind: string) {
  if (kind === "incident") return "var(--danger)";
  if (kind === "opportunity") return "var(--ok)";
  if (kind === "review") return "var(--warn)";
  return "var(--accent)";
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
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="hidden w-[260px] shrink-0 flex-col border-r border-border bg-white md:flex">
        <div className="px-5 pb-4 pt-6">
          <Link href="/" className="block">
            <p className="text-[17px] font-semibold tracking-tight">Product OS</p>
            <p className="mt-1 text-[13px] text-[var(--dim)]">Your product team, in rooms.</p>
          </Link>
        </div>

        <nav className="px-3 pb-4">
          {SYSTEM.map((item) => {
            const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "block rounded-lg px-3 py-1.5 text-[14px] transition-colors",
                  active ? "bg-[var(--elev)] font-medium text-foreground" : "text-[var(--dim)] hover:text-foreground"
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
                <p className="px-3 pb-1 text-[12px] font-medium text-[var(--faint)]">{kindLabel(kind)}</p>
                {group.map((room) => {
                  const href = `/rooms/${room.id}`;
                  const active = path === href;
                  return (
                    <Link
                      key={room.id}
                      href={href}
                      className={cn(
                        "mb-0.5 flex items-start gap-2 rounded-lg px-3 py-2 transition-colors",
                        active ? "bg-[var(--elev)]" : "hover:bg-[var(--elev)]/70"
                      )}
                    >
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: kindColor(kind) }} />
                      <span className="min-w-0 truncate text-[13px] leading-5 text-foreground">{room.title}</span>
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
            <p className="text-[13px] font-medium leading-4">You</p>
            <p className="text-[12px] text-[var(--dim)]">Here with the team</p>
          </div>
        </div>
      </aside>

      <main className={cn("min-w-0 flex-1 bg-background", inRoom ? "overflow-hidden bg-white" : "overflow-y-auto chat-scroll")}>
        {children}
      </main>
    </div>
  );
}
