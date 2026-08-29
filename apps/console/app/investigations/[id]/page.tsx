"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { RoomView } from "@/components/room-view";
import { Loading } from "@/components/ui";

export default function InvestigationAsRoom() {
  const [roomId, setRoomId] = useState<string | null>(null);

  useEffect(() => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    const invId = parts[parts.length - 1];
    api
      .rooms()
      .then((r) => {
        const match = r.rooms.find((room) => room.investigation_id === invId);
        setRoomId(match?.id ?? invId);
      })
      .catch(() => setRoomId(invId));
  }, []);

  if (!roomId) return <div className="p-6"><Loading label="Opening room" /></div>;
  return <RoomView initialId={roomId} />;
}
