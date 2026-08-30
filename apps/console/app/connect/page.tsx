"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";

export default function ConnectPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.tenants>> | null>(null);
  const [flags, setFlags] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .tenants()
      .then(async (listed) => {
        setData(listed);
        const first = listed.tenants[0];
        if (first) {
          const detail = await api.tenant(first.id);
          setFlags(detail.flags);
        }
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Opening connect" />;

  return (
    <div className="page-pad">
      <p className="text-[13px] text-[var(--faint)]">Company X · Product Y</p>
      <h1 className="mt-1 text-[26px] font-semibold tracking-tight sm:text-[32px]">Connect</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Product OS does not host their app. This page is the wire: git, deploy URL, token, flags they can read.
        Mail, calendar, and GitHub apply only when secrets exist — otherwise they skip, they do not pretend.
      </p>
      <div className="mt-10 max-w-xl space-y-4">
        {data.tenants.map((t) => (
          <article key={t.id} className="rounded-[20px] border border-border bg-white p-5">
            <p className="text-[13px] text-[var(--faint)]">{t.id}</p>
            <p className="mt-1 text-[18px] font-medium">{t.name}</p>
            <p className="mt-1 text-[14px] text-[var(--dim)]">{t.product}</p>
            <p className="mt-3 text-[14px]">{t.repo || "No git repo yet"}</p>
            <p className="text-[14px] text-[var(--dim)]">{t.deploy_url || "No deploy URL yet"}</p>
            <p className="mt-3 text-[13px] text-[var(--faint)]">
              {t.connected ? "Repo on file" : "Not connected"}
              {t.has_token ? " · token set" : " · no tenant token"}
            </p>
          </article>
        ))}
      </div>
      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">Flags they would read</h2>
      <div className="mt-5 max-w-xl space-y-3">
        {Object.entries(flags).length === 0 ? (
          <p className="text-[14px] text-[var(--dim)]">None written yet. An approve writes them.</p>
        ) : (
          Object.entries(flags).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-6 border-b border-border py-2 text-[14px]">
              <span>{k}</span>
              <span className="text-[var(--dim)]">{v}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
