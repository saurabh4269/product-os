import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("border border-border bg-card p-5", className)} {...props} />;
}

export function Badge({
  tone = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "muted" | "ok" | "warn" | "danger" | "high" | "accent" }) {
  const tones = {
    muted: "text-[var(--dim)]",
    ok: "text-ok",
    warn: "text-warn",
    danger: "text-danger",
    high: "text-danger",
    accent: "text-accent",
  };
  return (
    <span className={cn("text-[11px] uppercase tracking-[0.16em]", tones[tone], className)} {...props} />
  );
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const variants = {
    primary: "bg-accent text-[#100e14] hover:brightness-110",
    ghost: "bg-transparent text-foreground hover:bg-white/5",
    danger: "bg-danger text-[#100e14] hover:brightness-110",
  };
  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center gap-2 px-4 py-2 text-[13px] font-medium transition duration-150 disabled:cursor-not-allowed disabled:opacity-40",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export function Empty({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="py-16 text-center">
      <p className="font-display text-2xl">{title}</p>
      <p className="mt-2 text-[14px] text-[var(--dim)]">{hint}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="px-8 py-16">
      <p className="font-display text-2xl text-danger">Couldn’t reach the office.</p>
      <p className="mt-2 text-[14px] text-[var(--dim)]">{message}</p>
    </div>
  );
}

export function Loading({ label = "Opening" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 px-8 py-16">
      <span className="h-2 w-2 animate-pulse bg-accent" />
      <p className="text-[13px] text-[var(--dim)]">{label}</p>
    </div>
  );
}
