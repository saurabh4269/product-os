"""Work receipts — Cursor-style proof that real side effects landed in chat.

Every connector action (flag, PR, mail, calendar, call, memory) should post a
receipt into the room so the user sees work happen without leaving Product OS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loop.world import post


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def flag_proof(*, name: str, value: str, previous: str | None = None) -> dict[str, Any]:
    return {
        "kind": "flags",
        "status": "applied",
        "title": f"{name} → {value}",
        "subtitle": "Feature flag",
        "detail": f"Was {previous}" if previous else f"Set to {value}",
        "live": True,
        "source": "store.flags",
    }


def calendar_proof(slot: dict[str, Any] | None = None, *, report: dict[str, Any] | None = None) -> dict[str, Any]:
    slot = slot or {}
    report = report or {}
    url = (
        report.get("url")
        or slot.get("html_link")
        or slot.get("meet_url")
        or slot.get("url")
        or report.get("meet_url")
    )
    start = slot.get("start") or report.get("start") or ""
    title = slot.get("summary") or report.get("summary") or "Calendar hold"
    return {
        "kind": "workspace",
        "status": report.get("status") or "applied",
        "title": str(title),
        "subtitle": str(start)[:32] if start else "Workspace calendar",
        "detail": report.get("detail") or slot.get("detail") or "Hold created",
        "url": url,
        "console_url": url,
        "live": bool(url),
        "source": report.get("connector") or "calendar",
    }


def call_proof(artifact: dict[str, Any]) -> dict[str, Any]:
    phone = artifact.get("to_number") or artifact.get("phone") or artifact.get("to")
    return {
        "kind": "contacts",
        "status": artifact.get("status") or "applied",
        "title": artifact.get("title") or "Customer call",
        "subtitle": str(phone or "callback"),
        "detail": artifact.get("detail") or artifact.get("reason") or "",
        "phone": phone,
        "found": artifact.get("found"),
        "live": True,
        "source": "telephony",
    }


def memory_proof(*, statement: str, lesson_id: str | None = None) -> dict[str, Any]:
    return {
        "kind": "memory",
        "status": "applied",
        "title": "Lesson written",
        "subtitle": lesson_id or "Memory Bank",
        "detail": (statement or "")[:280],
        "live": True,
        "source": "memory",
    }


def post_receipt(
    engine: Any,
    room_id: str,
    *,
    kind: str,
    title: str,
    agent: str = "code_agent",
    status: str = "done",
    detail: str = "",
    summary: list[str] | None = None,
    open_url: str | None = None,
    proof: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> Any:
    """Post a work receipt into the room thread (and over WS)."""
    body = {
        "kind": kind,
        "status": status,  # running | done | failed
        "title": title,
        "detail": detail,
        "summary": summary or ([detail] if detail else []),
        "open_url": open_url,
        "url": open_url,
        "agent": agent,
        "at": _now_iso(),
        "proof": proof,
        **(extra or {}),
    }
    # Prefer nested proof for rich embeds; keep receipt envelope for status chip.
    text = title if status != "running" else f"{title}…"
    return post(
        engine,
        room_id,
        author=agent,
        author_kind="agent",
        kind="artifact",
        text=text,
        artifact_type="receipt",
        artifact=body,
    )


def post_connector_receipts(
    engine: Any,
    room_id: str,
    *,
    flag: dict[str, Any] | None = None,
    connectors: list[dict[str, Any]] | None = None,
    pr_url: str | None = None,
    agent: str = "code_agent",
) -> None:
    """Emit receipts for an execute_approved result bundle."""
    if flag and flag.get("name"):
        post_receipt(
            engine,
            room_id,
            kind="flags",
            title=f"Flag {flag['name']} → {flag.get('value')}",
            agent=agent,
            status="done",
            detail=str(flag.get("detail") or ""),
            proof=flag_proof(name=str(flag["name"]), value=str(flag.get("value") or ""), previous=flag.get("from")),
        )
    for rep in connectors or []:
        if not isinstance(rep, dict):
            continue
        conn = str(rep.get("connector") or "")
        url = rep.get("url")
        st = str(rep.get("status") or "skipped")
        receipt_status = "done" if st == "applied" else ("failed" if st == "failed" else "done")
        if "github.pr" in conn or (isinstance(url, str) and "/pull/" in url):
            # PR has its own dedicated post elsewhere when URL is final.
            if url and not pr_url:
                from loop.proof import github_pr_proof

                post_receipt(
                    engine,
                    room_id,
                    kind="github",
                    title="Opened pull request",
                    agent=agent,
                    status=receipt_status,
                    detail=str(rep.get("detail") or ""),
                    open_url=str(url),
                    proof=github_pr_proof(str(url)),
                    extra={"pr_url": url},
                )
            continue
        if "github.issue" in conn:
            post_receipt(
                engine,
                room_id,
                kind="github",
                title="Opened GitHub issue",
                agent=agent,
                status=receipt_status,
                detail=str(rep.get("detail") or ""),
                open_url=str(url) if url else None,
                proof={
                    "kind": "github",
                    "status": st,
                    "title": "GitHub issue",
                    "detail": rep.get("detail") or "",
                    "url": url,
                    "console_url": url,
                    "state": "open",
                },
            )
            continue
        if "mail" in conn or "gmail" in conn:
            from loop.proof import mail_proof

            post_receipt(
                engine,
                room_id,
                kind="gmail",
                title="Mail draft" if "draft" in conn or st != "applied" else "Mail sent",
                agent="coordination_agent",
                status=receipt_status,
                detail=str(rep.get("detail") or ""),
                open_url=str(url) if url else None,
                proof=mail_proof({"report": rep, "gmail_url": url, "subject": "Follow-up", "channel": conn}),
            )
            continue
        if "calendar" in conn:
            post_receipt(
                engine,
                room_id,
                kind="workspace",
                title="Calendar hold",
                agent="coordination_agent",
                status=receipt_status,
                detail=str(rep.get("detail") or ""),
                open_url=str(url) if url else None,
                proof=calendar_proof(report=rep),
            )
            continue
        # Generic connector receipt so nothing is silent
        post_receipt(
            engine,
            room_id,
            kind="other",
            title=conn or "Connector",
            agent=agent,
            status=receipt_status,
            detail=str(rep.get("detail") or st),
            open_url=str(url) if url else None,
            proof={
                "kind": "gateway",
                "status": st,
                "title": conn or "Connector",
                "detail": rep.get("detail") or "",
                "url": url,
                "console_url": url,
            },
        )
