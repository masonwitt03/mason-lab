from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LOW, NORMAL, HIGH, URGENT = 1, 2, 3, 4
PRIORITY_NAMES = {LOW: "low", NORMAL: "normal", HIGH: "high", URGENT: "urgent"}


@dataclass
class Alert:
    """One update an agent wants to send you.

    `key` identifies the underlying event so the controller never sends the same thing twice
    (within the agent's cooldown window).
    """

    agent: str
    key: str
    title: str
    body: str
    priority: int = NORMAL
    url: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def as_text(self) -> str:
        lines = [f"[{self.agent}] {self.title}", self.body]
        if self.url:
            lines.append(self.url)
        return "\n".join(line for line in lines if line)
