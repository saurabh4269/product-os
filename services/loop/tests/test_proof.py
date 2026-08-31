from __future__ import annotations

from loop.proof import github_pr_proof, homepage_proofs, warehouse_proof
from loop.tenant import Tenant, hash_token


def test_warehouse_proof_file_fallback(engine):
    engine.seed_world()
    tenants = engine.store.list_tenants()
    tenant = tenants[0] if tenants else None
    if tenant:
        tenant.warehouse_mode = "file"
        tenant.bq_raw_dataset = ""
        tenant.ga4_dataset = ""
        engine.store.put_tenant(tenant)
    out = warehouse_proof(engine, tenant, metric="purchase_conversion")
    assert out["kind"] in {"warehouse", "ga4"}
    assert out["source"] == "file_warehouse"
    assert out.get("live") is False
    assert "rows" in out
    assert out["columns"]


def test_warehouse_proof_prefers_live_bq(engine, monkeypatch):
    tenant = Tenant(
        id="acme",
        name="Cove",
        product="Cove",
        repo="saurabh4269/cove",
        warehouse_mode="auto",
        bq_project="proj",
        bq_raw_dataset="loop_raw",
        bq_metrics_dataset="loop_metrics",
        ga4_dataset="analytics_1",
        ga4_property_id="1",
        connected=True,
        token_hash=hash_token("x"),
    )
    engine.store.put_tenant(tenant)

    def fake_probe(t, start, end, include_recovery=True, prefer=""):
        assert prefer in {"", "ga4", "raw", "bq_raw"}
        if prefer == "ga4":
            return {
                "rows": {},
                "source": "ga4_export",
                "dataset": "analytics_1",
                "table": "events_*",
                "error": "GA4 empty",
            }
        return {
            "rows": {
                "Chrome": {"begin_checkout": 100, "purchase": 40, "conversion": 0.4},
                "Safari": {"begin_checkout": 80, "purchase": 10, "conversion": 0.125},
            },
            "source": "bigquery",
            "dataset": "loop_raw",
            "table": "events",
            "error": None,
        }

    monkeypatch.setattr("loop.connectors.bigquery.conversion_probe", fake_probe)
    monkeypatch.setattr(
        "loop.connectors.bigquery.read_metric_window",
        lambda *a, **k: {"claim": "live BQ claim", "source": "bigquery.events", "value": 0.4},
    )
    monkeypatch.setattr("loop.connectors.bigquery.metrics_daily_rows", lambda *a, **k: [])

    out = warehouse_proof(engine, tenant, metric="purchase_conversion")
    assert out["live"] is True
    assert out["source"] == "bigquery"
    assert out["dataset"] == "loop_raw"
    assert len(out["rows"]) == 2
    assert out["rows"][0]["browser"] == "Chrome"
    assert "file_warehouse" not in out["source"]


def test_warehouse_proof_metrics_daily_when_events_empty(engine, monkeypatch):
    tenant = Tenant(
        id="acme",
        name="Cove",
        product="Cove",
        warehouse_mode="bq_raw",
        bq_project="proj",
        bq_raw_dataset="loop_raw",
        bq_metrics_dataset="loop_metrics",
    )
    engine.store.put_tenant(tenant)
    monkeypatch.setattr(
        "loop.connectors.bigquery.conversion_probe",
        lambda *a, **k: {
            "rows": {},
            "source": "bigquery",
            "dataset": "loop_raw",
            "table": "events",
            "error": "empty",
        },
    )
    monkeypatch.setattr(
        "loop.connectors.bigquery.metrics_daily_rows",
        lambda *a, **k: [{"day": "2026-08-28", "value": 0.1734}, {"day": "2026-08-27", "value": 0.18}],
    )
    monkeypatch.setattr(
        "loop.connectors.bigquery.read_metric_window",
        lambda *a, **k: {"claim": "from metrics", "source": "bigquery.metrics_daily", "value": 0.1734},
    )
    out = warehouse_proof(engine, tenant)
    assert out["live"] is True
    assert out["source"] == "bigquery.metrics_daily"
    assert out["columns"] == ["day", "value"]
    assert out["rows"][0]["value"] == 0.1734


def test_warehouse_proof_does_not_fake_file_when_bq_configured(engine, monkeypatch):
    """Empty live BQ must stay live — never silently relabel as file warehouse."""
    tenant = Tenant(
        id="acme",
        name="Cove",
        product="Cove",
        warehouse_mode="auto",
        bq_project="proj",
        bq_raw_dataset="loop_raw",
        ga4_dataset="analytics_1",
    )
    monkeypatch.setattr(
        "loop.connectors.bigquery.conversion_probe",
        lambda *a, **k: {
            "rows": {},
            "source": "bigquery",
            "dataset": "loop_raw",
            "table": "events",
            "error": "loop_raw empty",
        },
    )
    monkeypatch.setattr("loop.connectors.bigquery.metrics_daily_rows", lambda *a, **k: [])
    monkeypatch.setattr("loop.connectors.bigquery.read_metric_window", lambda *a, **k: None)
    out = warehouse_proof(engine, tenant)
    assert out["live"] is True
    assert out["source"] != "file_warehouse"
    assert out["rows"] == []
    assert "empty" in (out.get("detail") or "").lower() or out.get("error")


def test_github_pr_proof_invalid_url():
    out = github_pr_proof("https://example.com/not-a-pr")
    assert out["status"] == "skipped"


def test_github_pr_proof_live(monkeypatch):
    def fake_request(method, url, token, body=None):
        if url.endswith("/pulls/12"):
            return 200, {
                "title": "Revert pay-sdk",
                "html_url": "https://github.com/acme/y/pull/12",
                "state": "open",
                "draft": False,
                "merged": False,
                "additions": 3,
                "deletions": 1,
                "changed_files": 2,
                "user": {"login": "bot"},
                "body": "flag off",
                "head": {"ref": "loop/fix"},
                "base": {"ref": "main"},
            }
        if url.endswith("/files"):
            return 200, [{"filename": "config/flags.json", "status": "modified", "additions": 3, "deletions": 1}]
        return 404, {}

    monkeypatch.setattr("loop.connectors.github.token_for_tenant", lambda t: "tok")
    monkeypatch.setattr("loop.connectors.github._request", fake_request)
    out = github_pr_proof("https://github.com/acme/y/pull/12")
    assert out["status"] == "applied"
    assert out["live"] is True
    assert out["title"] == "Revert pay-sdk"
    assert out["files"][0]["filename"] == "config/flags.json"


def test_homepage_proofs_uses_live_and_pr(engine, monkeypatch):
    tenant = Tenant(
        id="acme",
        name="Cove",
        product="Cove",
        repo="saurabh4269/cove",
        warehouse_mode="bq_raw",
        bq_project="proj",
        bq_raw_dataset="loop_raw",
        last_pr_url="https://github.com/saurabh4269/cove/pull/9",
        connected=True,
    )
    engine.store.put_tenant(tenant)
    monkeypatch.setattr(
        "loop.proof.warehouse_proof",
        lambda *a, **k: {
            "kind": "warehouse",
            "status": "applied",
            "source": "bigquery",
            "live": True,
            "rows": [{"browser": "Chrome", "begin_checkout": 1, "purchase": 1, "conversion": 1}],
            "columns": ["browser", "begin_checkout", "purchase", "conversion"],
        },
    )
    monkeypatch.setattr(
        "loop.proof.ga4_proof",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "loop.proof.github_pr_proof",
        lambda url, tenant=None: {
            "kind": "github",
            "status": "applied",
            "live": True,
            "title": "PR",
            "url": url,
        },
    )
    body = homepage_proofs(engine)
    assert body["warehouse"]["live"] is True
    assert body["warehouse"]["source"] == "bigquery"
    assert body["github"]["live"] is True


def test_agent_resources_signal(engine, monkeypatch):
    from loop.proof import agent_resources
    from loop.tenant import Tenant

    engine.store.put_tenant(
        Tenant(
            id="acme",
            name="Cove",
            product="Cove",
            repo="a/b",
            warehouse_mode="file",
            connected=True,
        )
    )
    monkeypatch.setattr(
        "loop.proof.warehouse_proof",
        lambda *a, **k: {"kind": "warehouse", "title": "BQ", "live": True, "rows": [], "columns": []},
    )
    monkeypatch.setattr(
        "loop.proof.ga4_proof",
        lambda *a, **k: {"kind": "ga4", "title": "GA4", "live": True, "rows": [], "columns": []},
    )
    cards = agent_resources(engine, "signal")
    kinds = {c["kind"] for c in cards}
    assert "ga4" in kinds
    assert "warehouse" in kinds


def test_proof_resources_endpoint(engine, monkeypatch):
    from fastapi.testclient import TestClient

    from loop import api as api_mod

    monkeypatch.setattr(api_mod, "_engine", engine)
    monkeypatch.setattr(api_mod, "get_engine", lambda: engine)
    engine.seed_world()
    with TestClient(api_mod.app) as client:
        res = client.get("/api/proof/resources?agent=signal_agent")
        assert res.status_code == 200
        assert res.json()["scope"] == "agent"
        assert isinstance(res.json()["cards"], list)
        home = client.get("/api/proof")
        assert home.status_code == 200
        assert "cards" in home.json()


def test_agent_snapshot_includes_resources(engine, monkeypatch):
    from loop.office import agent_snapshot

    monkeypatch.setattr(
        "loop.proof.agent_resources",
        lambda eng, aid: [{"kind": "ga4", "title": "GA4", "live": True}],
    )
    snap = agent_snapshot(engine, "signal_agent")
    assert snap is not None
    assert snap["resources"][0]["kind"] == "ga4"


def test_conversion_probe_falls_through_to_raw(monkeypatch):
    from datetime import date

    from loop.connectors import bigquery as bq
    from loop.tenant import Tenant

    t = Tenant(
        id="acme",
        name="Cove",
        product="Cove",
        warehouse_mode="auto",
        bq_project="proj",
        bq_raw_dataset="loop_raw",
        ga4_dataset="analytics_1",
    )
    monkeypatch.setattr(bq, "_client", lambda project: object())
    calls = {"ga4": 0, "raw": 0}

    def fake_ga4(*a, **k):
        calls["ga4"] += 1
        return []

    def fake_raw(*a, **k):
        calls["raw"] += 1
        return [{"browser": "Chrome", "begin_checkout": 10, "purchase": 2}]

    monkeypatch.setattr(bq, "_query_ga4_conversion", fake_ga4)
    monkeypatch.setattr(bq, "_query_raw_conversion", fake_raw)
    out = bq.conversion_probe(t, date(2026, 8, 25), date(2026, 9, 1), include_recovery=True)
    assert calls["ga4"] == 1 and calls["raw"] == 1
    assert out["source"] == "bigquery"
    assert out["rows"]["Chrome"]["purchase"] == 2
