"use client";

import { useEffect, useState } from "react";
import { api, type OfficeSnapshot, type Room } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";
import { CityMap } from "@/components/city-map";

export default function HomePage() {
  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [office, setOffice] = useState<OfficeSnapshot | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.rooms(), api.office()])
      .then(([r, o]) => {
        setRooms(r.rooms);
        setOffice(o);
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "API unreachable"));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!rooms || !office) return <Loading label="Opening the campus" />;

  const live = rooms.filter((r) => r.scenario_id || ["review", "research", "ops"].includes(r.kind));

  return (
    <CityMap rooms={live} desks={office.desks} handoffs={office.handoffs} working={office.working} />
  );
}
