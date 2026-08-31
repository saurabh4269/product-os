"use client";

import { useEffect, useState } from "react";

/** product-os-v2 word-stream for fresh agent lines. */
export function StreamBody({ text, live = false }: { text: string; live?: boolean }) {
  const [shown, setShown] = useState(live ? "" : text);

  useEffect(() => {
    if (!live) {
      setShown(text);
      return;
    }
    setShown("");
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) window.clearInterval(id);
    }, 14);
    return () => window.clearInterval(id);
  }, [text, live]);

  return <p className="max-w-[620px] text-[14px] leading-6 text-[var(--ink)]">{shown}</p>;
}
