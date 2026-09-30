from __future__ import annotations

import logging
from typing import Any

import requests

from .config import env
from .models import HIGH, LOW, NORMAL, URGENT, Alert

log = logging.getLogger(__name__)

NTFY_PRIORITY = {LOW: "2", NORMAL: "3", HIGH: "4", URGENT: "5"}


class Notifier:
    """Fans every alert out to the channels you enabled (phone push, Discord, Telegram, console).

    `min_priority` per channel lets you get only the important stuff on your phone while
    Discord keeps the full feed.
    """

    def __init__(self, cfg: dict[str, Any], http: Any = None):
        self.cfg = cfg or {}
        self.http = http or requests.Session()

    def send(self, alert: Alert) -> None:
        for channel, ccfg in self.cfg.items():
            ccfg = ccfg or {}
            if not ccfg.get("enabled", False) or alert.priority < ccfg.get("min_priority", LOW):
                continue
            try:
                getattr(self, f"_send_{channel}")(alert, ccfg)
            except Exception as e:  # one broken channel must not stop the others
                log.warning("notify via %s failed: %s", channel, e)

    def send_text(self, title: str, body: str, priority: int = NORMAL) -> None:
        self.send(Alert(agent="controller", key=title, title=title, body=body, priority=priority))

    def _send_console(self, alert: Alert, ccfg: dict) -> None:
        print("\n" + "=" * 60 + "\n" + alert.as_text() + "\n" + "=" * 60, flush=True)

    def _send_ntfy(self, alert: Alert, ccfg: dict) -> None:
        topic = env("NTFY_TOPIC") or ccfg.get("topic")
        if not topic:
            raise ValueError("NTFY_TOPIC not set")
        server = ccfg.get("server", "https://ntfy.sh").rstrip("/")
        headers = {"Title": alert.title[:250].encode("utf-8"), "Priority": NTFY_PRIORITY[alert.priority],
                   "Tags": alert.agent}
        if alert.url:
            headers["Click"] = alert.url
        self.http.post(f"{server}/{topic}", data=alert.body.encode("utf-8"), headers=headers, timeout=15)

    def _send_discord(self, alert: Alert, ccfg: dict) -> None:
        url = env("DISCORD_WEBHOOK_URL")
        if not url:
            raise ValueError("DISCORD_WEBHOOK_URL not set")
        self.http.post(url, json={"content": alert.as_text()[:1990]}, timeout=15)

    def _send_telegram(self, alert: Alert, ccfg: dict) -> None:
        token, chat = env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID")
        if not (token and chat):
            raise ValueError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set")
        self.http.post(f"https://api.telegram.org/bot{token}/sendMessage",
                       json={"chat_id": chat, "text": alert.as_text()[:4000],
                             "disable_web_page_preview": True}, timeout=15)
