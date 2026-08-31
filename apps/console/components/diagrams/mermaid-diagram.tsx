"use client";

import { useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/utils";

const THEME = {
  theme: "base" as const,
  themeVariables: {
    primaryColor: "#eef2ee",
    primaryTextColor: "#1d1d1f",
    primaryBorderColor: "#d2d2d7",
    lineColor: "#86868b",
    secondaryColor: "#f5f5f7",
    tertiaryColor: "#ffffff",
    fontFamily: "Inter, system-ui, sans-serif",
    fontSize: "13px",
  },
};

export function MermaidDiagram({
  source,
  className,
  title,
}: {
  source: string;
  className?: string;
  title?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const hostRef = useRef<HTMLDivElement>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let dead = false;
    const host = hostRef.current;
    if (!host) return;

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, securityLevel: "strict", ...THEME });
        const { svg } = await mermaid.render(`mmd-${uid}-${Date.now()}`, source.trim());
        if (dead || !hostRef.current) return;
        hostRef.current.innerHTML = svg;
        setErr(null);
      } catch (e) {
        if (!dead) setErr(e instanceof Error ? e.message : "Diagram failed");
      }
    }

    void render();
    return () => {
      dead = true;
    };
  }, [source, uid]);

  if (err) {
    return (
      <pre className={cn("overflow-x-auto rounded-2xl border border-border bg-white p-4 text-[11px]", className)}>
        {source.trim()}
      </pre>
    );
  }

  return (
    <figure className={cn("rounded-2xl border border-border bg-white p-4", className)}>
      {title ? <figcaption className="mb-3 text-[13px] font-medium text-[var(--faint)]">{title}</figcaption> : null}
      <div ref={hostRef} className="mermaid-host overflow-x-auto [&_svg]:mx-auto [&_svg]:max-w-full" />
    </figure>
  );
}
