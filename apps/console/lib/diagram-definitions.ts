/** Mermaid sources for in-product architecture views (light theme applied at render). */

export const PRODUCT_FLOW = `
flowchart LR
  s1["1 · Signal"] --> s2["2 · Investigate"]
  s2 --> s3["3 · Diagnose"]
  s3 --> s4["4 · Decide"]
  s4 --> path{BUG vs FEATURE}
  path -->|Type A| code["Code + Test"]
  path -->|Type B| product["Product + Experiment"]
  code --> s5["5 · Risk"]
  product --> s5
  s5 --> hitl{HIGH HITL?}
  hitl -->|yes| s6["6 · Approve"]
  hitl -->|auto| s7["7 · Verify"]
  s6 --> ship[PR on Product Y]
  ship --> s7
  s7 --> learn[Lesson → Memory]
  oauth{Workspace OAuth?} --> draft[Gmail draft]
  deny_send["✕ send / merge / deploy"]
  security["Security / Gateway"] --> deny{Exfil DENY?}
  deny -->|yes| reviews[Reviews column]
`;

export const FIVE_PLANES = `
flowchart TB
  subgraph tenant_y [Product Y — tenant origin]
    COVE[Cove storefront]
    WIRE[Loop wire · flags client]
    COVE --> WIRE
  end

  subgraph signal_plane [Signal plane]
    GA4[GA4 / Ads / PostHog]
    LOGS[Cloud Logging]
    CRM[Voice / Reviews]
    GA4 --> BQ[(BigQuery facts)]
    LOGS --> BQ
    CRM --> BQ
    WIRE -->|push ingest| INGEST[Ingest API]
  end

  subgraph agent_plane [Agent plane — ADK 2]
    stage_signal[Signal]
    stage_investigate[Investigate]
    fanout[Specialists fan-out]
    join[Evidence join]
    stage_root_cause[Root cause]
    path{BUG vs FEATURE}
    stage_code[Code + Test]
    stage_product[Product]
    stage_risk[Risk]
    hitl_gate{HIGH HITL}
    stage_approve[Approve]
    stage_verify[Verify]
    stage_learn[Learn]
    stage_signal --> stage_investigate --> fanout --> join --> stage_root_cause --> path
    path -->|A| stage_code --> stage_risk
    path -->|B| stage_product --> stage_risk
    stage_risk --> hitl_gate
    hitl_gate -->|human| stage_approve
    hitl_gate -->|LOW/MED| stage_verify
    stage_approve --> stage_verify --> stage_learn
  end

  subgraph hybrid [Hybrid engine]
    LOOP_HOST[Cloud Run loop]
    ADK_HOST[Cloud Run loop-adk optional]
    LOOP_HOST -.->|when creds| ADK_HOST
  end

  subgraph security_plane [Security plane]
    ID[Agent Identity]
    GW[Gateway]
    MA[Model Armor]
    ID --> GW --> MA
    GW --> deny{Exfil request?}
    deny -->|DENY| reviews[Reviews — blocked]
  end

  subgraph tools_plane [Tool plane]
    GH[GitHub PR]
    WS[Workspace MCP]
    FLAG[Flags / CI]
  end

  subgraph memory_plane [Memory / control]
    RT[Cloud Run]
    MB[(Memory Bank)]
    REG[Registry]
  end

  BQ --> stage_signal
  INGEST --> stage_signal
  stage_learn --> MB
  MB --> stage_signal
  GW --> stage_code
  stage_code --> GH
  stage_product --> WS
  stage_risk --> FLAG
  RT --> REG
  LOOP_HOST --> stage_investigate
`;

export const SYSTEM_HUB = `
flowchart TB
  YOU[You · operator] --> CONSOLE[Console UI]
  CONSOLE -->|REST| LOOP[Cloud Run loop]
  CONSOLE <-->|WebSocket /ws| LOOP
  LOOP --> ENG[LoopEngine]
  ENG --> AGENTS[Agent fleet]
  AGENTS -->|agent_callback| LOOP
  LOOP -.->|optional| ADK[loop-adk worker]
`;

export const INVESTIGATION_FANOUT = `
flowchart TB
  INV[Investigator] --> A[Analytics]
  INV --> L[Logs]
  INV --> D[Deploy]
  INV --> DB[Database]
  INV --> V[Customer voice]
  INV --> C[Code context]
  A --> JOIN[JoinNode]
  L --> JOIN
  D --> JOIN
  DB --> JOIN
  V --> JOIN
  C --> JOIN
  JOIN --> EV[Evidence agent]
`;

export const SIGNAL_SOURCES = `
flowchart TB
  subgraph push [Push — tenant initiates]
    P1[POST /api/t/id/signals]
    P2[POST /api/t/id/voice]
    P3[Cove checkout hang]
    P1 --> HUB[Product OS ingest]
    P2 --> HUB
    P3 --> HUB
  end

  subgraph pull [Pull — warehouse]
    R1[GA4 → BigQuery export]
    R2[loop_raw / loop_metrics]
    R3[Signal agent scheduled detect]
    R1 --> BQ[(BigQuery facts)]
    R2 --> BQ
    BQ --> R3 --> HUB
  end

  subgraph live [Live UI]
    CB[agent_callback] --> WS[WebSocket /ws]
    WS --> UI[Pipeline + rooms]
  end

  HUB --> SIG[Signal → investigate]
`;

export const HITL_GATES = `
flowchart LR
  RISK[Risk agent] --> H1{HIGH approve?}
  H1 -->|yes| YOU[You · modal]
  YOU --> PR[GitHub PR]
  H1 -->|no| AUTO[Auto path]
  OAUTH{Workspace OAuth?} --> DRAFT[Gmail draft]
  DENY1["✕ send_gmail"]
  DENY2["✕ merge PR"]
  DENY3["✕ tenant deploy"]
  GW[Gateway] --> EX{Exfil?}
  EX -->|DENY| BLOCK[Reviews]
`;

/** Append mermaid classDefs for highlighted nodes. */
export function withHighlight(source: string, stage: string | null, nodeIds: string[]): string {
  if (!stage || !nodeIds.length) return source;
  const classes = nodeIds.map((id) => `class ${id} highlight`);
  return `${source}\nclassDef highlight fill:#0071e3,color:#fff,stroke:#0071e3\n${classes.join("\n")}\n`;
}
