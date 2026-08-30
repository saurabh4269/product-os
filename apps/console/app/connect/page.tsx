"use client";

import { useEffect, useState } from "react";
import { api, type Tenant } from "@/lib/api";
import { Button, ErrorState, Loading } from "@/components/ui";

const field =
  "mt-1 w-full rounded-xl border border-border bg-white px-3 py-2 text-[14px] text-foreground outline-none focus:border-accent";

export default function ConnectPage() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [flags, setFlags] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [product, setProduct] = useState("");
  const [repo, setRepo] = useState("");
  const [deploy, setDeploy] = useState("");
  const [token, setToken] = useState("");

  async function load() {
    const listed = await api.tenants();
    const first = listed.tenants[0];
    if (!first) return;
    const detail = await api.tenant(first.id);
    setTenant(detail.tenant);
    setFlags(detail.flags);
    setName(detail.tenant.name);
    setProduct(detail.tenant.product);
    setRepo(detail.tenant.repo);
    setDeploy(detail.tenant.deploy_url);
  }

  useEffect(() => {
    load().catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!tenant) return <Loading label="Opening connect" />;

  async function save() {
    if (!tenant) return;
    setBusy(true);
    setSaved(null);
    try {
      await api.upsertTenant({
        id: tenant.id,
        name,
        product,
        repo,
        deploy_url: deploy,
      });
      if (token.trim()) {
        const rotated = await api.rotateToken(tenant.id, token.trim());
        setTenant(rotated.tenant);
        setToken("");
        setSaved("Saved. The token is hashed here and will not be shown again.");
      } else {
        const detail = await api.tenant(tenant.id);
        setTenant(detail.tenant);
        setFlags(detail.flags);
        setSaved("Saved.");
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(false);
    }
  }

  const gate = tenant.repo
    ? `Approvals will open a pull request on ${tenant.repo}. Product OS will not merge it.`
    : "Approvals will only flip an OS flag until a git repo is set.";

  return (
    <div className="page-pad">
      <p className="text-[13px] text-[var(--faint)]">{tenant.id}</p>
      <h1 className="mt-1 text-[26px] font-semibold tracking-tight sm:text-[32px]">Connect</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Their app lives on their origin. This desk holds git, the deploy URL, and a hashed token so they can read flags
        and post voice. Mail and calendar skip until Workspace OAuth exists.
      </p>

      <form
        className="mt-10 max-w-xl space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <label className="block text-[13px] text-[var(--faint)]">
          Name
          <input className={field} value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Product
          <input className={field} value={product} onChange={(e) => setProduct(e.target.value)} autoComplete="off" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          GitHub repo
          <input
            className={field}
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="org/product-y"
            autoComplete="off"
          />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Deploy URL
          <input
            className={field}
            value={deploy}
            onChange={(e) => setDeploy(e.target.value)}
            placeholder="https://…"
            autoComplete="off"
          />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Rotate tenant token
          <input
            className={field}
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder={tenant.has_token ? "Leave blank to keep the current token" : "Set a token"}
            autoComplete="new-password"
          />
        </label>
        <p className="text-[13px] leading-5 text-[var(--dim)]">{gate}</p>
        <p className="text-[13px] text-[var(--faint)]">
          {tenant.has_token ? "Token is set" : "No tenant token"}
          {tenant.last_connector ? ` · ${tenant.last_connector}` : ""}
        </p>
        {tenant.last_pr_url ? (
          <p className="text-[14px]">
            Last pull request:{" "}
            <a href={tenant.last_pr_url} className="text-accent" target="_blank" rel="noreferrer">
              {tenant.last_pr_url}
            </a>
          </p>
        ) : null}
        {tenant.deploy_url ? (
          <p className="text-[14px]">
            Product:{" "}
            <a href={tenant.deploy_url} className="text-accent" target="_blank" rel="noreferrer">
              {tenant.deploy_url}
            </a>
          </p>
        ) : null}
        <Button type="submit" disabled={busy}>
          Save
        </Button>
        {saved ? <p className="text-[14px] text-[var(--dim)]">{saved}</p> : null}
      </form>

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">Flags they read</h2>
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
