"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BookMarked,
  CalendarDays,
  CircleCheck,
  FlaskConical,
  House,
  Layers,
  PanelLeftClose,
  PanelLeftOpen,
  Plug,
  Users,
} from "lucide-react";
import { api, type Room } from "@/lib/api";
import { cn } from "@/lib/utils";
import { BeanMark } from "@/components/mascot";
import { AgentBadge } from "@/components/agent-badge";
import { useGlobalWs } from "@/lib/use-global-ws";
import { HumanInputProvider } from "@/lib/human-input-context";
import { HumanInputModals } from "@/components/human-input-modals";
import { ToastProvider } from "@/lib/toast-context";
import { ToastHost } from "@/components/toast-host";

const STORAGE = "loop-sidebar";

const SYSTEM = [
  { href: "/", label: "Home", icon: House },
  { href: "/registry", label: "Agents", icon: Users },
  { href: "/memory", label: "Memory", icon: BookMarked },
  { href: "/approvals", label: "Approvals", icon: CircleCheck, badgeKey: "approvals" as const },
  { href: "/workflows", label: "Workflows", icon: CalendarDays },
  { href: "/labs", label: "Labs", icon: FlaskConical },
  { href: "/connect", label: "Connect", icon: Plug },
  { href: "/labs/architecture", label: "Architecture", icon: Layers },
] as const;

const KINDS = ["incident", "opportunity", "review", "research", "ops"] as const;

function kindLabel(kind: string) {
  if (kind === "incident") return "Incidents";
  if (kind === "opportunity") return "Ideas";
  if (kind === "review") return "Reviews";
  if (kind === "research") return "Research";
  return "Ops";
}

function isActive(path: string, href: string) {
  if (href === "/") return path === "/";
  if (href === "/labs") return path === "/labs";
  return path.startsWith(href);
}

function Tip({
  label,
  show,
  fill,
  children,
}: {
  label: string;
  show: boolean;
  fill?: boolean;
  children: React.ReactNode;
}) {
  return (
    <span className={cn("group relative flex", show ? "justify-center" : fill ? "w-full justify-start" : "shrink-0")}>
      {children}
      {show ? (
        <span className="pointer-events-none absolute left-full top-1/2 z-[60] ml-3 hidden -translate-y-1/2 whitespace-nowrap rounded-md bg-[#1d1d1f] px-2 py-1 text-[12px] text-white opacity-0 shadow-lg group-hover:flex group-hover:opacity-100">
          {label}
        </span>
      ) : null}
    </span>
  );
}

function RoomList({
  path,
  rooms,
  onNavigate,
}: {
  path: string;
  rooms: Room[];
  onNavigate?: () => void;
}) {
  return (
    <div className="flex-1 overflow-y-auto chat-scroll px-2 pb-4 text-left">
      {KINDS.map((kind) => {
        const group = rooms.filter((r) => r.kind === kind);
        if (!group.length) return null;
        return (
          <div key={kind} className="mb-4">
            <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--faint)]">
              {kindLabel(kind)}
            </p>
            {group.map((room) => {
              const href = `/rooms/${room.id}`;
              return (
                <Link
                  key={room.id}
                  href={href}
                  onClick={onNavigate}
                  data-active={path === href ? "true" : undefined}
                  className="nav-item mb-0.5 block px-3 py-2 pl-3.5 text-[13px] leading-5"
                >
                  <span className="block truncate">{room.title}</span>
                </Link>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function SystemLinks({
  path,
  collapsed,
  onNavigate,
  approvalsPending = 0,
}: {
  path: string;
  collapsed: boolean;
  onNavigate?: () => void;
  approvalsPending?: number;
}) {
  return (
    <nav className={cn("flex flex-col gap-0.5", collapsed ? "items-center px-2" : "items-stretch px-2")}>
      {SYSTEM.map((item) => {
        const Icon = item.icon;
        const active = isActive(path, item.href);
        const badge =
          "badgeKey" in item && item.badgeKey === "approvals" && approvalsPending > 0 ? approvalsPending : 0;
        return (
          <Tip key={item.href} label={item.label} show={collapsed} fill={!collapsed}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              data-active={active ? "true" : undefined}
              className={cn(
                "nav-item group relative",
                collapsed ? "h-11 w-11 justify-center" : "h-10 w-full justify-start gap-3 px-3 pl-3.5",
              )}
            >
              <Icon size={18} strokeWidth={1.75} />
              {collapsed ? <span className="sr-only">{item.label}</span> : <span className="text-[14px]">{item.label}</span>}
              {badge ? (
                <span
                  className={cn(
                    "rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-semibold text-white",
                    collapsed ? "absolute right-1 top-1" : "ml-auto"
                  )}
                >
                  {badge}
                </span>
              ) : null}
            </Link>
          </Tip>
        );
      })}
    </nav>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { tick } = useGlobalWs();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [approvalsPending, setApprovalsPending] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [desktop, setDesktop] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .rooms()
      .then((r) => setRooms(r.rooms))
      .catch(() => setRooms([]));
  }, [path, tick]);

  useEffect(() => {
    api
      .status()
      .then((s) => setApprovalsPending(s.approvals_pending ?? 0))
      .catch(() => setApprovalsPending(0));
  }, [tick]);

  useEffect(() => {
    const wide = window.matchMedia("(min-width: 1024px)");
    const apply = () => setDesktop(wide.matches);
    apply();
    wide.addEventListener("change", apply);
    const stored = window.localStorage.getItem(STORAGE);
    if (stored === "open") setExpanded(true);
    else if (stored === "closed") setExpanded(false);
    else setExpanded(wide.matches);
    setReady(true);
    return () => wide.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (!ready) return;
    window.localStorage.setItem(STORAGE, expanded ? "open" : "closed");
  }, [expanded, ready]);

  useEffect(() => {
    if (!ready || desktop) return;
    setExpanded(false);
  }, [path, ready, desktop]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
      if (e.key === "[" && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        setExpanded((v) => !v);
      }
      if (e.key === "Escape" && !desktop) setExpanded(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [desktop]);

  const inRoom = path.startsWith("/rooms/") || path.startsWith("/agents/");
  const fillMain = inRoom;
  const onCampus = path === "/";
  const wide = expanded;

  return (
    <ToastProvider>
    <HumanInputProvider>
    <div className="flex h-[100dvh] overflow-hidden bg-background">
      <aside
        className={cn(
          "relative z-30 flex h-full shrink-0 flex-col border-r border-border bg-white text-left transition-[width] duration-200 ease-out",
          wide ? "w-[min(16.25rem,calc(100vw-3.5rem))]" : "w-16"
        )}
      >
        <div className={cn("flex", wide ? "items-center gap-2 px-3 pt-5 pb-4" : "flex-col items-center gap-2 px-2 pt-4 pb-3")}>
          <Link href="/" className={cn("group flex min-w-0 items-center", wide ? "flex-1 gap-2.5" : "h-11 w-11 justify-center")}>
            <BeanMark size={32} />
            {wide ? (
              <span className="min-w-0">
                <p className="truncate text-[15px] font-semibold leading-5 tracking-tight">Product OS</p>
              </span>
            ) : (
              <span className="sr-only">Product OS</span>
            )}
          </Link>
          <Tip label={expanded ? "Close sidebar" : "Open sidebar"} show={!wide}>
            <button
              type="button"
              aria-label={expanded ? "Close sidebar" : "Open sidebar"}
              aria-expanded={expanded}
              onClick={() => setExpanded((v) => !v)}
              className={cn(
                "group flex shrink-0 items-center justify-center rounded-lg text-[var(--dim)] transition-colors hover:bg-[var(--elev)] hover:text-foreground touch-manipulation",
                wide ? "h-8 w-8" : "h-11 w-11"
              )}
            >
              {expanded ? <PanelLeftClose size={16} strokeWidth={1.75} /> : <PanelLeftOpen size={16} strokeWidth={1.75} />}
            </button>
          </Tip>
        </div>

        <SystemLinks
          path={path}
          collapsed={!wide}
          onNavigate={!desktop ? () => setExpanded(false) : undefined}
          approvalsPending={approvalsPending}
        />

        {wide ? (
          <>
            <div className="mx-4 my-4 h-px bg-border" />
            <RoomList path={path} rooms={rooms} />
          </>
        ) : (
          <div className="flex-1" />
        )}

        <div className={cn("mt-auto border-t border-border", wide ? "flex items-center gap-2.5 px-3 py-3" : "flex justify-center pb-5 pt-3")}>
          <AgentBadge name="you" size={wide ? 32 : 28} variant="face" />
          {wide ? (
            <div>
              <p className="text-[13px] font-medium leading-4">You</p>
            </div>
          ) : (
            <span className="sr-only">You</span>
          )}
        </div>
      </aside>

      <main
        className={cn(
          "flex min-h-0 min-w-0 flex-1 flex-col bg-background",
          fillMain ? "overflow-hidden bg-white" : "overflow-y-auto chat-scroll",
          onCampus && "bg-[#eef2ee]"
        )}
      >
        {children}
      </main>
    </div>
    <HumanInputModals />
    <ToastHost />
    </HumanInputProvider>
    </ToastProvider>
  );
}
