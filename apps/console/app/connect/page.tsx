"use client";

import { useEffect, useState } from "react";
import { api, type GoogleOAuth, type Tenant } from "@/lib/api";
import { Button, ErrorState, Loading } from "@/components/ui";

const field =
  "mt-1 w-full rounded-xl border border-border bg-white px-3 py-2 text-[14px] text-foreground outline-none focus:border-accent";

export default function ConnectPage() {
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [flags, setFlags] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [name, setName] = useState("");
  const [product, setProduct] = useState("");
  const [repo, setRepo] = useState("");
  const [deploy, setDeploy] = useState("");
  const [token, setToken] = useState("");
  const [flagNames, setFlagNames] = useState("");
  const [codePaths, setCodePaths] = useState("");
  const [testCommand, setTestCommand] = useState("");
  const [bqProject, setBqProject] = useState("");
  const [bqRaw, setBqRaw] = useState("");
  const [bqMetrics, setBqMetrics] = useState("");
  const [ga4Property, setGa4Property] = useState("");
  const [ga4Dataset, setGa4Dataset] = useState("");
  const [adsDataset, setAdsDataset] = useState("");
  const [adsCustomer, setAdsCustomer] = useState("");
  const [warehouseMode, setWarehouseMode] = useState("auto");
  const [primaryMetric, setPrimaryMetric] = useState("purchase_conversion");
  const [funnelEvents, setFunnelEvents] = useState("");
  const [oauth, setOauth] = useState<GoogleOAuth | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [telephony, setTelephony] = useState<{
    twilio: boolean;
    gemini: boolean;
    google_inbound?: boolean;
    mode: string;
    detail: string;
  } | null>(null);
  const [adk, setAdk] = useState<Awaited<ReturnType<typeof api.adkStatus>> | null>(null);

  const [allTenants, setAllTenants] = useState<Tenant[]>([]);

  async function load(selectedId?: string) {
    const listed = await api.tenants();
    setAllTenants(listed.tenants);
    const pick = selectedId || tenant?.id || listed.tenants[0]?.id;
    if (!pick) {
      setTenant(null);
      return;
    }
    const detail = await api.tenant(pick);
    setTenant(detail.tenant);
    setFlags(detail.flags);
    setName(detail.tenant.name);
    setProduct(detail.tenant.product);
    setRepo(detail.tenant.repo);
    setDeploy(detail.tenant.deploy_url);
    setFlagNames((detail.tenant.flag_names ?? []).join(", "));
    setCodePaths((detail.tenant.code_paths ?? []).join(", "));
    setTestCommand(detail.tenant.test_command ?? "");
    setBqProject(detail.tenant.bq_project ?? "");
    setBqRaw(detail.tenant.bq_raw_dataset ?? "");
    setBqMetrics(detail.tenant.bq_metrics_dataset ?? "");
    setGa4Property(detail.tenant.ga4_property_id ?? "");
    setGa4Dataset(detail.tenant.ga4_dataset ?? "");
    setAdsDataset(detail.tenant.ads_dataset ?? "");
    setAdsCustomer(detail.tenant.ads_customer_id ?? "");
    setWarehouseMode(detail.tenant.warehouse_mode ?? "auto");
    setPrimaryMetric(detail.tenant.primary_metric ?? "purchase_conversion");
    setFunnelEvents((detail.tenant.funnel_events ?? []).join(", "));
    setOauth(await api.oauth());
    setTelephony(await api.telephony());
    setAdk(await api.adkStatus());
  }

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const ws = q.get("workspace");
    if (ws === "ok") setSaved("Google Workspace connected. Drafts and calendar holds can run. Send stays off.");
    if (ws === "error") setErr(q.get("detail") || "Google authorization did not complete.");
    load()
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"))
      .finally(() => setReady(true));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!ready) return <Loading label="Opening connect" />;
  if (!tenant) {
    return (
      <div className="page-pad">
        <h1 className="text-[26px] font-semibold tracking-tight">Connect</h1>
        <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
          No tenant is registered yet. Seed one, then come back.
        </p>
      </div>
    );
  }

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
        flag_names: flagNames
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        code_paths: codePaths
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        test_command: testCommand.trim(),
        bq_project: bqProject.trim(),
        bq_raw_dataset: bqRaw.trim(),
        bq_metrics_dataset: bqMetrics.trim(),
        ga4_property_id: ga4Property.trim(),
        ga4_dataset: ga4Dataset.trim(),
        ads_dataset: adsDataset.trim(),
        ads_customer_id: adsCustomer.trim(),
        warehouse_mode: warehouseMode.trim() || "auto",
        primary_metric: primaryMetric.trim() || "purchase_conversion",
        funnel_events: funnelEvents
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
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

  async function saveGoogle() {
    setBusy(true);
    setSaved(null);
    try {
      const next = await api.saveGoogleClient(clientId.trim(), clientSecret.trim());
      setOauth(next);
      setClientId("");
      setClientSecret("");
      setSaved("OAuth client saved. Authorize Gmail and Calendar next.");
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
      {allTenants.length > 1 ? (
        <label className="mt-2 block text-[13px] text-[var(--faint)]">
          Tenant
          <select
            className={field}
            value={tenant.id}
            onChange={(e) => {
              void load(e.target.value);
            }}
          >
            {allTenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.id})
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <h1 className="mt-1 text-[26px] font-semibold tracking-tight sm:text-[32px]">Connect</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Their app lives on their origin. This desk holds git, the deploy URL, and a hashed token so they can read flags
        and post voice. Gmail drafts and calendar holds need a one-time Google consent. Send stays off.
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
          Feature flags (comma-separated names)
          <input
            className={field}
            value={flagNames}
            onChange={(e) => setFlagNames(e.target.value)}
            placeholder="new_checkout_flow, pay_sdk_4_3"
            autoComplete="off"
          />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Code paths for fixes (comma-separated)
          <input
            className={field}
            value={codePaths}
            onChange={(e) => setCodePaths(e.target.value)}
            placeholder="app/checkout.rb, lib/payments.ts"
            autoComplete="off"
          />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Test command
          <input
            className={field}
            value={testCommand}
            onChange={(e) => setTestCommand(e.target.value)}
            placeholder="npm test -- --run"
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
          {tenant.last_ingest_at ? ` · last ingest ${tenant.last_ingest_at.slice(0, 16).replace("T", " ")}` : ""}
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

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">Warehouse (GA4 · Ads · BigQuery)</h2>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Product OS reads facts from BigQuery — not your app. Link a GA4 property export, optional Ads transfer, and
        loop_raw for synthetic or log sinks. Agents use these datasets for detect, evidence, and verify.
      </p>
      <form
        className="mt-6 max-w-xl space-y-5"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <label className="block text-[13px] text-[var(--faint)]">
          Mode
          <select className={field} value={warehouseMode} onChange={(e) => setWarehouseMode(e.target.value)}>
            <option value="auto">auto (BQ when datasets set)</option>
            <option value="file">file (fixtures only)</option>
            <option value="bq_raw">bq_raw (loop_raw tables)</option>
            <option value="ga4">ga4 (analytics_* export)</option>
          </select>
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          BQ project
          <input className={field} value={bqProject} onChange={(e) => setBqProject(e.target.value)} placeholder="mystical-timing-442601-q8" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Raw dataset (loop_raw)
          <input className={field} value={bqRaw} onChange={(e) => setBqRaw(e.target.value)} placeholder="loop_raw" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Metrics dataset
          <input className={field} value={bqMetrics} onChange={(e) => setBqMetrics(e.target.value)} placeholder="loop_metrics" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          GA4 property ID
          <input className={field} value={ga4Property} onChange={(e) => setGa4Property(e.target.value)} placeholder="123456789" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          GA4 BQ dataset (analytics_*)
          <input className={field} value={ga4Dataset} onChange={(e) => setGa4Dataset(e.target.value)} placeholder="analytics_123456789" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Ads dataset
          <input className={field} value={adsDataset} onChange={(e) => setAdsDataset(e.target.value)} placeholder="loop_raw or google_ads_transfer" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Ads customer ID
          <input className={field} value={adsCustomer} onChange={(e) => setAdsCustomer(e.target.value)} placeholder="1234567890" />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Primary metric
          <input className={field} value={primaryMetric} onChange={(e) => setPrimaryMetric(e.target.value)} />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Funnel events (comma-separated)
          <input
            className={field}
            value={funnelEvents}
            onChange={(e) => setFunnelEvents(e.target.value)}
            placeholder="page_view, view_item, begin_checkout, add_payment_info, purchase"
          />
        </label>
        <Button type="submit" disabled={busy}>
          Save warehouse config
        </Button>
      </form>

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">Phone calls</h2>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Google Telephony / CX Phone Gateway is inbound-only (no Google outbound PSTN). Optional Twilio free trial for
        dial-out + Gemini for dialogue; otherwise research runs simulated and still emits structured evidence. Set{" "}
        <code className="text-[13px]">LOOP_GTP_PHONE_NUMBER</code> and/or{" "}
        <code className="text-[13px]">TWILIO_*</code> + <code className="text-[13px]">GOOGLE_API_KEY</code> on Cloud Run{" "}
        <code className="text-[13px]">loop</code>.
      </p>
      {telephony ? (
        <p className="mt-4 text-[14px] text-[var(--dim)]">
          Google inbound {telephony.google_inbound ? "ready" : "not set"} · Twilio outbound{" "}
          {telephony.twilio ? "ready" : "not set"} · Gemini {telephony.gemini ? "ready" : "not set"} · mode{" "}
          {telephony.mode} · {telephony.detail}
        </p>
      ) : null}

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">ADK &amp; code agent</h2>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        ADK 2 fleet runs on an optional <code className="text-[13px]">loop-adk</code> worker. Main{" "}
        <code className="text-[13px]">loop</code> keeps the deterministic engine as fallback. Code-fix jobs: clone →
        test → PR; Antigravity is an optional preview editor behind{" "}
        <code className="text-[13px]">LOOP_CODE_BACKEND</code>.
      </p>
      {adk ? (
        <div className="mt-4 max-w-xl space-y-2 text-[14px] text-[var(--dim)]">
          <p>
            ADK SDK on this service:{" "}
            <span className="font-medium text-foreground">{adk.adk_installed ? "yes" : "no (main host)"}</span>
            {adk.adk_worker_url ? (
              <>
                {" "}
                · worker{" "}
                <a href={adk.adk_worker_url} className="text-accent" target="_blank" rel="noreferrer">
                  {adk.adk_worker_url.replace(/^https:\/\//, "")}
                </a>
              </>
            ) : (
              " · no worker URL (deploy loop-adk)"
            )}
          </p>
          <p>
            Fleet:{" "}
            {adk.fleet && typeof adk.fleet.agents === "number"
              ? `${adk.fleet.agents} agents · ${Array.isArray(adk.fleet.apps) ? adk.fleet.apps.length : 0} apps · workflow tools ${String(adk.fleet.workflow_tools ?? 0)}`
              : "deterministic fallback on main service"}
          </p>
          <p>
            Antigravity (preview): {adk.antigravity.installed ? "installed" : "not on slim host"} · code backend{" "}
            <code className="text-[13px]">{adk.code_backend}</code>
          </p>
        </div>
      ) : null}

      <h2 className="mt-12 text-[20px] font-semibold tracking-tight">Google Workspace</h2>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Coordination uses Calendar (list / free-busy / suggest / create + Meet) and Gmail drafts for review asks —
        HITL in the real workflow, not only an Approvals button. Send stays denied. Create a Web client in Google Auth
        Platform, paste it here, then authorize.
      </p>
      {oauth?.connected ? (
        <p className="mt-4 text-[14px] text-[var(--dim)]">
          Connected{oauth.email ? ` as ${oauth.email}` : ""}. Calendar + Gmail draft ready. Send stays off. Never
          auto-merges.
        </p>
      ) : oauth?.configured ? (
        <p className="mt-4 text-[14px]">
          Client saved.{" "}
          <a href={oauth.authorize_url || "/api/oauth/google/start"} className="text-accent">
            Authorize Gmail and Calendar
          </a>{" "}
          with the Google account you added as a test user.
        </p>
      ) : (
        <p className="mt-4 text-[14px] text-[var(--dim)]">
          OAuth client not saved yet — paste ID and secret below first. Authorizing before that sends you to a Google
          deny page.
        </p>
      )}
      {oauth?.redirect_uri ? (
        <p className="mt-3 max-w-lg text-[13px] leading-5 text-[var(--faint)]">
          Redirect URI to add on the client: {oauth.redirect_uri}
        </p>
      ) : null}
      {oauth && !oauth.configured ? (
        <form
          className="mt-6 max-w-xl space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            void saveGoogle();
          }}
        >
          <label className="block text-[13px] text-[var(--faint)]">
            OAuth client ID
            <input className={field} value={clientId} onChange={(e) => setClientId(e.target.value)} autoComplete="off" />
          </label>
          <label className="block text-[13px] text-[var(--faint)]">
            OAuth client secret
            <input
              className={field}
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="Never shown again"
              autoComplete="new-password"
            />
          </label>
          <p className="text-[13px] leading-5 text-[var(--dim)]">
            <a href={oauth.console.overview} className="text-accent" target="_blank" rel="noreferrer">
              Open Google Auth Platform
            </a>
            {" · "}
            <a href={oauth.console.create_client} className="text-accent" target="_blank" rel="noreferrer">
              Create a Web client
            </a>
            {" · "}
            add yourself under{" "}
            <a href={oauth.console.audience} className="text-accent" target="_blank" rel="noreferrer">
              Audience
            </a>{" "}
            as a test user.
          </p>
          <Button type="submit" disabled={busy || !clientId.trim() || !clientSecret.trim()}>
            Save client
          </Button>
        </form>
      ) : null}

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
