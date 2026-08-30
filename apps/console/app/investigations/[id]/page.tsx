"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { segmentId } from "@/lib/route-id";
import { ErrorState, Loading } from "@/components/ui";

export default function InvestigationAsRoom() {
  const path = usePathname() || "";
  const router = useRouter();
  const invId = segmentId(path, "investigations");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!invId) return;
    let live = true;
    api
      .rooms()
      .then((r) => {
        if (!live) return;
        const match = r.rooms.find((room) => room.investigation_id === invId);
        if (!match) {
          setErr("That room isn’t open.");
          return;
        }
        router.replace(`/rooms/${match.id}`);
      })
      .catch((e) => {
        if (live) setErr(e instanceof Error ? e.message : "failed");
      });
    return () => {
      live = false;
    };
  }, [invId, router]);

  if (err) return <ErrorState message={err} />;
  return (
    <div className="p-6">
      <Loading label="Opening room" />
    </div>
  );
}
