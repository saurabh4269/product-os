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
CREATE TABLE IF NOT EXISTS memory (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rooms (id TEXT PRIMARY KEY, json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, room_id TEXT, json TEXT NOT NULL);
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
        return result["value"], reused

    def get_flag(self, name: str) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM flags WHERE name=?", (name,)).fetchone()
        return row[0] if row else None

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

    def put_memory(self, id_: str, kind: str, payload: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO memory (id, kind, json) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET json=excluded.json",
                (id_, kind, json.dumps(payload)),
            )
            self._conn.commit()

    def list_memory(self, kind: str | None = None) -> list[dict]:
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
