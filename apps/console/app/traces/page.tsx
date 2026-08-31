"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loading } from "@/components/ui";

/** Traces merged into live rooms — old links land on home. */
export default function TracesRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);
  return <Loading label="Opening chat" />;
}
