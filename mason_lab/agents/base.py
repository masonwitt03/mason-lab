from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from ..models import Alert
from ..store import Store


@dataclass
class AgentContext:
    store: Store
    http: Any
    dry_run: bool = False


class Agent:
    """Every agent does one job and returns Alerts; the controller decides what gets sent."""

    name = "agent"
    default_interval_min = 60
    default_cooldown_h = 24.0

    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg or {}

    @property
    def interval_s(self) -> float:
        return float(self.cfg.get("interval_minutes", self.default_interval_min)) * 60

    @property
    def cooldown_s(self) -> float:
        return float(self.cfg.get("alert_cooldown_hours", self.default_cooldown_h)) * 3600

    def run(self, ctx: AgentContext) -> list[Alert]:
        raise NotImplementedError

    def digest_section(self, alerts: list[dict]) -> str:
        """Summarize the last day's alerts from this agent for the daily briefing."""
        if not alerts:
            return "  nothing new"
        return "\n".join(f"  - {a['title']}" for a in alerts[:10])

    @staticmethod
    def get_json(http: Any, url: str, **kw) -> Any:
        kw.setdefault("timeout", 20)
        r = http.get(url, **kw)
        r.raise_for_status()
        return r.json()


def default_http() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "mason-lab/0.1"
    return s
