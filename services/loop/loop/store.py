"""Durable SQLite control plane. Investigation state never lives only in process memory."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .models import (
    AgentCall,
    Approval,
    Evidence,
    Hypothesis,
    Investigation,
    Lesson,
    Outcome,
    PolicyVerdict,
    ProposedAction,
    Room,
    RoomMessage,
    Signal,
    TimelineEvent,
)
from .tenant import Tenant

T = TypeVar("T", bound=BaseModel)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS investigations (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hypotheses (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS approvals (id TEXT PRIMARY KEY, action_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outcomes (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lessons (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS verdicts (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS timeline (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agent_calls (id TEXT PRIMARY KEY, investigation_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS idempotency (
  key TEXT PRIMARY KEY,
  tool TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
  name TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_key TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
  tokenized_user TEXT PRIMARY KEY,
  count INTEGER NOT NULL,
  last_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS customer_identities (
  tokenized_user TEXT PRIMARY KEY,
  json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS customer_outreach (
  id TEXT PRIMARY KEY,
  investigation_id TEXT,
  json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rooms (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, room_id TEXT, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, json TEXT NOT NULL);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _put(self, table: str, obj: BaseModel, extra: dict[str, Any] | None = None) -> None:
        payload = obj.model_dump(mode="json")
        cols = ["id", "json"]
        vals: list[Any] = [obj.id, json.dumps(payload)]  # type: ignore[attr-defined]
        if extra:
            for k, v in extra.items():
                cols.insert(-1, k)
                vals.insert(-1, v)
        placeholders = ",".join("?" * len(cols))
        colnames = ",".join(cols)
        updates = ",".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = f"INSERT INTO {table} ({colnames}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}"
        with self._lock:
            self._conn.execute(sql, vals)
            self._conn.commit()
        self._maybe_snapshot()

    def _maybe_snapshot(self) -> None:
        try:
            from loop.state_persist import schedule_snapshot

            schedule_snapshot(self.path)
        except Exception:
            pass

    def _get(self, table: str, model: type[T], id_: str) -> T | None:
        with self._lock:
            row = self._conn.execute(f"SELECT json FROM {table} WHERE id=?", (id_,)).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def _list(self, table: str, model: type[T], where: str = "", args: tuple = ()) -> list[T]:
        sql = f"SELECT json FROM {table} {where}"
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [model.model_validate_json(r[0]) for r in rows]

    def put_signal(self, s: Signal) -> None:
        self._put("signals", s)

    def get_signal(self, id_: str) -> Signal | None:
        return self._get("signals", Signal, id_)

    def list_signals(self) -> list[Signal]:
        return self._list("signals", Signal)

    def put_investigation(self, inv: Investigation) -> None:
        self._put("investigations", inv)

    def get_investigation(self, id_: str) -> Investigation | None:
        return self._get("investigations", Investigation, id_)

    def list_investigations(self) -> list[Investigation]:
        return self._list("investigations", Investigation)

    def put_evidence(self, e: Evidence) -> None:
        self._put("evidence", e, {"investigation_id": e.investigation_id})

    def list_evidence(self, investigation_id: str) -> list[Evidence]:
        return self._list(
            "evidence", Evidence, "WHERE investigation_id=?", (investigation_id,)
        )

    def put_hypothesis(self, h: Hypothesis) -> None:
        self._put("hypotheses", h, {"investigation_id": h.investigation_id})

    def list_hypotheses(self, investigation_id: str) -> list[Hypothesis]:
        return self._list(
            "hypotheses", Hypothesis, "WHERE investigation_id=?", (investigation_id,)
        )

    def put_action(self, a: ProposedAction) -> None:
        self._put("actions", a, {"investigation_id": a.investigation_id})

    def get_action(self, id_: str) -> ProposedAction | None:
        return self._get("actions", ProposedAction, id_)

    def list_actions(self, investigation_id: str | None = None) -> list[ProposedAction]:
        if investigation_id:
            return self._list("actions", ProposedAction, "WHERE investigation_id=?", (investigation_id,))
        return self._list("actions", ProposedAction)

    def pending_approvals(self) -> list[ProposedAction]:
        return [a for a in self.list_actions() if a.status in {"proposed", "awaiting_approval"}]

    def put_approval(self, a: Approval) -> None:
        self._put("approvals", a, {"action_id": a.action_id})

    def list_approvals(self, action_id: str | None = None) -> list[Approval]:
        if action_id:
            return self._list("approvals", Approval, "WHERE action_id=?", (action_id,))
        return self._list("approvals", Approval)

    def put_outcome(self, o: Outcome) -> None:
        self._put("outcomes", o, {"investigation_id": o.investigation_id})

    def list_outcomes(self) -> list[Outcome]:
        return self._list("outcomes", Outcome)

    def put_lesson(self, lesson: Lesson) -> None:
        self._put("lessons", lesson, {"investigation_id": lesson.investigation_id})
        try:
            from loop import firestore_memory

            firestore_memory.upsert_from_lesson(lesson)
        except Exception:
            pass

    def list_lessons(self) -> list[Lesson]:
        return self._list("lessons", Lesson)

    def put_verdict(self, v: PolicyVerdict) -> None:
        self._put("verdicts", v)

    def list_verdicts(self) -> list[PolicyVerdict]:
        return self._list("verdicts", PolicyVerdict)

    def put_timeline(self, e: TimelineEvent) -> None:
        self._put("timeline", e, {"investigation_id": e.investigation_id})

    def list_timeline(self, investigation_id: str) -> list[TimelineEvent]:
        events = self._list("timeline", TimelineEvent, "WHERE investigation_id=?", (investigation_id,))
        return sorted(events, key=lambda x: x.at)

    def put_agent_call(self, c: AgentCall) -> None:
        self._put("agent_calls", c, {"investigation_id": c.investigation_id})

    def list_agent_calls(self, investigation_id: str) -> list[AgentCall]:
        return self._list("agent_calls", AgentCall, "WHERE investigation_id=?", (investigation_id,))

    def list_all_agent_calls(self) -> list[AgentCall]:
        calls = self._list("agent_calls", AgentCall)
        return sorted(calls, key=lambda c: c.started_at)

    def list_all_messages(self) -> list[RoomMessage]:
        msgs = self._list("messages", RoomMessage)
        return sorted(msgs, key=lambda m: m.created_at)

    def claim_idempotency(self, key: str, tool: str, compute) -> tuple[Any, bool]:
        """Return (result, reused). Honours A-7 at-least-once without duplicate side effects."""
        with self._lock:
            row = self._conn.execute(
                "SELECT result_json FROM idempotency WHERE key=?", (key,)
            ).fetchone()
            if row:
                return json.loads(row[0]), True
            result = compute()
            self._conn.execute(
                "INSERT INTO idempotency (key, tool, result_json, created_at) VALUES (?,?,?,?)",
                (key, tool, json.dumps(result), _now()),
            )
            self._conn.commit()
            return result, False

    def set_flag(self, name: str, value: str, key: str) -> tuple[str, bool]:
        def _set() -> dict:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO flags (name, value, updated_at, last_key) VALUES (?,?,?,?) "
                    "ON CONFLICT(name) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, last_key=excluded.last_key",
                    (name, value, _now(), key),
                )
                self._conn.commit()
            return {"name": name, "value": value}

        result, reused = self.claim_idempotency(key, "set_flag", _set)
        if not reused:
            try:
                from loop.flags_persist import persist_flags

                persist_flags(self)
            except Exception:
                pass
        return result["value"], reused

    def restore_flags(self, flags: dict[str, str]) -> None:
        """Restore flags from GCS without idempotency (cold start hydrate)."""
        if not flags:
            return
        with self._lock:
            for name, value in flags.items():
                self._conn.execute(
                    "INSERT INTO flags (name, value, updated_at, last_key) VALUES (?,?,?,?) "
                    "ON CONFLICT(name) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at, last_key=excluded.last_key",
                    (name, value, _now(), "gcs-restore"),
                )
            self._conn.commit()

    def get_flag(self, name: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM flags WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

    def list_flags(self) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute("SELECT name, value FROM flags").fetchall()
        return {r[0]: r[1] for r in rows}

    def put_tenant(self, tenant: Tenant) -> None:
        self._put("tenants", tenant)

    def get_tenant(self, id_: str) -> Tenant | None:
        return self._get("tenants", Tenant, id_)

    def list_tenants(self) -> list[Tenant]:
        return self._list("tenants", Tenant)

    def record_contact(self, tokenized_user: str, cap: int) -> bool:
        """L-4: frequency cap in tool code. Returns False if blocked."""
        with self._lock:
            row = self._conn.execute(
                "SELECT count FROM contacts WHERE tokenized_user=?", (tokenized_user,)
            ).fetchone()
            count = row[0] if row else 0
            if count >= cap:
                return False
            self._conn.execute(
                "INSERT INTO contacts (tokenized_user, count, last_at) VALUES (?,?,?) "
                "ON CONFLICT(tokenized_user) DO UPDATE SET count=count+1, last_at=excluded.last_at",
                (tokenized_user, 1, _now()),
            )
            self._conn.commit()
            return True

    def put_customer_identity(self, identity: dict[str, Any]) -> dict[str, Any]:
        """Upsert Product Y registration identity (email + phone + consent)."""
        tok = str(identity.get("tokenized_user") or "").strip()
        if not tok:
            raise ValueError("tokenized_user required")
        existing = self.get_customer_identity(tok) or {}
        merged = {**existing, **{k: v for k, v in identity.items() if v is not None and v != ""}}
        merged["tokenized_user"] = tok
        merged["updated_at"] = _now()
        if "created_at" not in merged:
            merged["created_at"] = merged["updated_at"]
        with self._lock:
            self._conn.execute(
                "INSERT INTO customer_identities (tokenized_user, json) VALUES (?,?) "
                "ON CONFLICT(tokenized_user) DO UPDATE SET json=excluded.json",
                (tok, json.dumps(merged)),
            )
            self._conn.commit()
        self._maybe_snapshot()
        return merged

    def get_customer_identity(self, tokenized_user: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT json FROM customer_identities WHERE tokenized_user=?",
                (tokenized_user,),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_customer_identities(self, *, tenant_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT json FROM customer_identities").fetchall()
        out = [json.loads(r[0]) for r in rows]
        if tenant_id:
            out = [x for x in out if x.get("tenant_id") in (None, tenant_id)]
        return out

    def put_outreach(self, row: dict[str, Any]) -> dict[str, Any]:
        oid = str(row.get("id") or "")
        if not oid:
            raise ValueError("outreach id required")
        inv = str(row.get("investigation_id") or "")
        with self._lock:
            self._conn.execute(
                "INSERT INTO customer_outreach (id, investigation_id, json) VALUES (?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET investigation_id=excluded.investigation_id, json=excluded.json",
                (oid, inv, json.dumps(row)),
            )
            self._conn.commit()
        self._maybe_snapshot()
        return row

    def get_outreach(self, id_: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT json FROM customer_outreach WHERE id=?", (id_,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_outreach(
        self,
        *,
        investigation_id: str | None = None,
        room_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if investigation_id:
                rows = self._conn.execute(
                    "SELECT json FROM customer_outreach WHERE investigation_id=?",
                    (investigation_id,),
                ).fetchall()
            else:
                rows = self._conn.execute("SELECT json FROM customer_outreach").fetchall()
        out = [json.loads(r[0]) for r in rows]
        if room_id:
            out = [x for x in out if x.get("room_id") == room_id]
        if status:
            out = [x for x in out if x.get("status") == status]
        out.sort(key=lambda x: str(x.get("created_at") or ""))
        return out

    def put_memory(self, id_: str, kind: str, payload: dict, *, tenant_id: str | None = None) -> None:
        body = dict(payload)
        if tenant_id:
            body["tenant_id"] = tenant_id
        with self._lock:
            self._conn.execute(
                "INSERT INTO memory (id, kind, json) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET json=excluded.json",
                (id_, kind, json.dumps(body)),
            )
            self._conn.commit()
        try:
            from loop import firestore_memory

            firestore_memory.upsert_from_memory(id_, kind, body)
        except Exception:
            pass

    def list_memory(self, kind: str | None = None, *, tenant_id: str | None = None) -> list[dict]:
        with self._lock:
            if kind:
                rows = self._conn.execute("SELECT id, kind, json FROM memory WHERE kind=?", (kind,)).fetchall()
            else:
                rows = self._conn.execute("SELECT id, kind, json FROM memory").fetchall()
        out = []
        for row in rows:
            payload = json.loads(row[2])
            payload.setdefault("id", row[0])
            payload.setdefault("kind", row[1])
            if tenant_id and payload.get("tenant_id") not in (None, tenant_id):
                continue
            out.append(payload)
        return out

    def put_room(self, room: Room) -> None:
        self._put("rooms", room)

    def get_room(self, id_: str) -> Room | None:
        return self._get("rooms", Room, id_)

    def list_rooms(self) -> list[Room]:
        rooms = self._list("rooms", Room)
        return sorted(rooms, key=lambda r: (r.kind.value, r.created_at), reverse=False)

    def put_message(self, msg: RoomMessage) -> None:
        self._put("messages", msg, {"room_id": msg.room_id})

    def list_messages(self, room_id: str) -> list[RoomMessage]:
        msgs = self._list("messages", RoomMessage, "WHERE room_id=?", (room_id,))
        return sorted(msgs, key=lambda m: m.created_at)

    def put_job(self, job: Any) -> None:
        from .jobs import Job

        assert isinstance(job, Job)
        self._put("jobs", job)

    def get_job(self, id_: str) -> Any | None:
        from .jobs import Job

        return self._get("jobs", Job, id_)

    def list_jobs(self, *, status: str | None = None, kind: str | None = None, limit: int = 50) -> list[Any]:
        from .jobs import Job

        clauses: list[str] = []
        args: list[Any] = []
        if status:
            clauses.append("json LIKE ?")
            args.append(f'%"status": "{status}"%')
        if kind:
            clauses.append("json LIKE ?")
            args.append(f'%"kind": "{kind}"%')
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._list("jobs", Job, where, tuple(args))
        rows.sort(key=lambda j: j.created_at, reverse=True)
        return rows[:limit]

    def claim_job(self, kinds: list[str]) -> Any | None:
        from .jobs import Job

        now = _now()
        with self._lock:
            rows = self._conn.execute("SELECT id, json FROM jobs").fetchall()
            candidates: list[tuple[str, Job]] = []
            for jid, raw in rows:
                job = Job.model_validate_json(raw)
                if job.status != "queued" or job.kind not in kinds:
                    continue
                if job.run_after and job.run_after > now:
                    continue
                candidates.append((jid, job))
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[1].created_at)
            job_id, job = candidates[0]
            self._conn.execute("BEGIN IMMEDIATE")
            cur = self._conn.execute("SELECT json FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not cur:
                self._conn.rollback()
                return None
            current = Job.model_validate_json(cur[0])
            if current.status != "queued":
                self._conn.rollback()
                return None
            job.status = "running"
            job.updated_at = now
            self._conn.execute(
                "UPDATE jobs SET json = ? WHERE id = ?",
                (job.model_dump_json(), job_id),
            )
            self._conn.commit()
            return job

    def put_audit(self, event: Any) -> None:
        from .audit import AuditEvent

        assert isinstance(event, AuditEvent)
        self._put("audit", event)

    def list_audit(self, limit: int = 100) -> list[Any]:
        from .audit import AuditEvent

        rows = self._list("audit", AuditEvent)
        rows.sort(key=lambda e: e.at, reverse=True)
        return rows[:limit]
