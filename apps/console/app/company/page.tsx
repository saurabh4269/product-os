"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";

export default function CompanyPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.company>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .company()
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Opening the company" />;

  const shop = "/shop/index.html";
  const ads = "/shop/ads.html";

  return (
    <div className="page-pad">
      <p className="text-[13px] text-[var(--faint)]">The company this OS is running</p>
      <h1 className="mt-1 text-[26px] font-semibold tracking-tight sm:text-[32px]">{data.company.name}</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        {data.company.tagline}. {data.company.product}. Ads buy the shop. The campus is where the work about it lives.
      </p>
      <div className="mt-6 flex flex-wrap gap-2">
        <a href={shop} className="rounded-full bg-accent px-4 py-2 text-[14px] font-medium text-white">
          Open the shop
        </a>
        <a href={ads} className="rounded-full bg-[var(--elev)] px-4 py-2 text-[14px] font-medium">
          The ad
        </a>
        <Link href="/approvals" className="rounded-full bg-[var(--elev)] px-4 py-2 text-[14px] font-medium">
          {data.loop.pending} waiting
        </Link>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        <div className="rounded-[20px] border border-border bg-white p-5">
          <p className="text-[12px] text-[var(--faint)]">Investigations</p>
          <p className="mt-1 text-[22px] font-semibold">{data.loop.investigations}</p>
        </div>
        <div className="rounded-[20px] border border-border bg-white p-5">
          <p className="text-[12px] text-[var(--faint)]">Resolved</p>
          <p className="mt-1 text-[22px] font-semibold">{data.loop.resolved}</p>
        </div>
        <div className="rounded-[20px] border border-border bg-white p-5">
          <p className="text-[12px] text-[var(--faint)]">failOpen</p>
          <p className="mt-1 text-[22px] font-semibold">{String(data.loop.failOpen)}</p>
        </div>
      </div>

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">Ads</h2>
      <p className="mt-2 max-w-lg text-[14px] leading-6 text-[var(--dim)]">
        Spend stayed flat. If checkout slips, it is not because we bought more traffic.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {data.ads.map((a) => (
          <article key={a.id} className="rounded-[20px] border border-border bg-white p-5">
            <p className="text-[13px] text-[var(--faint)]">{a.id}</p>
            <p className="mt-1 text-[16px] font-medium">{a.name}</p>
            <p className="mt-2 text-[14px] text-[var(--dim)]">
              {a.clicks ?? "—"} clicks · ${Math.round(Number(a.cost ?? 0))} · {a.conversions ?? "—"} buys
            </p>
          </article>
        ))}
      </div>

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">What the shop is running</h2>
      <div className="mt-5 max-w-xl space-y-3">
        {Object.entries(data.flags).map(([k, v]) => (
          <div key={k} className="flex justify-between gap-6 border-b border-border py-2 text-[14px]">
            <span>{k}</span>
            <span className="text-[var(--dim)]">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
