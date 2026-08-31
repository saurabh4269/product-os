"use client";

import { useState } from "react";
import type { Evidence, Hypothesis } from "@/lib/api";
import { cn } from "@/lib/utils";

export function EvidenceGraph({
  evidence,
  hypotheses,
}: {
  evidence: Evidence[];
  hypotheses: Hypothesis[];
}) {
  const hyp = hypotheses[0];
  const trusted = evidence.filter((e) => e.trust_level === "trusted");
  const untrusted = evidence.filter((e) => e.trust_level !== "trusted");
  const [picked, setPicked] = useState<string | null>(null);
  const width = 720;
  const height = 320;
  const cx = width / 2;
  const cy = 70;
  const nodes = trusted.map((e, i) => {
    const x = 90 + i * Math.min(180, Math.floor((width - 180) / Math.max(trusted.length, 1)));
    const y = 210;
    return { e, x, y };
  });

  return (
    <div className="rounded-2xl border border-border bg-white p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full" role="img" aria-label="Evidence graph">
        {nodes.map((n) => {
          const linked = hyp?.supporting_evidence_ids.includes(n.e.id);
          const hot = picked === n.e.id;
          return (
            <line
              key={`line-${n.e.id}`}
              x1={cx}
              y1={cy + 28}
              x2={n.x}
              y2={n.y - 22}
              stroke={linked ? "#248a3d" : "#d2d2d7"}
              strokeWidth={hot ? 2.5 : linked ? 2 : 1.5}
              opacity={picked && !hot ? 0.35 : 1}
            />
          );
        })}
        <circle cx={cx} cy={cy} r="28" fill="#eef2ee" stroke="#0071e3" strokeWidth="2" />
        <text x={cx} y={cy + 4} textAnchor="middle" fill="#1d1d1f" fontSize="11" fontWeight="600">
          {hyp ? `${Math.round(hyp.confidence * 100)}%` : "—"}
        </text>
        <text x={cx} y={24} textAnchor="middle" fill="#86868b" fontSize="10">
          hypothesis
        </text>
        {nodes.map((n) => {
          const linked = hyp?.supporting_evidence_ids.includes(n.e.id);
          const hot = picked === n.e.id;
          return (
            <g
              key={n.e.id}
              className="cursor-pointer"
              onMouseEnter={() => setPicked(n.e.id)}
              onMouseLeave={() => setPicked(null)}
              onClick={() => setPicked((p) => (p === n.e.id ? null : n.e.id))}
            >
              <rect
                x={n.x - 70}
                y={n.y - 22}
                width="140"
                height="44"
                rx="10"
                fill={hot ? "#f5f5f7" : "#ffffff"}
                stroke={linked ? "#248a3d" : "#d2d2d7"}
                strokeWidth={hot ? 2 : 1.5}
              />
              <text x={n.x} y={n.y - 4} textAnchor="middle" fill="#1d1d1f" fontSize="10" fontWeight="600">
                {n.e.source_type}
              </text>
              <text x={n.x} y={n.y + 12} textAnchor="middle" fill="#86868b" fontSize="9">
                {n.e.independence_group}
              </text>
            </g>
          );
        })}
        {untrusted.map((e, i) => {
          const x = 90 + i * 180;
          const y = 290;
          const hot = picked === e.id;
          return (
            <g
              key={e.id}
              className="cursor-pointer"
              onMouseEnter={() => setPicked(e.id)}
              onMouseLeave={() => setPicked(null)}
            >
              <rect
                x={x - 70}
                y={y - 18}
                width="140"
                height="36"
                rx="10"
                fill={hot ? "#fff5f5" : "#ffffff"}
                stroke="#de3b2f"
                strokeWidth={hot ? 2 : 1.5}
                strokeDasharray="4 3"
              />
              <text x={x} y={y + 4} textAnchor="middle" fill="#de3b2f" fontSize="10">
                {e.source_type} · untrusted
              </text>
            </g>
          );
        })}
      </svg>
      {picked ? (
        <p className={cn("mt-2 text-[12px] text-[var(--dim)]")}>
          Tap a source to see how it links to the hypothesis. Green lines = supporting evidence.
        </p>
      ) : (
        <p className="mt-2 text-[12px] text-[var(--faint)]">Hover sources to highlight links</p>
      )}
    </div>
  );
}
