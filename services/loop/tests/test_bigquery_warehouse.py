"""BigQuery warehouse config and file fallbacks (no live GCP in CI)."""

from __future__ import annotations

from datetime import date

from loop.connectors.bigquery import (
    enrich_anomaly_dimensions,
    has_bq,
    read_metric_window,
    resolve_bq_config,
)
from loop.tenant import Tenant


def test_resolve_bq_config_from_tenant_fields():
    t = Tenant(
        id="acme",
        name="Acme",
        product="Cove",
        bq_project="proj",
        bq_raw_dataset="loop_raw",
        warehouse_mode="bq_raw",
    )
    cfg = resolve_bq_config(t)
    assert cfg is not None
    assert cfg.project == "proj"
    assert cfg.raw_dataset == "loop_raw"
    assert has_bq(t)


def test_file_mode_disables_bq():
    t = Tenant(id="x", name="X", product="Y", warehouse_mode="file", bq_raw_dataset="loop_raw")
    assert resolve_bq_config(t) is None
    assert not has_bq(t)


def test_read_metric_window_file_fallback(engine):
    t = Tenant(id="acme", name="Acme", product="Cove", warehouse_mode="file")
    out = read_metric_window(engine, t, "purchase_conversion", baseline=0.08)
    assert out is not None
    assert out["source"] == "file_warehouse"
    assert "conversion" in out["claim"].lower()


def test_enrich_signal_dict_file_mode(engine):
    from loop.tenant import Tenant
    from loop.unified_runner import enrich_signal_dict

    t = Tenant(id="acme", name="Acme", product="Cove", warehouse_mode="file")
    engine.store.put_tenant(t)
    out = enrich_signal_dict(
        engine,
        {"metric": "checkout_conversion", "dimensions": {}},
        tenant_id="acme",
    )
    assert out["tenant_id"] == "acme"


def test_enrich_anomaly_dimensions_file_mode_noop():
    t = Tenant(id="acme", name="Acme", product="Cove", warehouse_mode="file")
    dims = enrich_anomaly_dimensions(None, t, {"hypothesis": "test"})
    assert dims == {"hypothesis": "test"}


def test_detect_all_signals_includes_file_warehouse(engine):
    found = engine.detect_all_signals()
    assert isinstance(found, list)
