import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-xl border border-border bg-card p-5", className)} {...props} />;
}

export function Badge({
  tone = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "muted" | "ok" | "warn" | "danger" | "high" | "accent" }) {
  const tones = {
    muted: "bg-muted text-[var(--dim)]",
    ok: "bg-ok/15 text-ok",
    warn: "bg-warn/15 text-warn",
    danger: "bg-danger/15 text-danger",
    high: "bg-danger text-white",
    accent: "bg-accent/15 text-accent",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide",
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
    primary: "bg-accent text-white hover:brightness-110",
    ghost: "bg-muted text-foreground hover:bg-white/10",
    danger: "bg-danger text-white hover:brightness-110",
  };
  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition duration-150 disabled:cursor-not-allowed disabled:opacity-50",
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
      <p className="mt-1 text-sm text-[var(--dim)]">{hint}</p>
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
        <p className="font-mono text-xs uppercase tracking-widest text-[var(--dim)]">{label}</p>
      </div>
    </Card>
  );
}
