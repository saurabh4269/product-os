#!/usr/bin/env python3
"""Create GA4 property + web stream + BigQuery link; push IDs to Cove + Loop tenant."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _ga4_adc_paths() -> list[Path]:
    paths = [Path.home() / ".config/gcloud/application_default_credentials.json"]
    project = __import__("os").environ.get("GOOGLE_CLOUD_PROJECT", "mystical-timing-442601-q8")
    bucket = __import__("os").environ.get("LOOP_BUNDLE_BUCKET", f"{project}-loop-host")
    cache = Path.home() / ".config/gcloud/ga4_adc.json"
    if not cache.is_file():
        try:
            raw = subprocess.check_output(
                ["gcloud", "storage", "cat", f"gs://{bucket}/ga4_adc.json"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(raw)
        except (subprocess.CalledProcessError, OSError):
            pass
    if cache.is_file():
        paths.insert(0, cache)
    return paths


def token() -> str:
    import google.auth.transport.requests
    import google.oauth2.credentials

    for adc in _ga4_adc_paths():
        if not adc.is_file():
            continue
        try:
            data = json.loads(adc.read_text())
            if not data.get("refresh_token"):
                continue
            creds = google.oauth2.credentials.Credentials.from_authorized_user_info(
                data,
                scopes=[
                    "https://www.googleapis.com/auth/analytics.edit",
                    "https://www.googleapis.com/auth/cloud-platform",
                ],
            )
            creds.refresh(google.auth.transport.requests.Request())
            if creds.token:
                return creds.token
        except Exception:
            continue
    try:
        import google.auth

        creds, _ = google.auth.default(
            scopes=[
                "https://www.googleapis.com/auth/analytics.edit",
                "https://www.googleapis.com/auth/cloud-platform",
            ]
        )
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token or ""
    except Exception:
        pass
    out = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    return out


def api(method: str, url: str, body: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500]
        raise RuntimeError(f"{method} {url} → {exc.code}: {detail}") from exc


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--cove-url", required=True)
    p.add_argument("--tenant-id", default="acme")
    p.add_argument("--loop-url", required=True)
    p.add_argument("--admin-token", default="")
    p.add_argument("--display-name", default="Cove")
    args = p.parse_args()

    summaries = api("GET", "https://analyticsadmin.googleapis.com/v1beta/accountSummaries?pageSize=20")
    accounts = summaries.get("accountSummaries") or []
    if not accounts:
        print("setup-ga4: no Analytics accounts visible — run ./scripts/setup-ga4-auth.sh", file=sys.stderr)
        return 1
    account = accounts[0]["account"]
    account_id = account.split("/")[-1]

    # Reuse existing Cove property if present
    props = api("GET", f"https://analyticsadmin.googleapis.com/v1beta/properties?filter=parent:accounts/{account_id}")
    prop = None
    for row in props.get("properties") or []:
        if args.display_name.lower() in (row.get("displayName") or "").lower():
            prop = row
            break
    if not prop:
        prop = api(
            "POST",
            "https://analyticsadmin.googleapis.com/v1beta/properties",
            {
                "parent": f"accounts/{account_id}",
                "displayName": args.display_name,
                "timeZone": "America/Los_Angeles",
                "currencyCode": "USD",
                "industryCategory": "SHOPPING",
            },
        )
    prop_name = prop["name"]
    prop_id = prop_name.split("/")[-1]
    ga4_dataset = f"analytics_{prop_id}"
    print(f"setup-ga4: property {prop_name} ({prop.get('displayName')})")

    streams = api("GET", f"https://analyticsadmin.googleapis.com/v1beta/{prop_name}/dataStreams")
    stream = None
    for row in streams.get("dataStreams") or []:
        if row.get("type") == "WEB_DATA_STREAM":
            stream = row
            break
    if not stream:
        stream = api(
            "POST",
            f"https://analyticsadmin.googleapis.com/v1beta/{prop_name}/dataStreams",
            {
                "type": "WEB_DATA_STREAM",
                "displayName": "Cove web",
                "webStreamData": {"defaultUri": args.cove_url.rstrip("/")},
            },
        )
    measurement_id = (stream.get("webStreamData") or {}).get("measurementId") or ""
    if not measurement_id:
        print("setup-ga4: web stream has no measurementId yet", file=sys.stderr)
        return 1
    print(f"setup-ga4: measurement ID {measurement_id}")

    bq_base = f"https://analyticsadmin.googleapis.com/v1alpha/{prop_name}/bigQueryLinks"
    try:
        links = api("GET", bq_base)
        linked = any(
            args.project in (l.get("project") or "")
            for l in links.get("bigQueryLinks") or links.get("bigqueryLinks") or []
        )
    except RuntimeError as exc:
        if "404" not in str(exc):
            raise
        linked = False
    if not linked:
        api(
            "POST",
            bq_base,
            {
                "project": f"projects/{args.project}",
                "datasetLocation": "US",
                "dailyExportEnabled": True,
                "streamingExportEnabled": True,
                "freshDailyExportEnabled": True,
            },
        )
        print(f"setup-ga4: BigQuery daily export → {args.project}.{ga4_dataset}")

    # Cove Cloud Run
    subprocess.run(
        [
            "gcloud",
            "run",
            "services",
            "update",
            "cove",
            "--project",
            args.project,
            "--region",
            "us-central1",
            "--update-env-vars",
            f"NEXT_PUBLIC_GA_MEASUREMENT_ID={measurement_id}",
            "--quiet",
        ],
        check=True,
    )
    print(f"setup-ga4: Cove env NEXT_PUBLIC_GA_MEASUREMENT_ID={measurement_id}")

    if args.admin_token:
        body = {
            "id": args.tenant_id,
            "name": "Cove",
            "product": "Cove",
            "repo": "saurabh4269/cove",
            "deploy_url": args.cove_url,
            "ga4_property_id": prop_id,
            "ga4_dataset": ga4_dataset,
            "warehouse_mode": "auto",
            "bq_project": args.project,
            "bq_raw_dataset": "loop_raw",
            "bq_metrics_dataset": "loop_metrics",
        }
        req = urllib.request.Request(
            f"{args.loop_url.rstrip('/')}/api/tenants",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {args.admin_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30):
            pass
        print(f"setup-ga4: Loop tenant {args.tenant_id} ga4_dataset={ga4_dataset}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        if "ACCESS_TOKEN_SCOPE_INSUFFICIENT" in str(exc) or "403" in str(exc):
            print(f"setup-ga4: {exc}", file=sys.stderr)
            print("Run once: ./scripts/setup-ga4-auth.sh", file=sys.stderr)
            raise SystemExit(1) from exc
        raise
