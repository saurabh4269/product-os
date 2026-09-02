"use client";

import { ConnectWorkspace } from "@/components/settings/connect-workspace";
import { SettingsChrome } from "@/components/settings/settings-chrome";

export default function SettingsPage() {
  return (
    <div className="page-pad fade-in mx-auto max-w-container-max">
      <SettingsChrome active="connect" />
      <ConnectWorkspace />
    </div>
  );
}
