"""Signal schema + capture store. Stdlib only.

A Signal is the atomic unit of meta-learning: one observed fact about
how a conversation went. Signals are append-only; downstream consumers
(summarizer, evo-skillopt) read, never mutate.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field

SIGNAL_KINDS = (
    "task_success",     # agent completed what the user asked
    "task_failure",     # agent failed, errored, or user rejected output
    "user_feedback",    # explicit thumbs/correction/praise
    "coordination",     # multi-agent handoff observation
    "domain_insight",   # new reusable fact surfaced mid-session
    "emerging_need",    # user needed something no agent/skill covers
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    agent TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL,
    score REAL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_session ON signals(session_id);
CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts);
"""


@dataclass
class Signal:
    kind: str
    session_id: str
    detail: str
    agent: str = ""
    score: float | None = None  # -1.0..1.0 outcome/feedback strength
    ts: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def validate(self) -> Signal:
        if self.kind not in SIGNAL_KINDS:
            raise ValueError(f"unknown signal kind: {self.kind!r}")
        if not self.session_id:
            raise ValueError("session_id required")
        if not self.detail:
            raise ValueError("detail required")
        if self.score is not None and not (-1.0 <= self.score <= 1.0):
            raise ValueError("score must be in [-1.0, 1.0]")
        return self

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


class SignalStore:
    """SQLite WAL store. One shared connection behind a lock —
    stdlib sqlite3 is safe with that shape (same pattern as
    evo-skillopt's job queue)."""

    def __init__(self, db_path: str = "metaclaw.db"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def add(self, sig: Signal) -> Signal:
        sig.validate()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO signals (id, session_id, kind, agent, detail, score, ts)"
                " VALUES (?,?,?,?,?,?,?)",
                (sig.id, sig.session_id, sig.kind, sig.agent, sig.detail, sig.score, sig.ts),
            )
        return sig

    def for_session(self, session_id: str) -> list[Signal]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, session_id, kind, agent, detail, score, ts"
                " FROM signals WHERE session_id=? ORDER BY ts",
                (session_id,),
            ).fetchall()
        return [Signal(kind=r[2], session_id=r[1], detail=r[4], agent=r[3],
                       score=r[5], ts=r[6], id=r[0]) for r in rows]

    def sessions(self, since: float | None = None, limit: int = 100) -> list[str]:
        q = "SELECT DISTINCT session_id FROM signals"
        args: tuple = ()
        if since is not None:
            q += " WHERE ts>=?"
            args = (since,)
        q += " ORDER BY session_id LIMIT ?"
        with self._lock:
            return [r[0] for r in self._conn.execute(q, args + (limit,)).fetchall()]

    def counts_by_kind(self, session_id: str) -> dict[str, int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT kind, COUNT(*) FROM signals WHERE session_id=? GROUP BY kind",
                (session_id,),
            ).fetchall()
        return {k: n for k, n in rows}

    def close(self) -> None:
        with self._lock:
            self._conn.close()
