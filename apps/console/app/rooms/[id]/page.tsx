import { Suspense } from "react";
import { RoomView } from "@/components/room-view";

export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function RoomPage() {
  return (
    <Suspense fallback={null}>
      <RoomView />
    </Suspense>
  );
}
