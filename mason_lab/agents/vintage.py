from __future__ import annotations

import time
from datetime import datetime

from ..models import HIGH, LOW, NORMAL, Alert
from ..vintage import SEASONS, Inventory, stale_actions, stats
from .base import Agent, AgentContext


def format_report(s: dict, month: int) -> str:
    lines = [
        f"Profit ${s['profit']:,.2f} on {s['sold']} sales (revenue ${s['revenue']:,.2f}, ROI {s['roi']}%)"
        if s["sold"] else "No sales logged yet.",
        f"Sell-through {s['sell_through']}% | avg {s['avg_days_to_sell']} days to sell"
        if s["sold"] else "",
        f"{s['active']} listed, worth ${s['inventory_value']:,.2f} at ask (cost ${s['inventory_cost']:,.2f})",
    ]
    labels = {"school": "Schools", "brand": "Brands", "decade": "Decades", "kind": "Types", "platform": "Platforms"}
    for attr, label in labels.items():
        rows = s["by"].get(attr) or []
        if rows:
            lines.append(f"{label} (best profit/piece): " + ", ".join(
                f"{r['name']} ${r['avg_profit']:.0f} in {r['avg_days']:.0f}d (x{r['n']})" for r in rows[:4]))
    best = [r["name"] for attr in ("school", "brand", "decade") for r in (s["by"].get(attr) or [])[:1]]
    if best:
        lines.append("BUY MORE OF: " + ", ".join(best))
    if month in SEASONS:
        lines.append("Season: " + SEASONS[month])
    return "\n".join(l for l in lines if l)


class VintageAgent(Agent):
    """Watches your vintage inventory: flags pieces that aren't moving (with the exact markdown to make),
    and sends a weekly report on what earns the most so you know what to buy next.

    You log buys and sales with `python -m mason_lab vintage ...`; Depop has no public API.
    """

    name = "vintage"
    default_interval_min = 24 * 60
    default_cooldown_h = 24 * 365

    def run(self, ctx: AgentContext, now: float | None = None) -> list[Alert]:
        now = now or time.time()
        inv = Inventory(ctx.store.db)
        items = inv.all()
        if not items:
            return []
        alerts = []
        actions = stale_actions(items, now, int(self.cfg.get("stale_days", 21)),
                                int(self.cfg.get("dead_days", 45)), float(self.cfg.get("markdown_pct", 15)))
        if actions:
            body = "\n".join(f"#{i.id} {i.school or ''} {i.kind} (${i.price:.2f}): {advice}".replace("  ", " ")
                             for i, _, advice in actions)
            key = "stale:" + ",".join(f"{i.id}{stage[0]}" for i, stage, _ in actions)
            alerts.append(Alert(agent=self.name, key=key, title=f"Vintage: {len(actions)} pieces need a price cut",
                                body=body + "\n\nUpdate prices with: python -m mason_lab vintage price <id> <new>",
                                priority=NORMAL, data={"ids": [i.id for i, _, _ in actions]}))

        dt = datetime.fromtimestamp(now)
        if dt.weekday() == int(self.cfg.get("report_weekday", 6)):  # default Sunday
            s = stats(items, int(self.cfg.get("min_sales_for_ranking", 2)))
            alerts.append(Alert(agent=self.name, key=f"report:{dt:%Y-%W}", title="Vintage weekly report",
                                body=format_report(s, dt.month), priority=HIGH if s["sold"] else LOW,
                                data={"profit": s["profit"], "sold": s["sold"]}))
        return alerts

    def digest_section(self, alerts: list[dict]) -> str:
        if not alerts:
            return "  nothing needs attention"
        return "\n".join(f"  - {a['title']}" for a in alerts)
