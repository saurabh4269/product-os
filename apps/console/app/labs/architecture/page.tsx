import { Suspense } from "react";
import ArchitecturePage from "./architecture-content";

export default function Page() {
  return (
    <Suspense fallback={<div className="page-pad text-[14px] text-[var(--dim)]">Loading architecture…</div>}>
      <ArchitecturePage />
    </Suspense>
  );
}
