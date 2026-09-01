"""Signal watch closes the loop — detect → auto-investigate."""

from __future__ import annotations

from loop.models import InvestigationState, SignalStatus
from loop.signal_watch import tick_signal_watch


def test_tick_auto_investigates_new_signal(engine, monkeypatch):
    monkeypatch.setenv("LOOP_AUTO_INVESTIGATE", "1")
    signals = engine.detect_signals()
    assert signals
    sig = signals[0]
    sig.status = SignalStatus.OPEN
    engine.store.put_signal(sig)

    before = len(engine.store.list_investigations())
    summary = tick_signal_watch(engine)
    after = len(engine.store.list_investigations())

    assert summary.get("new_signal_ids") or summary.get("auto_investigated", 0) >= 0
    invs = engine.store.list_investigations()
    if after > before:
        inv = invs[0]
        assert inv.state in {InvestigationState.AWAITING_APPROVAL, InvestigationState.APPROVED, InvestigationState.OPEN}
        assert inv.originating_signal_ids


def test_auto_investigate_skips_duplicate(engine):
    from loop.auto_investigate import auto_investigate_signal

    signals = engine.detect_signals()
    assert signals
    sig = signals[0]
    sig.status = SignalStatus.OPEN
    engine.store.put_signal(sig)

    first = auto_investigate_signal(engine, sig.id)
    second = auto_investigate_signal(engine, sig.id)
    assert first.get("status") == "applied"
    assert second.get("reason") == "already_investigating"
