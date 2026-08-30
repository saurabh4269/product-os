"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Loading } from "@/components/ui";

export default function RoomsIndex() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);
  return <Loading label="Opening rooms" />;
}
