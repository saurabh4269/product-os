"use client";

import Link from "next/link";
import { useToast } from "@/lib/toast-context";
import { cn } from "@/lib/utils";

export function ToastHost() {
  const toast = useToast();
  if (!toast?.toasts.length) return null;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex max-w-sm flex-col gap-2">
      {toast.toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto rounded-xl border bg-white px-4 py-3 shadow-lg transition-all",
            t.hot ? "border-accent/40 ring-2 ring-accent/15" : "border-border"
          )}
        >
          <p className={cn("text-[13px] font-medium", t.hot ? "text-accent" : "text-foreground")}>{t.message}</p>
          {t.href ? (
            <Link href={t.href} className="mt-1 block text-[12px] text-accent hover:underline">
              Open →
            </Link>
          ) : null}
          <button type="button" className="mt-1 text-[11px] text-[var(--faint)] hover:text-foreground" onClick={() => toast.dismiss(t.id)}>
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}
