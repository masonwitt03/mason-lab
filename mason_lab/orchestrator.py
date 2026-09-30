from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from .agents import REGISTRY, Agent, AgentContext
from .agents.base import default_http
from .models import HIGH, PRIORITY_NAMES, Alert
from .notify import Notifier
from .store import Store

log = logging.getLogger(__name__)


class Controller:
    """The central system: owns every agent, schedules them, dedupes their alerts,
    routes alerts to your phone/Discord/Telegram, and sends one daily briefing."""

    def __init__(self, cfg: dict[str, Any], store: Store | None = None, notifier: Notifier | None = None,
                 http: Any = None, agents: dict[str, Agent] | None = None):
        self.cfg = cfg
        self.store = store or Store(cfg.get("database", "data/mason_lab.db"))
        self.http = http or default_http()
        self.notifier = notifier or Notifier(cfg.get("notify", {}), self.http)
        self.ctx = AgentContext(store=self.store, http=self.http, dry_run=bool(cfg.get("dry_run", False)))
        if agents is not None:
            self.agents = agents
        else:
            acfg = cfg.get("agents", {})
            self.agents = {name: cls(acfg.get(name, {})) for name, cls in REGISTRY.items()
                           if (acfg.get(name) or {}).get("enabled", False)}
        self._next_run = {name: 0.0 for name in self.agents}

    def run_agent(self, name: str) -> list[Alert]:
        agent = self.agents[name]
        try:
            alerts = agent.run(self.ctx) or []
        except Exception as e:
            log.exception("agent %s failed", name)
            self.store.record_run(name, False, 0, repr(e))
            return []
        fresh = []
        for a in alerts:
            if self.store.was_sent(a.agent, a.key, agent.cooldown_s):
                continue
            self.notifier.send(a)
            self.store.record_alert(a)
            fresh.append(a)
        self.store.record_run(name, True, len(fresh))
        log.info("agent %s: %d new alerts (%d raw)", name, len(fresh), len(alerts))
        return fresh

    def tick(self, now: float | None = None) -> None:
        now = now or time.time()
        for name, agent in self.agents.items():
            if now >= self._next_run[name]:
                self.run_agent(name)
                self._next_run[name] = now + agent.interval_s
        self._maybe_digest(now)

    def _maybe_digest(self, now: float) -> None:
        hour = self.cfg.get("daily_digest_hour")
        if hour is None:
            return
        today = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        if datetime.fromtimestamp(now).hour >= int(hour) and self.store.get("controller", "digest_day") != today:
            self.send_digest(now)
            self.store.put("controller", "digest_day", today)

    def build_digest(self, now: float | None = None) -> str:
        now = now or time.time()
        since = now - 86400
        alerts = self.store.alerts_since(since)
        runs = self.store.runs_since(since)
        lines = [f"Daily briefing - {datetime.fromtimestamp(now):%a %b %d}", ""]
        for name, agent in self.agents.items():
            mine = [a for a in alerts if a["agent"] == name]
            failed = [r for r in runs if r["agent"] == name and not r["ok"]]
            health = f" ({len(failed)} failed runs - check logs)" if failed else ""
            lines.append(f"{name.upper()}: {len(mine)} updates{health}")
            lines.append(agent.digest_section(mine))
            lines.append("")
        top = [a for a in alerts if a["priority"] >= HIGH][:5]
        if top:
            lines.append("TOP PRIORITIES")
            lines += [f"  - [{PRIORITY_NAMES[a['priority']]}] {a['title']}" for a in top]
        return "\n".join(lines).rstrip()

    def send_digest(self, now: float | None = None) -> str:
        text = self.build_digest(now)
        self.notifier.send_text("Daily briefing", text)
        return text

    def run_forever(self, poll_s: float = 30) -> None:
        log.info("controller started with agents: %s", ", ".join(self.agents) or "(none enabled)")
        while True:
            self.tick()
            time.sleep(poll_s)
