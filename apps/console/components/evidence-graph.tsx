"use client";

import type { Evidence, Hypothesis } from "@/lib/api";

export function EvidenceGraph({
  evidence,
  hypotheses,
}: {
  evidence: Evidence[];
  hypotheses: Hypothesis[];
}) {
  const hyp = hypotheses[0];
  const trusted = evidence.filter((e) => e.trust_level === "trusted");
  const width = 720;
  const height = 280;
  const cx = width / 2;
  const cy = 70;
  const nodes = trusted.map((e, i) => {
    const x = 90 + i * 180;
    const y = 210;
    return { e, x, y };
  });

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label="Evidence graph">
      {nodes.map((n) => (
        <line
          key={n.e.id}
          x1={cx}
          y1={cy + 28}
          x2={n.x}
          y2={n.y - 22}
          stroke={hyp?.supporting_evidence_ids.includes(n.e.id) ? "#16A34A" : "#334155"}
          strokeWidth="1.5"
        />
      ))}
      <circle cx={cx} cy={cy} r="28" fill="#16A34A22" stroke="#16A34A" />
      <text x={cx} y={cy + 4} textAnchor="middle" fill="#F8FAFC" fontSize="11" fontFamily="Fira Code">
        {hyp ? `${Math.round(hyp.confidence * 100)}%` : "—"}
      </text>
      <text x={cx} y={24} textAnchor="middle" fill="#94A3B8" fontSize="10">
        hypothesis
      </text>
      {nodes.map((n) => (
        <g key={n.e.id}>
          <rect x={n.x - 70} y={n.y - 22} width="140" height="44" rx="8" fill="#0E1223" stroke="#334155" />
          <text x={n.x} y={n.y - 4} textAnchor="middle" fill="#F8FAFC" fontSize="10">
            {n.e.source_type}
          </text>
          <text x={n.x} y={n.y + 12} textAnchor="middle" fill="#94A3B8" fontSize="9" fontFamily="Fira Code">
            {n.e.independence_group}
          </text>
        </g>
      ))}
    </svg>
  );
}
