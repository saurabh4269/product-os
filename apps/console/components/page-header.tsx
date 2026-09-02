import { cn } from "@/lib/utils";

/** Shared page title row — matches registry, data plane, outcomes. */
export function PageHeader({
  title,
  children,
  className,
}: {
  title: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "mb-margin-lg flex flex-col justify-between gap-4 md:flex-row md:items-end",
        className
      )}
    >
      <h1 className="text-display-lg font-bold tracking-tight text-text-primary">{title}</h1>
      {children ? <div className="flex flex-wrap items-center gap-2">{children}</div> : null}
    </header>
  );
}

export function PageStatPill({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "rounded-full border border-border bg-white px-2.5 py-1 text-[12px] text-text-secondary",
        className
      )}
    >
      {children}
    </span>
  );
}
