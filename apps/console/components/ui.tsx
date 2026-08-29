import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-xl border border-border bg-card p-5", className)}
      {...props}
    />
  );
}

export function Badge({
  tone = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "muted" | "ok" | "warn" | "danger" | "high" }) {
  const tones = {
    muted: "bg-muted text-slate-300",
    ok: "bg-accent/15 text-accent",
    warn: "bg-amber-500/15 text-amber-400",
    danger: "bg-danger/15 text-red-400",
    high: "bg-danger text-white",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 font-mono text-[11px] uppercase tracking-wide",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const variants = {
    primary: "bg-accent text-background hover:bg-green-500",
    ghost: "bg-muted text-foreground hover:bg-slate-700",
    danger: "bg-danger text-white hover:bg-red-500",
  };
  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <Card className="border-dashed text-center">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-1 text-sm text-slate-400">{hint}</p>
    </Card>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <Card className="border-danger/40">
      <p className="text-sm text-red-300">{message}</p>
    </Card>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <Card>
      <div className="flex items-center gap-3">
        <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
        <p className="font-mono text-xs uppercase tracking-widest text-slate-400">{label}</p>
      </div>
    </Card>
  );
}
