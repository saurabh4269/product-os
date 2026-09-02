import type { RegistryAgent } from "@/lib/api";
import { cn } from "@/lib/utils";
import { MIcon } from "@/components/ref/icon";

function riskTone(level: string) {
  if (level === "HIGH") return "text-accent-error";
  if (level === "MEDIUM") return "text-amber-600";
  return "text-accent-success";
}

function trustTooltip(a: Pick<RegistryAgent, "risk_level" | "trust_boundary" | "capabilities" | "environment">) {
  const caps = a.capabilities.slice(0, 6).join(", ");
  const env = a.environment && a.environment !== "prod" ? ` · ${a.environment}` : "";
  return `${a.risk_level} risk · ${a.trust_boundary}${env}${caps ? ` · ${caps}` : ""}`;
}

/** One glyph for registry cards — full identity on the agent page. */
export function AgentTrustGlyph({
  agent,
  className,
}: {
  agent: Pick<RegistryAgent, "risk_level" | "trust_boundary" | "capabilities" | "environment">;
  className?: string;
}) {
  const high = agent.risk_level === "HIGH";
  return (
    <span
      title={trustTooltip(agent)}
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-full bg-surface-base text-[18px]",
        riskTone(agent.risk_level),
        className
      )}
      aria-label={trustTooltip(agent)}
    >
      <MIcon name={high ? "gpp_maybe" : "shield"} className="text-[18px]" />
    </span>
  );
}

export function AgentIdentityPanel({ agent }: { agent: RegistryAgent }) {
  return (
    <div className="rounded-xl border border-surface-subtle/60 bg-white p-4">
      <p className="text-label-caps uppercase text-text-secondary">Identity</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-body-sm">
        <div>
          <dt className="text-on-surface-variant">Risk</dt>
          <dd className="font-medium text-text-primary">{agent.risk_level}</dd>
        </div>
        <div>
          <dt className="text-on-surface-variant">Trust boundary</dt>
          <dd className="font-mono text-text-primary">{agent.trust_boundary}</dd>
        </div>
        {agent.environment && agent.environment !== "prod" ? (
          <div className="col-span-2">
            <dt className="text-on-surface-variant">Environment</dt>
            <dd className="font-medium text-text-primary">{agent.environment}</dd>
          </div>
        ) : null}
      </dl>
      {agent.capabilities.length ? (
        <>
          <p className="mt-4 text-label-caps uppercase text-text-secondary">Capabilities</p>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {agent.capabilities.map((c) => (
              <li
                key={c}
                className="rounded-md border border-surface-subtle bg-surface-base px-2 py-0.5 font-mono text-[11px] text-on-surface-variant"
              >
                {c}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
