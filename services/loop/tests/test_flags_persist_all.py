"""All tenant-scoped flags persist to GCS."""

from __future__ import annotations

from loop.flags_persist import filter_persistable, persist_flags


def test_custom_tenant_flag_persisted(engine, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    written: dict = {}

    def fake_write(uri, data):
        written.update(data)
        return True

    monkeypatch.setattr("loop.gcs_state.write_json", fake_write)
    monkeypatch.setattr("loop.flags_persist.flags_gcs_uri", lambda: "gs://test-bucket/tenant_flags.json")

    engine.store.set_flag("t:acme:checkout_experiment", "on", "key1")
    persist_flags(engine.store)
    assert "t:acme:checkout_experiment" in written.get("flags", {})

    filtered = filter_persistable({"t:beta:custom_flag": "off", "ephemeral": "1"})
    assert "t:beta:custom_flag" in filtered
    assert "ephemeral" not in filtered
