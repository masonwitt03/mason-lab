from __future__ import annotations

import math
import re
import statistics
import time
from collections import Counter
from typing import Any

from ..config import env
from ..models import HIGH, NORMAL, Alert
from .base import Agent, AgentContext

ETSY = "https://openapi.etsy.com/v3/application"

# Products that tend to sell well on Etsy AND can be made/fulfilled without inventory (digital or POD).
DEFAULT_SEEDS = [
    "digital planner", "wedding invitation template", "custom pet portrait", "personalized necklace",
    "svg bundle", "printable wall art", "custom embroidered sweatshirt", "budget spreadsheet",
    "teacher gift", "bachelorette shirts", "canva template", "stickers", "halloween shirt",
    "christmas ornament personalized", "baby milestone blanket", "resume template",
]

# Terms that are almost always trademark/IP violations - Etsy will take these down and can close your shop.
IP_RISK = re.compile(r"\b(disney|marvel|nike|taylor swift|swiftie|pokemon|harry potter|stanley|"
                     r"barbie|star wars|nfl|nba|bluey|hello kitty|louis vuitton|chanel|gucci)\b", re.I)


def price_usd(listing: dict) -> float:
    p = listing.get("price") or {}
    return (p.get("amount") or 0) / (p.get("divisor") or 100)


def analyze_niche(keyword: str, listings: list[dict], total_count: int, now: float | None = None) -> dict[str, Any]:
    """Demand vs competition for one search term.

    Demand = favorites per day on the top-ranked listings (Etsy doesn't expose sales; favorites
    track sales closely). Competition = total active listings for the term.
    """
    now = now or time.time()
    fav_rates, prices, tags = [], [], Counter()
    for l in listings:
        age_days = max((now - (l.get("original_creation_timestamp") or now)) / 86400, 7)
        fav_rates.append((l.get("num_favorers") or 0) / age_days)
        if price_usd(l):
            prices.append(price_usd(l))
        tags.update(t.lower() for t in l.get("tags") or [])
    demand = statistics.median(fav_rates) if fav_rates else 0.0
    competition = max(total_count, 1)
    opportunity = demand * 100 / math.log10(competition + 10)
    return {
        "keyword": keyword,
        "demand_fav_per_day": round(demand, 2),
        "competition": total_count,
        "opportunity": round(opportunity, 1),
        "median_price": round(statistics.median(prices), 2) if prices else None,
        "price_p75": round(statistics.quantiles(prices, n=4)[2], 2) if len(prices) >= 4 else None,
        "top_tags": [t for t, _ in tags.most_common(20) if not IP_RISK.search(t)],
        "ip_risk": bool(IP_RISK.search(keyword)),
    }


def draft_listing(niche: dict) -> dict[str, Any]:
    """A ready-to-edit listing that fits Etsy's limits (title <=140 chars, 13 tags <=20 chars)."""
    kw = niche["keyword"]
    tags = []
    for t in [kw] + niche["top_tags"]:
        t = t[:20].strip()
        if t and t not in tags:
            tags.append(t)
        if len(tags) == 13:
            break
    extras = [t.title() for t in tags[1:5]]
    title = kw.title()
    for e in extras:
        if len(title) + len(e) + 3 > 140:
            break
        title += f" | {e}"
    # price just under the 75th percentile: premium positioning without being the most expensive
    target = niche.get("price_p75") or niche.get("median_price")
    price = round(target * 0.95, 2) if target else None
    return {"title": title, "tags": tags, "suggested_price": price}


class EtsyAgent(Agent):
    """Finds Etsy niches with high demand and beatable competition, and drafts listings for them.

    Uses the official Etsy Open API v3 (read-only, needs ETSY_API_KEY). It doesn't auto-publish:
    you review each draft, add your own photos/mockups, and post it - that keeps the shop safe.
    """

    name = "etsy"
    default_interval_min = 24 * 60
    default_cooldown_h = 24 * 7

    def run(self, ctx: AgentContext) -> list[Alert]:
        key = env("ETSY_API_KEY")
        if not key:
            return []
        hdr = {"x-api-key": key}
        niches = []
        for kw in self.cfg.get("seed_keywords", DEFAULT_SEEDS):
            res = self.get_json(ctx.http, f"{ETSY}/listings/active", headers=hdr,
                                params={"keywords": kw, "limit": 100, "sort_on": "score"})
            niches.append(analyze_niche(kw, res.get("results", []), res.get("count", 0)))

        niches = [n for n in niches if not n["ip_risk"]]
        niches.sort(key=lambda n: n["opportunity"], reverse=True)
        prev = {n["keyword"]: n for n in ctx.store.get(self.name, "last_niches", [])}
        ctx.store.put(self.name, "last_niches", niches)

        alerts = []
        week = time.strftime("%Y-W%W")
        top = niches[: int(self.cfg.get("top_n", 5))]
        if top:
            lines = []
            for i, n in enumerate(top, 1):
                d = draft_listing(n)
                trend = ""
                if n["keyword"] in prev and prev[n["keyword"]]["demand_fav_per_day"]:
                    pct = (n["demand_fav_per_day"] / prev[n["keyword"]]["demand_fav_per_day"] - 1) * 100
                    trend = f" ({pct:+.0f}% demand vs last scan)"
                lines += [
                    f"{i}. {n['keyword']} - opportunity {n['opportunity']}{trend}",
                    f"   demand {n['demand_fav_per_day']} fav/day | {n['competition']:,} competing listings"
                    f" | median ${n['median_price']}",
                    f"   Draft title: {d['title']}",
                    f"   Tags: {', '.join(d['tags'])}",
                    f"   Price at: ${d['suggested_price']}",
                ]
            alerts.append(Alert(agent=self.name, key=f"report:{week}", title="Etsy: best niches to list this week",
                                body="\n".join(lines), priority=HIGH, data={"niches": top}))

        for n in niches:  # sudden demand spikes are worth jumping on before competition catches up
            p = prev.get(n["keyword"])
            if p and p["demand_fav_per_day"] and n["demand_fav_per_day"] >= 1.5 * p["demand_fav_per_day"]:
                alerts.append(Alert(agent=self.name, key=f"spike:{n['keyword']}:{week}",
                                    title=f"Etsy demand spike: {n['keyword']}",
                                    body=f"Demand up {n['demand_fav_per_day'] / p['demand_fav_per_day']:.1f}x since "
                                         f"last scan. List something in this niche in the next few days.",
                                    priority=NORMAL, data={"keyword": n["keyword"]}))
        return alerts

    def digest_section(self, alerts: list[dict]) -> str:
        for a in alerts:
            if a["key"].startswith("report:"):
                return "\n".join(f"  - {n['keyword']} (opp {n['opportunity']}, ${n['median_price']})"
                                 for n in a["data"]["niches"])
        return "  no new niche report today (weekly)"
