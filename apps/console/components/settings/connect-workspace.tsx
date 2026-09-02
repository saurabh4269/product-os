"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, adminRememberEnabled, clearAdminToken, hasAdminToken, verifyAdminToken, type GoogleOAuth, type Tenant } from "@/lib/api";
import { Button, ErrorState, Loading } from "@/components/ui";
import { LiveIncidentPanel } from "@/components/live-incident-panel";
import { SignalSourcesDiagram } from "@/components/diagrams/signal-sources-diagram";
import { TenantWireDiagram } from "@/components/diagrams/tenant-wire-diagram";

const field =
  "field-input mt-1 w-full rounded-xl border border-border bg-white px-3 py-2 text-[14px] text-foreground outline-none transition-colors focus:border-accent focus:ring-2 focus:ring-accent/20";

type CloudRunService = { id: string; name: string; url: string; repo_hint?: string };
type VerifyCheck = { id: string; ok: boolean; label: string; detail?: string; room_id?: string };

const COVE_PRESET = {
  service: "cove",
  repo: "saurabh4269/cove",
  name: "Cove",
  product: "Cove",
  tenant_id: "cove",
};

export function ConnectWorkspace() {
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
  const [ga4Ready, setGa4Ready] = useState(false);
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
  const [services, setServices] = useState<CloudRunService[]>([]);
  const [servicesDetail, setServicesDetail] = useState("");
  const [pickService, setPickService] = useState("");
  const [wireRepo, setWireRepo] = useState("");
  const [wireName, setWireName] = useState("");
  const [wireProduct, setWireProduct] = useState("");
  const [wireTenantId, setWireTenantId] = useState("");
  const [wireProgress, setWireProgress] = useState<string | null>(null);
  const [onceToken, setOnceToken] = useState<string | null>(null);
  const [verifyChecks, setVerifyChecks] = useState<VerifyCheck[]>([]);
  const [verifyReady, setVerifyReady] = useState(false);
  const [verifyRoomId, setVerifyRoomId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [wireHint, setWireHint] = useState<string | null>(null);
  const [adminTokenInput, setAdminTokenInput] = useState("");
  const [adminOk, setAdminOk] = useState(false);
  const [rememberAdmin, setRememberAdmin] = useState(false);

  function applyTenantFields(detail: { tenant: Tenant; flags: Record<string, string> }) {
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
    if (!wireRepo) setWireRepo(detail.tenant.repo || "");
    if (!wireName) setWireName(detail.tenant.name || "");
    if (!wireProduct) setWireProduct(detail.tenant.product || "");
    if (!wireTenantId) setWireTenantId(detail.tenant.id || "");
  }

  async function load(selectedId?: string) {
    const listed = await api.tenants();
    setAllTenants(listed.tenants);
    const pick = selectedId || tenant?.id || listed.tenants[0]?.id;
    if (!pick) {
      setTenant(null);
    } else {
      const detail = await api.tenant(pick);
      applyTenantFields(detail);
    }
    setOauth(await api.oauth());
    setGa4Ready((await api.ga4Status()).ready);
    setTelephony(await api.telephony());
    setAdk(await api.adkStatus());
    try {
      const svc = await api.onboardServices();
      setServices(svc.services || []);
      setServicesDetail(svc.detail || svc.status);
      if (!pickService && svc.services?.length) {
        const cove = svc.services.find((s) => s.id === "cove");
        if (cove) {
          setPickService(cove.id);
          if (cove.repo_hint) setWireRepo(cove.repo_hint);
          if (cove.url) setDeploy(cove.url);
        }
      }
    } catch {
      setServicesDetail("Could not list Cloud Run services (admin token or IAM). Paste a service name below.");
    }
  }

  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const ws = q.get("workspace");
    const ga4 = q.get("ga4");
    if (ws === "ok") setSaved("Google Workspace connected. Drafts and calendar holds can run. Send stays off.");
    if (ws === "error") setErr(q.get("detail") || "Google authorization did not complete.");
    if (ga4 === "ok") setSaved("GA4 Admin authorized. Analytics export automation can run.");
    if (ga4 === "error") setErr(q.get("detail") || "GA4 authorization did not complete.");
    setAdminOk(hasAdminToken());
    setRememberAdmin(adminRememberEnabled());
    load()
      .catch((e) => {
        const msg = e instanceof Error ? e.message : "failed";
        if (msg.includes("401") || msg.includes("admin bearer")) {
          setErr(null);
        } else {
          setErr(msg);
        }
      })
      .finally(() => setReady(true));
  }, []);

  async function saveAdminToken() {
    if (!adminTokenInput.trim()) return;
    setBusy(true);
    try {
      const ok = await verifyAdminToken(adminTokenInput.trim(), rememberAdmin);
      setAdminOk(ok);
      if (ok) {
        setSaved(
          rememberAdmin
            ? "Admin token saved on this device. Wire, incidents, and approvals stay unlocked."
            : "Admin token saved for this tab. Check “Remember on this device” to keep it after closing the browser."
        );
        setErr(null);
        await load();
      } else {
        setSaved("Admin token rejected — check LOOP_ADMIN_TOKEN on Cloud Run.");
      }
    } finally {
      setBusy(false);
    }
  }

  function forgetAdminToken() {
    clearAdminToken();
    setAdminOk(false);
    setRememberAdmin(false);
    setAdminTokenInput("");
    setSaved("Admin token cleared from this browser.");
  }

  if (err && !ready) return <ErrorState message={err} />;
  if (!ready) return <Loading label="Opening connect" />;

  function applyCovePreset() {
    setPickService(COVE_PRESET.service);
    setWireRepo(COVE_PRESET.repo);
    setWireName(COVE_PRESET.name);
    setWireProduct(COVE_PRESET.product);
    setWireTenantId(COVE_PRESET.tenant_id);
    const hit = services.find((s) => s.id === COVE_PRESET.service);
    if (hit?.url) setDeploy(hit.url);
    setSaved("Cove preset loaded. Wire & verify next.");
  }

  async function wireAndVerify() {
    const service = pickService.trim();
    const r = wireRepo.trim();
    if (!service && !deploy.trim()) {
      setSaved("Pick a Cloud Run service or set a deploy URL in Advanced.");
      return;
    }
    if (!r) {
      setSaved("GitHub repo is required (org/name).");
      return;
    }
    setBusy(true);
    setSaved(null);
    setOnceToken(null);
    setWireHint(null);
    setVerifyChecks([]);
    setVerifyReady(false);
    setVerifyRoomId(null);
    setWireProgress("Creating tenant and minting token…");
    try {
      const onboarded = await api.onboardTenant({
        cloud_run_service: service,
        repo: r,
        tenant_id: wireTenantId.trim() || undefined,
        name: wireName.trim() || undefined,
        product: wireProduct.trim() || undefined,
        deploy_url: deploy.trim() || undefined,
        wire: Boolean(service),
      });
      if (onboarded.token) setOnceToken(onboarded.token);
      const wireStatus = onboarded.wire?.status || "";
      if (wireStatus === "skipped") {
        setWireHint(onboarded.wire?.hint || onboarded.wire?.detail || "Wire skipped — set LOOP_* on Product Y manually if needed.");
        if (onboarded.wire?.manual) setWireHint((h) => `${h || ""}\n${onboarded.wire?.manual}`);
      }
      setWireProgress(
        wireStatus === "applied"
          ? "Env pushed to Cloud Run. Verifying…"
          : wireStatus === "reused"
            ? "Already wired. Verifying…"
            : "Tenant saved. Verifying…"
      );
      const verified = await api.verifyTenant(onboarded.tenant_id);
      setVerifyChecks(verified.checks || []);
      setVerifyReady(Boolean(verified.ready || verified.ready_for_demo));
      setVerifyRoomId(verified.room_id || null);
      await load(onboarded.tenant_id);
      setWireProgress(null);
      setSaved(
        verified.ready || verified.ready_for_demo
          ? "Connected. Product OS can ingest signals and open rooms."
          : "Partial — check the checklist below."
      );
    } catch (e) {
      setWireProgress(null);
      setSaved(e instanceof Error ? e.message : "Wire failed");
    } finally {
      setBusy(false);
    }
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

  const gate = (tenant?.repo || wireRepo)
    ? `Approvals will open a pull request on ${tenant?.repo || wireRepo}. Product OS will not merge it.`
    : "Approvals will only flip an OS flag until a git repo is set.";

  return (
    <>
      {!adminOk ? (
        <section className="surface-lg mt-4 max-w-xl space-y-3 p-5">
          <p className="text-[14px] leading-6 text-[var(--dim)]">
            Hosted Product OS requires an admin token to wire tenants, approve fixes, and reset walkthroughs. Paste{" "}
            <code className="text-[13px]">LOOP_ADMIN_TOKEN</code> from Cloud Run.
          </p>
          <div className="flex flex-wrap gap-2">
            <input
              type="password"
              className={field}
              placeholder="Admin bearer token"
              value={adminTokenInput}
              onChange={(e) => setAdminTokenInput(e.target.value)}
            />
            <Button disabled={busy || !adminTokenInput.trim()} onClick={() => void saveAdminToken()}>
              Authorize
            </Button>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-[13px] text-[var(--dim)]">
            <input
              type="checkbox"
              className="size-4 rounded border-border accent-[#0071e3]"
              checked={rememberAdmin}
              onChange={(e) => setRememberAdmin(e.target.checked)}
            />
            Remember on this device
          </label>
        </section>
      ) : (
        <section className="surface-lg mt-4 max-w-xl space-y-2 p-5">
          <p className="text-[14px] text-[var(--dim)]">
            Admin authorized{rememberAdmin ? " · remembered on this device" : " · this tab only"}.
          </p>
          <button
            type="button"
            className="text-[13px] text-[var(--faint)] underline-offset-2 hover:text-foreground hover:underline"
            onClick={forgetAdminToken}
          >
            Forget admin token
          </button>
        </section>
      )}
      {tenant ? <p className="text-[13px] text-[var(--faint)]">{tenant.id}</p> : null}
      {allTenants.length > 1 ? (
        <label className="mt-2 block text-[13px] text-[var(--faint)]">
          Tenant
          <select
            className={field}
            value={tenant?.id || ""}
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
      <section className="surface-lg mt-6 max-w-xl space-y-5 p-5 sm:p-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">
          Wire product (GCP)
        </p>
        <p className="text-[14px] text-[var(--dim)]">
          Pick the Cloud Run service for Product Y and its GitHub repo. Product OS mints the tenant token and
          pushes <code className="text-[13px]">LOOP_*</code> env vars — no copy-paste.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" disabled={busy} onClick={applyCovePreset}>
            Start with Cove
          </Button>
        </div>
        <label className="block text-[13px] text-[var(--faint)]">
          Cloud Run service
          {services.length > 0 ? (
            <select
              className={field}
              value={pickService}
              onChange={(e) => {
                const id = e.target.value;
                setPickService(id);
                const hit = services.find((s) => s.id === id);
                if (hit?.repo_hint) setWireRepo(hit.repo_hint);
                if (hit?.url) setDeploy(hit.url);
                if (id && !wireTenantId) setWireTenantId(id);
                if (id && !wireName) setWireName(id.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()));
              }}
            >
              <option value="">Select…</option>
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.url ? ` · ${s.url.replace(/^https:\/\//, "")}` : ""}
                </option>
              ))}
            </select>
          ) : (
            <input
              className={field}
              value={pickService}
              onChange={(e) => setPickService(e.target.value)}
              placeholder="cove"
              autoComplete="off"
            />
          )}
        </label>
        {servicesDetail ? <p className="text-[12px] text-[var(--faint)]">{servicesDetail}</p> : null}
        <label className="block text-[13px] text-[var(--faint)]">
          GitHub repo
          <input
            className={field}
            value={wireRepo}
            onChange={(e) => setWireRepo(e.target.value)}
            placeholder="org/product-y"
            autoComplete="off"
          />
        </label>
        <label className="block text-[13px] text-[var(--faint)]">
          Display name
          <input className={field} value={wireName} onChange={(e) => setWireName(e.target.value)} autoComplete="off" />
        </label>
        <Button type="button" disabled={busy || (!pickService.trim() && !deploy.trim()) || !wireRepo.trim()} onClick={() => void wireAndVerify()}>
          Wire & verify
        </Button>
        {wireProgress ? <p className="text-[14px] text-[var(--dim)]">{wireProgress}</p> : null}
        {wireHint ? <p className="whitespace-pre-wrap text-[13px] text-[var(--faint)]">{wireHint}</p> : null}
        {onceToken ? (
          <p className="rounded-xl border border-border bg-[#fbfbfd] px-3 py-2 text-[13px] text-[var(--dim)]">
            Token minted once (already pushed if wire succeeded). Reveal:{" "}
            <code className="break-all text-[12px]">{onceToken}</code>
          </p>
        ) : null}
        {verifyChecks.length > 0 ? (
          <ul className="divide-y divide-border rounded-xl border border-border">
            {verifyChecks.map((c) => (
              <li key={c.id} className="flex items-start justify-between gap-4 px-3 py-2.5 text-[14px]">
                <span>
                  <span className={c.ok ? "text-[var(--dim)]" : "text-[var(--faint)]"}>{c.ok ? "✓" : "·"} </span>
                  {c.label}
                  {c.detail ? <span className="mt-0.5 block text-[12px] text-[var(--faint)]">{c.detail}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
        {verifyReady ? (
          <div className="flex flex-wrap gap-3 text-[14px]">
            {verifyRoomId ? (
              <Link href={`/rooms/${verifyRoomId}`} className="text-accent">
                Open verify room →
              </Link>
            ) : null}
            <Link href="/" className="text-accent">
              Open campus →
            </Link>
            {(tenant?.deploy_url || deploy) ? (
              <a href={tenant?.deploy_url || deploy} className="text-accent" target="_blank" rel="noreferrer">
                Open product →
              </a>
            ) : null}
          </div>
        ) : null}
        <p className="text-[13px] text-[var(--faint)]">{gate}</p>
        {saved ? <p className="text-[14px] text-[var(--dim)]">{saved}</p> : null}
      </section>

      {tenant ? (
        <LiveIncidentPanel tenantId={tenant.id} adminReady={adminOk} />
      ) : null}

      <section className="surface-lg mt-8 max-w-4xl p-4 sm:p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Tenant wire</p>
        <div className="mt-4 overflow-x-auto">
          <TenantWireDiagram productName={product || wireProduct || name || wireName} deployUrl={deploy} repo={repo || wireRepo} />
        </div>
      </section>

      <section className="surface-lg mt-8 max-w-4xl p-4 sm:p-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Signal sources</p>
        <div className="mt-4">
          <SignalSourcesDiagram />
        </div>
      </section>

      <section className="surface-lg mt-8 max-w-xl p-5 sm:p-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Google Workspace</p>
        {oauth?.connected ? (
          <p className="mt-4 text-[14px] text-[var(--dim)]">
            Connected{oauth.email ? ` · ${oauth.email}` : ""}
          </p>
        ) : oauth?.configured ? (
          <p className="mt-4 text-[14px]">
            <a href={oauth.authorize_url || "/api/oauth/google/start"} className="text-accent">
              Authorize
            </a>
          </p>
        ) : (
          <p className="mt-4 text-[14px] text-[var(--faint)]">Paste OAuth client in Advanced</p>
        )}
      </section>

      <button
        type="button"
        className="mt-8 text-[13px] text-accent"
        onClick={() => setShowAdvanced((v) => !v)}
      >
        {showAdvanced ? "Hide advanced" : "Advanced"}
      </button>

      {showAdvanced ? (
        <>
          {!tenant ? (
            <p className="mt-4 max-w-xl text-[14px] text-[var(--faint)]">
              Wire a product above first, or use the form after a tenant exists.
            </p>
          ) : (
            <form
              className="surface-lg mt-4 max-w-xl space-y-5 p-5 sm:p-6"
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
            </form>
          )}

          <section className="surface-lg mt-8 max-w-xl space-y-5 p-5 sm:p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Warehouse</p>
            <form
              className="space-y-5"
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
              <Button type="submit" disabled={busy || !tenant}>
                Save warehouse config
              </Button>
            </form>
          </section>

          <section className="surface-lg mt-8 max-w-xl p-5 sm:p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">GA4 Admin</p>
            {ga4Ready ? (
              <p className="mt-4 text-[14px] text-[var(--dim)]">Ready · run warehouse setup</p>
            ) : oauth?.configured ? (
              <p className="mt-4 text-[14px]">
                <a href="/api/oauth/ga4/start" className="text-accent">
                  Authorize
                </a>
              </p>
            ) : (
              <p className="mt-4 text-[14px] text-[var(--faint)]">Save OAuth client first</p>
            )}
          </section>

          <section className="surface-lg mt-8 max-w-xl p-5 sm:p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Phone</p>
            {telephony ? (
              <p className="mt-4 text-[14px] text-[var(--dim)]">
                Inbound {telephony.google_inbound ? "yes" : "no"} · Twilio {telephony.twilio ? "yes" : "no"} · Gemini{" "}
                {telephony.gemini ? "yes" : "no"} · {telephony.mode}
              </p>
            ) : null}
          </section>

          <section className="surface-lg mt-8 max-w-xl p-5 sm:p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">ADK</p>
            {adk ? (
              <div className="mt-4 space-y-2 text-[14px] text-[var(--dim)]">
                <p>
                  SDK {adk.adk_installed ? "yes" : "no"}
                  {adk.adk_worker_url ? (
                    <>
                      {" "}
                      ·{" "}
                      <a href={adk.adk_worker_url} className="text-accent" target="_blank" rel="noreferrer">
                        worker
                      </a>
                    </>
                  ) : null}
                </p>
                <p>
                  Fleet:{" "}
                  {adk.fleet && typeof adk.fleet.agents === "number"
                    ? `${adk.fleet.agents} agents · ${Array.isArray(adk.fleet.apps) ? adk.fleet.apps.length : 0} apps`
                    : "fallback"}
                </p>
                <p>
                  Code {adk.code_backend} · Antigravity {adk.antigravity.installed ? "yes" : "no"}
                </p>
              </div>
            ) : null}
          </section>

          <section className="surface-lg mt-8 max-w-xl p-5 sm:p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">OAuth client</p>
            {oauth?.redirect_uri ? (
              <p className="mt-3 text-[13px] text-[var(--faint)]">Redirect: {oauth.redirect_uri}</p>
            ) : null}
            {oauth && !oauth.configured ? (
              <form
                className="mt-6 space-y-5"
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
                <p className="text-[13px] text-[var(--faint)]">
                  <a href={oauth.console.overview} className="text-accent" target="_blank" rel="noreferrer">
                    Auth Platform
                  </a>
                  {" · "}
                  <a href={oauth.console.create_client} className="text-accent" target="_blank" rel="noreferrer">
                    Web client
                  </a>
                  {" · "}
                  <a href={oauth.console.audience} className="text-accent" target="_blank" rel="noreferrer">
                    Test users
                  </a>
                </p>
                <Button type="submit" disabled={busy || !clientId.trim() || !clientSecret.trim()}>
                  Save client
                </Button>
              </form>
            ) : null}
          </section>

          <section className="surface-lg mt-8 max-w-xl p-5 sm:p-6">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Flags</p>
            <div className="mt-4 divide-y divide-border">
              {Object.entries(flags).length === 0 ? null : (
                Object.entries(flags).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-6 py-2.5 text-[14px]">
                    <span>{k}</span>
                    <span className="text-[var(--dim)]">{v}</span>
                  </div>
                ))
              )}
            </div>
          </section>
        </>
      ) : null}
    </>
  );
}
