"use client";

import { cn } from "@/lib/utils";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";

type BoxProps = {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  sub?: string;
  highlight?: boolean;
  dashed?: boolean;
  href?: string | null;
};

function Box({ id, x, y, w, h, label, sub, highlight, dashed, href }: BoxProps) {
  const inner = (
    <g id={id} className={highlight ? "diagram-hot" : undefined}>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={12}
        fill={highlight ? "#0071e3" : "#ffffff"}
        stroke={highlight ? "#0071e3" : "#d2d2d7"}
        strokeWidth={highlight ? 2 : 1}
        strokeDasharray={dashed ? "4 3" : undefined}
      />
      <text
        x={x + w / 2}
        y={y + (sub ? h / 2 - 4 : h / 2 + 5)}
        textAnchor="middle"
        fill={highlight ? "#ffffff" : "#1d1d1f"}
        fontSize={13}
        fontWeight={600}
      >
        {label}
      </text>
      {sub ? (
        <text x={x + w / 2} y={y + h / 2 + 14} textAnchor="middle" fill={highlight ? "#e8f2ff" : "#86868b"} fontSize={11}>
          {sub}
        </text>
      ) : null}
    </g>
  );
  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer">
        {inner}
      </a>
    );
  }
  return inner;
}

function Arrow({ x1, y1, x2, y2, label }: { x1: number; y1: number; x2: number; y2: number; label?: string }) {
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#86868b" strokeWidth={1.5} markerEnd="url(#wire-arrow)" />
      {label ? (
        <text x={midX} y={midY - 6} textAnchor="middle" fill="#86868b" fontSize={10}>
          {label}
        </text>
      ) : null}
    </g>
  );
}

/** Light SVG tenant wire — Product Y ↔ Connect ↔ Product OS ↔ outcomes. */
export function TenantWireDiagram({
  productName = "Product Y",
  deployUrl,
  repo,
  className,
}: {
  productName?: string;
  deployUrl?: string | null;
  repo?: string | null;
  className?: string;
}) {
  const stage = usePipelineHighlight();
  const hotIngest = stage === "signal" || stage === "investigate";
  const hotEng = stage === "evidence" || stage === "root_cause" || stage === "risk";
  const hotApprove = stage === "approve";
  const hotVerify = stage === "verify" || stage === "learn";

  return (
    <svg
      viewBox="0 0 920 280"
      className={cn("w-full max-w-4xl", className)}
      role="img"
      aria-label="Tenant wire diagram"
    >
      <defs>
        <marker id="wire-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#86868b" />
        </marker>
      </defs>
      <rect width="920" height="280" fill="#f5f5f7" rx="16" />

      <text x="24" y="28" fill="#86868b" fontSize={11} letterSpacing={2}>
        TENANT WIRE
      </text>

      <Box
        id="stage_signal"
        x={24}
        y={48}
        w={140}
        h={72}
        label={productName}
        sub={deployUrl ? "open product" : "tenant app"}
        href={deployUrl || undefined}
      />
      <Box id="tenant_sdk" x={24} y={136} w={140} h={56} label="Loop wire" sub="flags + ingest" highlight={hotIngest} />

      <Box id="connect" x={220} y={72} w={150} h={120} label="Connect" sub="token · repo · BQ" dashed />

      <Box id="stage_investigate" x={420} y={48} w={150} h={56} label="Ingest API" sub="push signals" highlight={hotIngest} />
      <Box id="stage_evidence" x={420} y={120} w={150} h={56} label="Loop engine" sub="rooms + agents" highlight={hotEng} />
      <Box id="stage_approve" x={420} y={192} w={150} h={56} label="Pipeline" sub="live board" highlight={hotApprove || hotVerify} />

      <Box id="bq" x={620} y={48} w={130} h={56} label="BigQuery" sub="pull facts" />
      <Box id="pr" x={620} y={120} w={130} h={56} label="GitHub PR" sub={repo || "on approve"} highlight={hotApprove} />
      <Box id="flags" x={620} y={192} w={130} h={56} label="Flags" sub="tenant reads" highlight={hotVerify} />
      <Box id="cal" x={780} y={120} w={110} h={56} label="Calendar" sub="hold + Meet" />

      <Arrow x1={164} y1={164} x2={220} y2={132} label="config" />
      <Arrow x1={164} y1={84} x2={420} y2={76} label="push" />
      <Arrow x1={370} y1={132} x2={420} y2={148} />
      <Arrow x1={570} y1={76} x2={620} y2={76} label="pull" />
      <Arrow x1={570} y1={148} x2={620} y2={148} />
      <Arrow x1={570} y1={220} x2={620} y2={220} />
      <Arrow x1={750} y1={148} x2={780} y2={148} />
      <Arrow x1={750} y1={220} x2={620} y2={220} label="read" />
    </svg>
  );
}
