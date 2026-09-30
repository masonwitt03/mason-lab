from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class Store:
    """SQLite-backed memory: which alerts were sent, agent run history, and small per-agent state."""

    def __init__(self, path: str | Path = "data/mason_lab.db"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sent (agent TEXT, key TEXT, ts REAL, PRIMARY KEY (agent, key));
            CREATE TABLE IF NOT EXISTS alerts (agent TEXT, key TEXT, title TEXT, body TEXT,
                                               priority INT, url TEXT, data TEXT, ts REAL);
            CREATE TABLE IF NOT EXISTS runs (agent TEXT, ts REAL, ok INT, n_alerts INT, error TEXT);
            CREATE TABLE IF NOT EXISTS state (agent TEXT, k TEXT, v TEXT, PRIMARY KEY (agent, k));
            """
        )

    def was_sent(self, agent: str, key: str, cooldown_s: float) -> bool:
        row = self.db.execute("SELECT ts FROM sent WHERE agent=? AND key=?", (agent, key)).fetchone()
        return bool(row) and (time.time() - row[0]) < cooldown_s

    def record_alert(self, alert) -> None:
        now = time.time()
        self.db.execute("INSERT OR REPLACE INTO sent VALUES (?,?,?)", (alert.agent, alert.key, now))
        self.db.execute(
            "INSERT INTO alerts VALUES (?,?,?,?,?,?,?,?)",
            (alert.agent, alert.key, alert.title, alert.body, alert.priority, alert.url,
             json.dumps(alert.data, default=str), now),
        )
        self.db.commit()

    def record_run(self, agent: str, ok: bool, n_alerts: int, error: str | None = None) -> None:
        self.db.execute("INSERT INTO runs VALUES (?,?,?,?,?)", (agent, time.time(), int(ok), n_alerts, error))
        self.db.commit()

    def alerts_since(self, since_ts: float) -> list[dict[str, Any]]:
        cur = self.db.execute(
            "SELECT agent, key, title, body, priority, url, data, ts FROM alerts WHERE ts>=? ORDER BY priority DESC, ts",
            (since_ts,),
        )
        cols = [c[0] for c in cur.description]
        out = [dict(zip(cols, r)) for r in cur.fetchall()]
        for a in out:
            a["data"] = json.loads(a["data"] or "{}")
        return out

    def runs_since(self, since_ts: float) -> list[dict[str, Any]]:
        cur = self.db.execute("SELECT agent, ts, ok, n_alerts, error FROM runs WHERE ts>=?", (since_ts,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def get(self, agent: str, k: str, default: Any = None) -> Any:
        row = self.db.execute("SELECT v FROM state WHERE agent=? AND k=?", (agent, k)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, agent: str, k: str, v: Any) -> None:
        self.db.execute("INSERT OR REPLACE INTO state VALUES (?,?,?)", (agent, k, json.dumps(v, default=str)))
        self.db.commit()
