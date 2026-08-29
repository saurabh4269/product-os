"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  GitBranch,
  Gavel,
  LayoutDashboard,
  Scale,
  Shield,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Pulse", icon: LayoutDashboard },
  { href: "/investigations", label: "Rooms", icon: Activity },
  { href: "/approvals", label: "Approvals", icon: Gavel },
  { href: "/outcomes", label: "Outcomes", icon: Scale },
  { href: "/governance", label: "Governance", icon: Shield },
  { href: "/opportunities", label: "Opportunities", icon: Sparkles },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 border-r border-border bg-[#070b16] md:flex md:flex-col">
        <div className="px-5 py-6">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.28em] text-accent">LOOP</span>
            <span className="text-sm text-slate-400">Northstar Pay</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((item) => {
            const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150",
                  active ? "bg-muted text-foreground" : "text-slate-400 hover:bg-muted/60 hover:text-foreground"
                )}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-border px-5 py-4 font-mono text-[11px] text-slate-500">
          <div className="flex items-center gap-2">
            <GitBranch size={12} />
            us-central1 · failOpen=false
          </div>
        </div>
      </aside>
      <div className="md:pl-60">
        <header className="sticky top-0 z-10 border-b border-border/80 bg-background/80 backdrop-blur">
          <div className="flex items-center justify-between px-6 py-3">
            <p className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
              Autonomous reliability · evidence first
            </p>
            <span className="rounded-full bg-accent/15 px-2 py-0.5 font-mono text-[10px] text-accent">
              live warehouse
            </span>
          </div>
        </header>
        <main className="px-6 py-8">{children}</main>
      </div>
    </div>
  );
}
