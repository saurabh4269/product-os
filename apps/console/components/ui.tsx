import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { BeanMark, BeanWave } from "@/components/mascot";
import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function Surface({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("surface", className)} {...props} />;
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("surface-lg p-5", className)} {...props} />;
}

/** Minimal page title — no subtitle essays (SaaS / refero pattern). */
export function PageHeader({
  title,
  action,
  className,
}: {
  title: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      <h1 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">{title}</h1>
      {action}
    </div>
  );
}

/** Tappable list row — chevron implies drill-down without copy. */
export function RowLink({
  href,
  leading,
  title,
  subtitle,
  trailing,
  className,
  onClick,
}: {
  href: string;
  leading?: ReactNode;
  title: string;
  subtitle?: ReactNode;
  trailing?: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={cn("group row-link px-4 py-3.5 sm:px-5 sm:py-4", className)}
    >
      {leading}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] font-medium">{title}</span>
        {subtitle ? <span className="mt-0.5 block truncate text-[12px] text-[var(--faint)]">{subtitle}</span> : null}
      </span>
      {trailing}
      <ChevronRight className="h-4 w-4 shrink-0 text-[var(--faint)] opacity-40 transition group-hover:opacity-100 group-hover:translate-x-0.5" />
    </Link>
  );
}

export function Chip({
  tone = "muted",
  className,
  children,
}: {
  tone?: "muted" | "ok" | "warn" | "danger" | "accent";
  className?: string;
  children: ReactNode;
}) {
  const tones = {
    muted: "bg-[var(--elev)] text-[var(--faint)]",
    ok: "bg-ok/10 text-ok",
    warn: "bg-warn/10 text-warn",
    danger: "bg-danger/10 text-danger",
    accent: "bg-accent/10 text-accent",
  };
  return (
    <span className={cn("inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide", tones[tone], className)}>
      {children}
    </span>
  );
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

export function IconButton({
  className,
  label,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-lg text-[var(--dim)] transition-colors duration-150 ease-out hover:bg-[var(--elev)] hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40 press",
        className
      )}
      {...props}
    />
  );
}

export function Button({
  className,
  variant = "primary",
  size = "default",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "outline" | "danger";
  size?: "default" | "sm" | "icon";
}) {
  const variants = {
    primary: "bg-accent text-white shadow-sm hover:bg-[#0077ed] focus-visible:ring-accent/40",
    ghost: "bg-transparent text-foreground hover:bg-[var(--elev)]",
    outline: "border border-border bg-card text-foreground shadow-sm hover:bg-[var(--elev)]",
    danger: "bg-transparent text-danger hover:bg-danger/10",
  };
  const sizes = {
    default: "h-10 rounded-full px-4 text-[14px]",
    sm: "h-8 rounded-full px-3 text-[13px]",
    icon: "h-9 w-9 rounded-lg p-0",
  };
  return (
    <button
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 font-medium transition-all duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-40 press",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}

export function Empty({ title, hint, className }: { title: string; hint?: string; className?: string }) {
  return (
    <div className={cn("py-16 text-center fade-in", className)}>
      <p className="text-[18px] font-medium">{title}</p>
      {hint ? <p className="mt-2 text-[14px] text-[var(--dim)]">{hint}</p> : null}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="page-pad flex items-start gap-4 fade-in">
      <BeanMark size={48} />
      <div>
        <p className="text-[18px] font-medium">Can’t reach the app right now.</p>
        <p className="mt-2 text-[14px] text-[var(--dim)]">{message}</p>
        <button type="button" onClick={() => window.location.reload()} className="mt-4 text-[14px] font-medium text-accent press">
          Try again
        </button>
      </div>
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 page-pad fade-in">
      <BeanWave />
      <p className="text-[14px] text-[var(--dim)]">{label}</p>
    </div>
  );
}
