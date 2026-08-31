"""Signal dedupe — detect must not mint duplicate Safari rows."""

from __future__ import annotations

from loop.engine import dedupe_signals
from loop.models import Segment


def test_detect_signals_is_idempotent(engine):
    first = engine.detect_signals()
    second = engine.detect_signals()
    assert len(first) >= 1
    assert len(second) >= 1
    safari_first = [s for s in first if any(seg.browser == "Safari" for seg in s.affected_segments)]
    assert safari_first
    ids = {s.id for s in engine.store.list_signals() if any(seg.browser == "Safari" for seg in s.affected_segments)}
    assert len(ids) == 1


def test_dedupe_signals_keeps_newest():
    from datetime import datetime, timezone

    from loop.models import Direction, Signal, SignalFamily, SignalStatus

    a = Signal(
        id="sig_a",
        family=SignalFamily.BUSINESS,
        direction=Direction.NEGATIVE,
        funnel_position="purchase",
        metric="purchase_conversion",
        magnitude=-0.2,
        baseline=0.1,
        affected_segments=[Segment(browser="Safari", os="iOS", platform="web")],
        detection_window={},
        confidence=0.9,
        source="test",
        status=SignalStatus.OPEN,
        detected_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    b = a.model_copy(update={"id": "sig_b", "magnitude": -0.538, "detected_at": datetime(2026, 8, 2, tzinfo=timezone.utc)})
    out = dedupe_signals([a, b])
    assert len(out) == 1
    assert out[0].id == "sig_b"
    assert out[0].magnitude == -0.538
