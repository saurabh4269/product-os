"use client";

import { useParams } from "next/navigation";
import { InvestigationRoom } from "@/components/investigation-room";

export default function InvestigationPage() {
  const params = useParams<{ id: string }>();
  return <InvestigationRoom initialId={params.id} />;
}
