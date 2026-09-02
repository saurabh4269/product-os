"use client";

import { useEffect, useSyncExternalStore } from "react";
import { globalSocket } from "@/lib/api";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";
import type { CalendarPrompt, OAuthPrompt } from "@/lib/human-input-context";
import type { PendingApproval } from "@/lib/demo-guide-context";

export type ActivityEvent = {
  ts?: string;
  agent_id?: string;
  message?: string;
  room_id?: string;
  stage?: string;
  tenant_id?: string;
  type?: string;
};

export type ConnectionStatus = "connecting" | "live" | "reconnecting" | "offline";

type DemoHandlers = {
  active?: boolean;
  setHighlightStage?: (stage: string | null) => void;
  setFleetWorking?: (on: boolean) => void;
  setPendingApproval?: (payload: PendingApproval | null) => void;
};

type HumanInputHandlers = {
  setPendingOAuth?: (p: OAuthPrompt | null) => void;
  setPendingCalendar?: (p: CalendarPrompt | null) => void;
};

type ToastHandlers = {
  push?: (message: string, opts?: { href?: string; hot?: boolean }) => void;
};

type WsSnapshot = {
  activity: ActivityEvent[];
  tick: number;
  connection: ConnectionStatus;
  incidentLifecycle: { tenantId: string; lifecycle: Record<string, unknown> } | null;
};

let ws: WebSocket | null = null;
let timer: number | null = null;
const conn = { dead: false };
let backoff = 1000;
let demoHandlers: DemoHandlers = {};
let humanInputHandlers: HumanInputHandlers = {};
let toastHandlers: ToastHandlers = {};

const snapshot: WsSnapshot = {
  activity: [],
  tick: 0,
  connection: "connecting",
  incidentLifecycle: null,
};

const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function setSnapshot(patch: Partial<WsSnapshot>) {
  Object.assign(snapshot, patch);
  emit();
}

function handleMessage(ev: MessageEvent) {
  try {
    const e = JSON.parse(ev.data) as ActivityEvent & {
      type?: string;
      stage?: string;
      activity?: ActivityEvent[];
      approval?: PendingApproval;
      kind?: string;
      reason?: string;
      authorize_url?: string;
      redirect_uri?: string;
      title?: string;
      slots?: CalendarPrompt["slots"];
      action_id?: string;
      event_url?: string;
      pr_url?: string;
      tenant_id?: string;
      lifecycle?: Record<string, unknown>;
    };
    const d = demoHandlers;
    const h = humanInputHandlers;
    const t = toastHandlers;
    if (e.type === "initial_state") {
      if (Array.isArray(e.activity)) snapshot.activity = e.activity.slice(0, 80);
      setSnapshot({ tick: snapshot.tick + 1 });
      return;
    }
    if (e.type === "activity") {
      snapshot.activity = [e, ...snapshot.activity].slice(0, 80);
      emit();
    }
    if (e.type === "funnel_stage" && e.stage) {
      setPipelineHighlight(e.stage);
      if (d?.active) {
        d.setHighlightStage?.(e.stage);
        if (e.stage === "approve" || e.stage === "learn" || e.stage === "verify") {
          d.setFleetWorking?.(false);
        }
      }
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "approval_required") {
      setPipelineHighlight("approve");
      if (e.approval) d.setPendingApproval?.(e.approval);
      d.setHighlightStage?.("approve");
      d.setFleetWorking?.(false);
      t.push?.("Approval needed", { hot: true });
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "approval_resolved") {
      d.setPendingApproval?.(null);
      t.push?.("Approval recorded");
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "human_input_required") {
      if (e.kind === "oauth") {
        h.setPendingOAuth?.({
          reason: e.reason || "",
          authorize_url: e.authorize_url || "/api/oauth/google/start",
          redirect_uri: e.redirect_uri,
          room_id: e.room_id,
        });
      }
      if (e.kind === "calendar" && e.slots?.length) {
        h.setPendingCalendar?.({
          title: e.title || "Pick a review slot",
          room_id: e.room_id,
          action_id: e.action_id,
          slots: e.slots,
        });
      }
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "payoff") {
      if (e.kind === "pr_opened" && e.pr_url) {
        t.push?.("Pull request opened", { href: e.pr_url, hot: true });
      }
      if (e.kind === "calendar_scheduled") {
        t.push?.("Calendar hold placed", { href: e.event_url, hot: true });
      }
      if (e.kind === "verified" && e.room_id) {
        t.push?.("Outcome verified", { href: `/rooms/${e.room_id}` });
      }
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "work_card" || e.type === "artifact" || e.type === "message") {
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "orchestration" || e.type === "signal_detected") {
      setSnapshot({ tick: snapshot.tick + 1 });
    }
    if (e.type === "incident_lifecycle" && e.tenant_id && e.lifecycle) {
      snapshot.incidentLifecycle = {
        tenantId: String(e.tenant_id),
        lifecycle: e.lifecycle as Record<string, unknown>,
      };
      setSnapshot({ tick: snapshot.tick + 1 });
    }
  } catch {
    /* ignore */
  }
}

function connect() {
  if (conn.dead) return;
  setSnapshot({ connection: snapshot.connection === "live" ? "live" : "connecting" });
  try {
    ws = globalSocket();
    ws.onopen = () => {
      backoff = 1000;
      setSnapshot({ connection: "live" });
    };
    ws.onmessage = handleMessage;
    ws.onclose = () => {
      if (conn.dead) return;
      setSnapshot({ connection: "reconnecting" });
      timer = window.setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 15000);
    };
    ws.onerror = () => {
      if (snapshot.connection !== "live") {
        setSnapshot({ connection: "reconnecting" });
      }
    };
  } catch {
    setSnapshot({ connection: "offline" });
    timer = window.setTimeout(connect, backoff);
  }
}

function ensureConnected() {
  if (typeof window === "undefined") return;
  if (!ws && !conn.dead) connect();
}

function subscribe(listener: () => void) {
  ensureConnected();
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return snapshot;
}

/** Register demo-guide handlers for WS-driven chapter + modal state. */
export function registerDemoWsHandlers(handlers: DemoHandlers | null) {
  demoHandlers = handlers ?? {};
}

export function registerHumanInputWsHandlers(handlers: HumanInputHandlers | null) {
  humanInputHandlers = handlers ?? {};
}

export function registerToastWsHandlers(handlers: ToastHandlers | null) {
  toastHandlers = handlers ?? {};
}

export function useGlobalWs() {
  const snap = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  return {
    activity: snap.activity,
    tick: snap.tick,
    connection: snap.connection,
    incidentLifecycle: snap.incidentLifecycle,
  };
}

/** Wire demo context into the shared WS connection (homepage only). */
export function useDemoWsBridge(demo: DemoHandlers | null | undefined) {
  useEffect(() => {
    if (!demo) {
      registerDemoWsHandlers(null);
      return;
    }
    registerDemoWsHandlers({
      active: demo.active,
      setHighlightStage: demo.setHighlightStage,
      setFleetWorking: demo.setFleetWorking,
      setPendingApproval: demo.setPendingApproval,
    });
    return () => registerDemoWsHandlers(null);
  }, [demo, demo?.active]);
}

/** Wire toast notifications into shared WS (shell). */
export function useToastWsBridge(handlers: ToastHandlers | null | undefined) {
  useEffect(() => {
    if (!handlers) {
      registerToastWsHandlers(null);
      return;
    }
    registerToastWsHandlers({ push: handlers.push });
    return () => registerToastWsHandlers(null);
  }, [handlers, handlers?.push]);
}

/** Wire human-input modals into shared WS (shell). */
export function useHumanInputWsBridge(handlers: HumanInputHandlers | null | undefined) {
  useEffect(() => {
    if (!handlers) {
      registerHumanInputWsHandlers(null);
      return;
    }
    registerHumanInputWsHandlers({
      setPendingOAuth: handlers.setPendingOAuth,
      setPendingCalendar: handlers.setPendingCalendar,
    });
    return () => registerHumanInputWsHandlers(null);
  }, [handlers, handlers?.setPendingOAuth, handlers?.setPendingCalendar]);
}
