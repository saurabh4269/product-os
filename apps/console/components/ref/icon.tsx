import { cn } from "@/lib/utils";

/** Material Symbols — matches reference HTML `material-symbols-outlined` usage. */
export function MIcon({
  name,
  className,
  fill,
}: {
  name: string;
  className?: string;
  fill?: boolean;
}) {
  return (
    <span className={cn("material-symbols-outlined", fill && "fill", className)} aria-hidden>
      {name}
    </span>
  );
}
