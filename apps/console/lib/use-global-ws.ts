"use client";

import { useEffect, useRef, useState } from "react";
import { globalSocket } from "@/lib/api";

export type ActivityEvent = {
  ts?: string;
  agent_id?: string;
  message?: string;
  room_id?: string;
  stage?: string;
  tenant_id?: string;
  type?: string;
};

export function useGlobalWs() {
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [tick, setTick] = useState(0);
  const backoff = useRef(1000);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: number | null = null;
    let dead = false;

    function connect() {
      if (dead) return;
      try {
        ws = globalSocket();
        ws.onopen = () => {
          backoff.current = 1000;
        };
        ws.onmessage = (ev) => {
          try {
            const e = JSON.parse(ev.data) as ActivityEvent & { type?: string };
            if (e.type === "activity") {
              setActivity((prev) => [e, ...prev].slice(0, 80));
            }
            if (e.type === "funnel_stage" || e.type === "approval_required" || e.type === "approval_resolved") {
              setTick((t) => t + 1);
            }
          } catch {
            /* ignore */
          }
        };
        ws.onclose = () => {
          if (dead) return;
          timer = window.setTimeout(connect, backoff.current);
          backoff.current = Math.min(backoff.current * 2, 15000);
        };
      } catch {
        timer = window.setTimeout(connect, backoff.current);
      }
    }

    connect();
    return () => {
      dead = true;
      if (timer) window.clearTimeout(timer);
      ws?.close();
    };
  }, []);

  return { activity, tick };
}
