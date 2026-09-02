import { Suspense } from "react";
import { RoomView } from "@/components/room-view";

export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function RoomPage() {
  return (
    <Suspense fallback={<div className="page-pad text-[14px] text-[var(--dim)]">Loading room…</div>}>
      <RoomView />
    </Suspense>
  );
}
