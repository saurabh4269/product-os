import { PipMark, PipWave } from "@/components/mascot";
import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, HTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-2xl border border-border bg-card p-5", className)} {...props} />;
}

export function Badge({
  tone = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "muted" | "ok" | "warn" | "danger" | "high" | "accent" }) {
  const tones = {
    muted: "text-[var(--faint)]",
    ok: "text-ok",
    warn: "text-warn",
    danger: "text-danger",
    high: "text-danger",
    accent: "text-accent",
  };
  return <span className={cn("text-[12px] font-medium", tones[tone], className)} {...props} />;
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const variants = {
    primary: "bg-accent text-white hover:bg-[#0077ed]",
    ghost: "bg-transparent text-foreground hover:bg-muted",
    danger: "bg-transparent text-danger hover:bg-[#de3b2f0f]",
  };
  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center gap-2 rounded-full px-4 py-2 text-[14px] font-medium transition duration-150 disabled:cursor-not-allowed disabled:opacity-40",
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
      <p className="text-[18px] font-medium">{title}</p>
      <p className="mt-2 text-[14px] text-[var(--dim)]">{hint}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="page-pad flex items-start gap-4">
      <PipMark size={48} className="rounded-2xl" />
      <div>
        <p className="text-[18px] font-medium">Can’t reach the app right now.</p>
        <p className="mt-2 text-[14px] text-[var(--dim)]">{message}</p>
      </div>
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 page-pad">
      <PipWave />
      <p className="text-[14px] text-[var(--dim)]">{label}</p>
    </div>
  );
}
