"use client";

import { ConnectWorkspace } from "@/components/settings/connect-workspace";
import { SettingsChrome } from "@/components/settings/settings-chrome";

/** Tenant wire — OAuth callbacks land on /connect?workspace=…; must work in static export. */
export default function ConnectPage() {
  return (
    <div className="page-pad fade-in mx-auto max-w-container-max">
      <SettingsChrome active="connect" />
      <ConnectWorkspace />
    </div>
  );
}
