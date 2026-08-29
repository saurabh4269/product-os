"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
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

function titleFor(path: string) {
  if (path === "/") return "Campus";
  if (path.startsWith("/rooms/")) return "Room";
  if (path.startsWith("/agents/")) return "Agent";
  if (path.startsWith("/registry")) return "Agents";
  if (path.startsWith("/memory")) return "Memory";
  if (path.startsWith("/approvals")) return "Approvals";
  return "Product OS";
}

function NavBody({
  path,
  rooms,
  onNavigate,
}: {
  path: string;
  rooms: Room[];
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="px-5 pb-5 pt-7">
        <Link href="/" onClick={onNavigate} className="block">
          <p className="text-[17px] font-semibold tracking-tight">Product OS</p>
          <p className="mt-1 text-[13px] text-[var(--dim)]">A campus for the work.</p>
        </Link>
      </div>

      <nav className="px-3 pb-4">
        {SYSTEM.map((item) => {
          const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "block rounded-full px-3 py-2.5 text-[15px] transition-colors lg:py-1.5 lg:text-[14px]",
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
                    onClick={onNavigate}
                    className={cn(
                      "mb-0.5 block rounded-lg px-3 py-2.5 transition-colors lg:py-1.5",
                      active ? "bg-[var(--elev)]" : "hover:bg-[var(--elev)]"
                    )}
                  >
                    <span className="block truncate text-[14px] leading-5 text-foreground lg:text-[13px]">{room.title}</span>
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
    </>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api
      .rooms()
      .then((r) => setRooms(r.rooms))
      .catch(() => setRooms([]));
  }, [path]);

  useEffect(() => {
    setOpen(false);
  }, [path]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const inRoom = path.startsWith("/rooms/") || path.startsWith("/agents/");
  const onCampus = path === "/";

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background">
      <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center gap-2 border-b border-black/5 bg-white/90 px-3 pt-[env(safe-area-inset-top)] backdrop-blur-md lg:hidden">
        <button
          type="button"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          className="flex h-11 w-11 items-center justify-center rounded-full text-foreground touch-manipulation"
        >
          {open ? <X size={20} strokeWidth={1.75} /> : <Menu size={20} strokeWidth={1.75} />}
        </button>
        <Link href="/" className="min-w-0">
          <p className="truncate text-[15px] font-semibold tracking-tight">{titleFor(path)}</p>
        </Link>
      </header>

      {open ? (
        <button
          type="button"
          aria-label="Close menu"
          className="fixed inset-0 z-40 bg-black/25 lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(86vw,280px)] flex-col border-r border-border bg-white shadow-xl transition-transform duration-200 ease-out lg:static lg:z-0 lg:flex lg:w-[248px] lg:shrink-0 lg:translate-x-0 lg:shadow-none",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <NavBody path={path} rooms={rooms} onNavigate={() => setOpen(false)} />
      </aside>

      <main
        className={cn(
          "min-w-0 flex-1 bg-background pt-[calc(3.5rem+env(safe-area-inset-top))] lg:pt-0",
          inRoom ? "overflow-hidden bg-white" : "overflow-y-auto chat-scroll",
          onCampus && "bg-[#eef2ee]"
        )}
      >
        {children}
      </main>
    </div>
  );
}
