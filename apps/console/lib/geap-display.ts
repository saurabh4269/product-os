import type { GeapStatusPayload } from "@/lib/api";

/** Short id for chips — e.g. 7709236223511887872 → 7709… */
export function geapEngineShortId(payload: GeapStatusPayload | null | undefined): string | null {
  if (!payload) return null;
  const raw =
    payload.geap?.agent_engine_short_id ||
    payload.geap?.agent_engine_id ||
    payload.live_engine?.resource_name ||
    payload.memory_bank?.agent_engine_id ||
    null;
  if (!raw) return null;
  const short = raw.includes("/") ? raw.split("/").pop()! : raw;
  if (short.length <= 8) return short;
  return `${short.slice(0, 4)}…`;
}

export function geapEngineFullShortId(payload: GeapStatusPayload | null | undefined): string | null {
  if (!payload) return null;
  const raw =
    payload.geap?.agent_engine_short_id ||
    payload.geap?.agent_engine_id ||
    payload.live_engine?.resource_name ||
    payload.memory_bank?.agent_engine_id ||
    null;
  if (!raw) return null;
  return raw.includes("/") ? raw.split("/").pop()! : raw;
}

export function geapMemoryBankUri(payload: GeapStatusPayload | null | undefined): string | null {
  if (!payload) return null;
  return (
    payload.memory_bank?.memory_bank_uri ||
    payload.geap?.memory_bank_uri ||
    (geapEngineFullShortId(payload) ? `agentengine://${geapEngineFullShortId(payload)}` : null)
  );
}

export function geapDisplayName(payload: GeapStatusPayload | null | undefined): string {
  return (
    payload?.geap?.display_name ||
    payload?.live_engine?.display_name ||
    "loop-incident-orchestrator"
  );
}

export function geapOperational(payload: GeapStatusPayload | null | undefined): boolean {
  if (!payload) return false;
  return Boolean(payload.geap?.enabled && payload.geap?.operational);
}

export function geapMemoryOperational(payload: GeapStatusPayload | null | undefined): boolean {
  if (!payload) return false;
  return Boolean(payload.memory_bank?.operational || payload.memory_bank?.enabled);
}

export function geapRoutingLine(payload: GeapStatusPayload | null | undefined): string {
  return payload?.routing?.signals || "geap → adk worker → inline adk → LoopEngine";
}

export function geapVertexConsoleUrl(payload: GeapStatusPayload | null | undefined): string | null {
  const project = payload?.geap?.project || "mystical-timing-442601-q8";
  const region = payload?.geap?.region || "us-central1";
  const engineId = geapEngineFullShortId(payload);
  if (!engineId) {
    return `https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=${project}`;
  }
  return `https://console.cloud.google.com/vertex-ai/agents/locations/${region}/agent-engines/${engineId}?project=${project}`;
}
