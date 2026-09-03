"""Room UI truth — GitHub card lifecycle and pending approval visibility."""

from __future__ import annotations

from typing import Any


def _execution_blob(action: Any) -> dict[str, Any]:
    arts = getattr(action, "artifacts", None) or {}
    if not isinstance(arts, dict):
        return {}
    exe = arts.get("execution")
    return dict(exe) if isinstance(exe, dict) else {}


def investigation_pr_url(store: Any, inv_id: str | None) -> str | None:
    """First tenant PR URL opened by any action on this investigation."""
    if not inv_id or not hasattr(store, "list_actions"):
        return None
    for act in store.list_actions(inv_id):
        exe = _execution_blob(act)
        for key in ("pr_url", "code_pr_url"):
            url = exe.get(key)
            if isinstance(url, str) and "/pull/" in url:
                return url
    return None


def investigation_pr_opened(store: Any, inv_id: str | None) -> bool:
    if not inv_id or not hasattr(store, "list_actions"):
        return False
    for act in store.list_actions(inv_id):
        exe = _execution_blob(act)
        if exe.get("pr_opened") or exe.get("pr_url") or exe.get("code_pr_url"):
            return True
    return False


def github_card_lifecycle(
    *,
    pr_url: str | None,
    connector_status: str,
) -> str:
    """Map connector outcome to GitHub work-card lifecycle (running|done|failed)."""
    if pr_url:
        return "done"
    if connector_status == "failed":
        return "failed"
    if connector_status in {"applied", "done", "skipped"}:
        return "done"
    if connector_status == "running":
        return "running"
    return "done"


def github_card_title(*, pr_url: str | None, connector_status: str, default: str) -> str:
    if pr_url:
        return "Pull request open"
    if connector_status == "failed":
        return default if "fail" in default.lower() else "Code fix failed"
    if connector_status == "skipped":
        return "Code fix skipped"
    return default


def suppress_pending_action(store: Any, action: Any, *, inv_pr_url: str | None = None) -> bool:
    """Hide duplicate blocking approvals when a sibling already shipped the tenant PR."""
    if getattr(action, "status", None) not in {"proposed", "awaiting_approval"}:
        return False
    if getattr(action, "type", None) != "code_change":
        return False
    pr_url = inv_pr_url if inv_pr_url is not None else investigation_pr_url(store, action.investigation_id)
    if not pr_url:
        return False
    exe = _execution_blob(action)
    if exe.get("pr_url") or exe.get("pr_opened"):
        return False
    return True


def visible_pending_actions(store: Any, inv_id: str) -> list[Any]:
    pr_url = investigation_pr_url(store, inv_id)
    pending = [
        act
        for act in store.list_actions(inv_id)
        if act.status in {"proposed", "awaiting_approval"}
    ]
    return [act for act in pending if not suppress_pending_action(store, act, inv_pr_url=pr_url)]


def receipt_proof_status(
    *,
    kind: str,
    receipt_status: str,
    pr_url: str | None,
) -> str:
    """Normalize receipt lifecycle for GitHub cards shown in the room thread."""
    if kind == "github" and pr_url:
        return "done"
    return receipt_status
