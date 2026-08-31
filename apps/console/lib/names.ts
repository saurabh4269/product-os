/** Match backend `canonical_agent` for agent page links and API calls. */
export function canonicalAgentId(raw: string) {
  if (!raw || raw === "you" || raw === "system") return raw;
  const aliases: Record<string, string> = {
    orchestrator_agent: "orchestrator",
    analytics: "analytics_agent",
    logs: "logs_agent",
    deployment: "deployment_agent",
    customer_voice: "customer_voice_agent",
    feedback: "feedback_agent",
    product: "product_agent",
    risk: "risk_agent",
    code: "code_agent",
    learning: "learning_agent",
    security: "security_policy_agent",
    security_policy: "security_policy_agent",
    coordinator: "coordination_agent",
    coordination: "coordination_agent",
  };
  if (aliases[raw]) return aliases[raw];
  if (raw.endsWith("_agent")) return raw;
  const guessed = `${raw}_agent`;
  return guessed;
}

export function agentHref(id: string) {
  return `/agents/${canonicalAgentId(id)}`;
}

export function shortName(id: string) {
  if (id === "you") return "You";
  if (id === "system") return "System";
  return id
    .replace(/_agent$/, "")
    .replace(/^customer_/, "")
    .replace(/^product_intelligence$/, "intel")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function hashHue(id: string) {
  let n = 0;
  for (let i = 0; i < id.length; i++) n = (n * 31 + id.charCodeAt(i)) >>> 0;
  return n;
}

/** Soft pastel palette — one cute blob per agent, not a busy pixel person. */
export function agentPalette(name: string) {
  if (name === "you") {
    return { bg: "#e8f2ff", fg: "#0071e3" };
  }
  if (name === "system") {
    return { bg: "#f0f0f2", fg: "#86868b" };
  }
  const hue = hashHue(name) % 360;
  return {
    bg: `hsl(${hue} 46% 94%)`,
    fg: `hsl(${hue} 24% 40%)`,
  };
}
