"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { useHumanInputWsBridge } from "@/lib/use-global-ws";

export type OAuthPrompt = {
  reason: string;
  authorize_url: string;
  redirect_uri?: string;
  room_id?: string;
};

export type CalendarSlot = {
  start: string;
  end: string;
  duration_minutes?: number;
};

export type CalendarPrompt = {
  title: string;
  room_id?: string;
  action_id?: string;
  slots: CalendarSlot[];
};

type HumanInputContextValue = {
  pendingOAuth: OAuthPrompt | null;
  pendingCalendar: CalendarPrompt | null;
  setPendingOAuth: (p: OAuthPrompt | null) => void;
  setPendingCalendar: (p: CalendarPrompt | null) => void;
  dismissOAuth: () => void;
  dismissCalendar: () => void;
};

const HumanInputContext = createContext<HumanInputContextValue | null>(null);

export function HumanInputProvider({ children }: { children: ReactNode }) {
  const [pendingOAuth, setPendingOAuth] = useState<OAuthPrompt | null>(null);
  const [pendingCalendar, setPendingCalendar] = useState<CalendarPrompt | null>(null);

  const dismissOAuth = useCallback(() => setPendingOAuth(null), []);
  const dismissCalendar = useCallback(() => setPendingCalendar(null), []);

  const value = useMemo(
    () => ({
      pendingOAuth,
      pendingCalendar,
      setPendingOAuth,
      setPendingCalendar,
      dismissOAuth,
      dismissCalendar,
    }),
    [pendingOAuth, pendingCalendar, dismissOAuth, dismissCalendar]
  );

  useHumanInputWsBridge(value);

  return <HumanInputContext.Provider value={value}>{children}</HumanInputContext.Provider>;
}

export function useHumanInput() {
  return useContext(HumanInputContext);
}
