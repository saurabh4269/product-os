import { RoomView } from "@/components/room-view";

export function generateStaticParams() {
  return [{ id: "_" }];
}

export default function RoomPage() {
  return <RoomView />;
}
