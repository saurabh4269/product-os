"""Flags GCS persistence across cold start."""

from __future__ import annotations

from loop.flags_persist import hydrate_flags, persist_flags


def test_flags_persist_and_hydrate(tmp_path, monkeypatch):
    from loop.engine import LoopEngine
    from loop.store import Store
    from loop.warehouse import Warehouse

    wh = tmp_path / "wh"
    wh.mkdir()
    (wh / "meta.json").write_text('{"days":1,"events":1}')
    store_a = Store(tmp_path / "a.db")
    LoopEngine(store_a, Warehouse(wh))

    blob: dict = {}

    def fake_write(uri, data):
        blob.clear()
        blob.update(data)

    def fake_read(uri):
        return dict(blob)

    monkeypatch.setattr("loop.flags_persist.flags_gcs_uri", lambda: "gs://test/tenant_flags.json")
    monkeypatch.setattr("loop.gcs_state.write_json", fake_write)
    monkeypatch.setattr("loop.gcs_state.read_json", fake_read)

    store_a.set_flag("pay_sdk_4_3", "off", "act-1")
    store_a.set_flag("t:acme:pay_sdk_4_3", "off", "act-1:t")
    assert blob.get("flags", {}).get("pay_sdk_4_3") == "off"

    store_b = Store(tmp_path / "b.db")
    engine_b = LoopEngine(store_b, Warehouse(wh))
    assert engine_b.store.get_flag("pay_sdk_4_3") is None
    n = hydrate_flags(store_b)
    assert n >= 1
    assert store_b.get_flag("pay_sdk_4_3") == "off"
    assert store_b.get_flag("t:acme:pay_sdk_4_3") == "off"

    persist_flags(store_b)
    assert blob["flags"]["pay_sdk_4_3"] == "off"
