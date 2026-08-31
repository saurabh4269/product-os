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
  const spread = (count: number, start: number, end: number) => {
    if (count <= 1) return [cx];
    const step = (end - start) / (count - 1);
    return Array.from({ length: count }, (_, i) => start + i * step);
  };
  const xs = spread(trusted.length, 90, width - 90);
  const nodes = trusted.map((e, i) => ({ e, x: xs[i], y: 210 }));
  const ux = spread(untrusted.length, 90, width - 90);

  return (
    <div className="overflow-x-auto rounded-2xl border border-border bg-white p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto min-w-[320px] w-full" role="img" aria-label="Evidence graph">
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
          {hyp ? `${Math.round(hyp.confidence * 100)}%` : ""}
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
          const x = ux[i];
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
    </div>
  );
}
