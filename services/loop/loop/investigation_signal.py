"""Convert stored signals into AnomalyEvent for the unified investigation pipeline."""

from __future__ import annotations

from typing import Any

from .auto_investigate import tenant_id_from_signal
from .investigation import AnomalyEvent
from .models import Signal


def anomaly_event_from_signal(
    sig: Signal,
    *,
    note: str = "",
    tenant_id: str | None = None,
) -> AnomalyEvent:
    """Build a generic AnomalyEvent from a tenant or warehouse signal."""
    from .world import _tenant_ingest_dimensions

    bound = tenant_id or tenant_id_from_signal(sig)
    window = sig.detection_window if isinstance(sig.detection_window, dict) else {}
    src_note = note or str(window.get("source") or window.get("note") or "")
    dims: dict[str, Any] = {}
    if bound:
        dims = _tenant_ingest_dimensions(bound, sig.metric, float(sig.magnitude), src_note)
    seg = sig.affected_segments[0] if sig.affected_segments else None
    if seg and (seg.browser or seg.os or seg.platform or seg.geo):
        dims.setdefault("segments", {})
        seg_map = dims["segments"] if isinstance(dims.get("segments"), dict) else {}
        if seg.browser:
            seg_map["browser"] = seg.browser
        if seg.os:
            seg_map["os"] = seg.os
        if seg.platform:
            seg_map["platform"] = seg.platform
        if seg.geo:
            seg_map["geo"] = seg.geo
        dims["segments"] = seg_map
    polarity = "negative" if str(getattr(sig.direction, "value", sig.direction)) == "negative" else "positive"
    funnel = "checkout" if "conversion" in (sig.metric or "") or "checkout" in (sig.metric or "") else "product"
    return AnomalyEvent(
        kind="tenant_signal" if bound else "warehouse_signal",
        metric=sig.metric,
        title=f"{sig.metric} anomaly",
        magnitude=float(sig.magnitude),
        baseline=float(sig.baseline or 0),
        funnel_position=sig.funnel_position or funnel,
        confidence=float(sig.confidence or 0.6),
        source=sig.source or (f"tenant.{bound}" if bound else "warehouse"),
        polarity=polarity,
        family=str(getattr(sig.family, "value", sig.family) or "business"),
        dimensions=dims,
    )
