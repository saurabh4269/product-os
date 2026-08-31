"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useToastWsBridge } from "@/lib/use-global-ws";

export type ToastItem = {
  id: string;
  message: string;
  href?: string;
  hot?: boolean;
};

type ToastContextValue = {
  toasts: ToastItem[];
  push: (message: string, opts?: { href?: string; hot?: boolean }) => void;
  dismiss: (id: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, opts?: { href?: string; hot?: boolean }) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setToasts((prev) => [{ id, message, href: opts?.href, hot: opts?.hot }, ...prev].slice(0, 5));
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 8000);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const value = useMemo(() => ({ toasts, push, dismiss }), [toasts, push, dismiss]);

  useToastWsBridge(value);

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  return useContext(ToastContext);
}
