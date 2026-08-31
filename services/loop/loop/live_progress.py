"""SalesShortcut-style incremental UI updates during investigation."""

from __future__ import annotations

import os
import time
from typing import Any

from loop.activity import emit_activity
from loop.agents.graphs import AGENT_STAGE


def publish_agent_progress(
    room_id: str,
    agent_id: str,
    message: str,
    *,
    tenant_id: str = "",
    stage: str | None = None,
    artifact: dict[str, Any] | None = None,
    delay: bool = False,
) -> None:
    """Push activity + funnel_stage + agent_callback so the pipeline board moves live."""
    st = stage or AGENT_STAGE.get(agent_id, "investigate")
    emit_activity(
        agent_id=agent_id,
        message=message,
        room_id=room_id,
        stage=st,
        tenant_id=tenant_id,
        artifact=artifact,
    )
    try:
        from loop.live import HUB

        frame = {"type": "funnel_stage", "stage": st, "agentId": agent_id, "roomId": room_id}
        HUB.publish_global(frame)
        if room_id:
            HUB.publish(room_id, frame)
            HUB.publish(
                room_id,
                {
                    "type": "agent_callback",
                    "agentId": agent_id,
                    "status": "idle",
                    "message": message,
                    "stage": st,
                    "artifact": artifact,
                },
            )
    except Exception:
        pass
    if delay or os.environ.get("LOOP_DEMO_STAGED") == "1":
        time.sleep(float(os.environ.get("LOOP_DEMO_STAGE_MS", "120")) / 1000.0)


def publish_stage(room_id: str, stage: str, agent_id: str, message: str, *, tenant_id: str = "", delay: bool = False) -> None:
    publish_agent_progress(room_id, agent_id, message, tenant_id=tenant_id, stage=stage, delay=delay)
