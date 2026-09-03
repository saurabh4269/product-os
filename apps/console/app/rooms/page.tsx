"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { api, tryGet, type OfficeSnapshot, type Room } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { LiveRoomsRail } from "@/components/live-rooms-rail";
import { ErrorState, Loading } from "@/components/ui";

export default function RoomsIndex() {
  const { tick } = useGlobalWs();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [office, setOffice] = useState<OfficeSnapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [roomsRes, officeRes] = await Promise.all([
          tryGet(() => api.rooms()),
          tryGet(() => api.office()),
        ]);
        if (cancelled) return;
        setRooms(roomsRes.data?.rooms ?? []);
        setOffice(officeRes.data ?? null);
        setErr(null);
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "API unreachable");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [tick]);

  if (loading) {
    return <Loading label="Loading rooms" />;
  }

  if (err) {
    return (
      <div className="page-pad">
        <ErrorState message={err} />
      </div>
    );
  }

  const desks = office?.desks ?? [];

  return (
    <div className="page-pad mx-auto max-w-5xl">
      <div className="mb-6">
        <Link href="/" className="text-[13px] font-medium text-accent hover:underline">
          ← Campus
        </Link>
        <h1 className="mt-2 text-[22px] font-semibold tracking-tight text-foreground">Rooms</h1>
        <p className="mt-1 text-[14px] text-[var(--dim)]">
          Open work chambers — walk in to see specialist handoffs and live tool embeds.
        </p>
      </div>
      <LiveRoomsRail rooms={rooms} desks={desks} />
    </div>
  );
}
