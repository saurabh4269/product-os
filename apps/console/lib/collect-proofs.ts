import type { Bundle, RoomMessage } from "@/lib/api";
import { proofFromArtifact, type ProofPayload } from "@/components/proof-embed";

/** Gather live tool receipts from a room — GA4, BQ, GitHub, mail, etc. */
export function proofsFromRoom(messages: RoomMessage[], bundle: Bundle | null): ProofPayload[] {
  const seen = new Set<string>();
  const out: ProofPayload[] = [];

  function push(p: ProofPayload | null) {
    if (!p?.kind) return;
    const key = `${p.kind}-${p.title}-${p.url || p.console_url || ""}`;
    if (seen.has(key)) return;
    seen.add(key);
    out.push(p);
  }

  for (const msg of messages) {
    push(proofFromArtifact(msg.artifact, msg.artifact_type));
  }

  if (bundle) {
    for (const action of bundle.actions) {
      const art = action.artifacts as Record<string, unknown>;
      const exec = (art?.execution ?? {}) as Record<string, unknown>;
      push(proofFromArtifact({ ...exec, pr_url: exec.pr_url, proof: exec.proof }, "pr"));
      push(proofFromArtifact(art, "code_fix"));
    }
    for (const ev of bundle.evidence) {
      const ref = ev.source_reference || "";
      if (/bigquery|bq|ga4|analytics|warehouse/i.test(ref) || ev.source_type === "warehouse") {
        push({
          kind: ev.source_type.includes("ga4") ? "ga4" : "warehouse",
          title: ev.source_type.replace(/_/g, " "),
          subtitle: ref,
          detail: ev.claim,
          columns: ["claim", "confidence"],
          rows: [{ claim: ev.claim, confidence: ev.confidence }],
          live: true,
          source: "evidence",
        });
      }
    }
  }

  return out;
}

export function metricSparkFromProof(proof?: ProofPayload | null): number[] {
  if (!proof?.rows?.length) return [];
  const col = proof.columns?.find((c) => /conversion|rate|value|metric/i.test(c)) || proof.columns?.[0];
  if (!col) return [];
  return proof.rows
    .map((r) => {
      const v = Number(r[col]);
      return Number.isFinite(v) ? (v > 0 && v < 1 ? v * 100 : v) : 0;
    })
    .filter((n) => n > 0)
    .slice(-12);
}

type ProofCatalog = {
  ga4?: ProofPayload | null;
  warehouse?: ProofPayload | null;
  github?: ProofPayload | null;
  logs?: ProofPayload | null;
  deploys?: ProofPayload | null;
  gateway?: ProofPayload | null;
  cards?: ProofPayload[];
};

/** Deduped live connector cards from proof + proofResources APIs. */
export function mergeProofCatalog(catalog: ProofCatalog, extra: ProofPayload[] = []): ProofPayload[] {
  const cards = [
    catalog.ga4,
    catalog.warehouse,
    catalog.github,
    catalog.logs,
    catalog.deploys,
    catalog.gateway,
    ...(catalog.cards || []),
    ...extra,
  ].filter((c): c is ProofPayload => Boolean(c && c.kind));

  const byKey = new Map<string, ProofPayload>();
  for (const card of cards) {
    const kind = String(card.kind || "unknown");
    const key = `${kind}-${card.title || ""}-${card.url || card.console_url || ""}`;
    const prev = byKey.get(key);
    if (!prev) {
      byKey.set(key, card);
      continue;
    }
    const prevRows = prev.rows?.length ?? 0;
    const nextRows = card.rows?.length ?? 0;
    if (Boolean(card.live) && !prev.live) byKey.set(key, card);
    else if (nextRows > prevRows) byKey.set(key, card);
  }
  return Array.from(byKey.values());
}
