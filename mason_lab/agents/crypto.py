from __future__ import annotations

import math
import time
from typing import Any

from ..models import HIGH, NORMAL, URGENT, Alert
from .base import Agent, AgentContext

DEX = "https://api.dexscreener.com"
RUGCHECK = "https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
COINGECKO_TRENDING = "https://api.coingecko.com/api/v3/search/trending"


def _f(d: dict | None, *path: str, default: float = 0.0) -> float:
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
    try:
        return float(d) if d is not None else default
    except (TypeError, ValueError):
        return default


def score_pair(pair: dict, boosts: float = 0.0) -> dict[str, Any]:
    """Momentum score (0-100) plus a list of red flags for one DexScreener pair.

    Momentum = short-term price moves + volume acceleration + buy pressure.
    Red flags = things that make a pump likely to be a rug or an exit for early holders.
    """
    ch_m5, ch_h1, ch_h6 = (_f(pair, "priceChange", k) for k in ("m5", "h1", "h6"))
    vol_h1, vol_h6, vol_h24 = (_f(pair, "volume", k) for k in ("h1", "h6", "h24"))
    buys_h1, sells_h1 = _f(pair, "txns", "h1", "buys"), _f(pair, "txns", "h1", "sells")
    liq = _f(pair, "liquidity", "usd")
    mcap = _f(pair, "marketCap") or _f(pair, "fdv")
    created_ms = pair.get("pairCreatedAt") or 0
    age_h = (time.time() * 1000 - created_ms) / 3.6e6 if created_ms else None

    # volume in the last hour vs the average hour of the last 6h: >1 means it's accelerating
    accel = vol_h1 / (vol_h6 / 6) if vol_h6 > 0 else 0.0
    buy_ratio = buys_h1 / max(buys_h1 + sells_h1, 1)

    score = 0.0
    score += max(min(ch_m5, 30), -30) * 0.6           # up to 18
    score += max(min(ch_h1, 100), -50) * 0.25         # up to 25
    score += min(accel, 5) * 5                        # up to 25
    score += (buy_ratio - 0.5) * 60                   # up to 30
    score += min(math.log10(vol_h1 + 1), 6)           # up to 6 - prefer real volume
    score += min(boosts / 100, 5)                     # paid DexScreener boosts: small weight, it's marketing
    score = max(0.0, min(100.0, score))

    flags = []
    if liq < 20_000:
        flags.append(f"thin liquidity ${liq:,.0f}")
    if mcap and liq and mcap / liq > 30:
        flags.append(f"mcap/liquidity {mcap / liq:.0f}x - price is easy to dump")
    if age_h is not None and age_h < 1:
        flags.append(f"pair is {age_h * 60:.0f} min old")
    if buys_h1 + sells_h1 < 50:
        flags.append("very few trades")
    if ch_h6 > 500:
        flags.append(f"already +{ch_h6:.0f}% in 6h - late entry risk")
    if vol_h24 and liq and vol_h24 / liq > 50:
        flags.append("volume/liquidity extreme - possible wash trading")

    return {
        "score": round(score, 1), "flags": flags, "liq": liq, "mcap": mcap, "age_h": age_h,
        "ch_m5": ch_m5, "ch_h1": ch_h1, "ch_h6": ch_h6, "vol_h1": vol_h1, "accel": round(accel, 2),
        "buy_ratio": round(buy_ratio, 2),
    }


def trade_plan(price: float, bankroll: float, risk_pct: float, stop_pct: float, flags: list[str]) -> str:
    """Position sizing so a single bad coin can't wipe you out. Halve size when there are red flags."""
    risk_amt = bankroll * risk_pct / 100 / (2 if flags else 1)
    size = risk_amt / (stop_pct / 100)
    return (f"Max size ${size:,.0f} (risking ${risk_amt:,.0f}) | stop -{stop_pct:.0f}% @ {price * (1 - stop_pct / 100):.8g}"
            f" | take 1/2 at +100% @ {price * 2:.8g}, trail the rest")


def describe_pair(pair: dict, s: dict) -> str:
    base = pair.get("baseToken", {})
    lines = [
        f"{base.get('name', '?')} (${base.get('symbol', '?')}) on {pair.get('chainId')}/{pair.get('dexId')}",
        f"Price ${_f(pair, 'priceUsd'):.8g} | 5m {s['ch_m5']:+.1f}% | 1h {s['ch_h1']:+.1f}% | 6h {s['ch_h6']:+.1f}%",
        f"MC ${s['mcap']:,.0f} | Liq ${s['liq']:,.0f} | Vol 1h ${s['vol_h1']:,.0f} (x{s['accel']} accel)"
        f" | buys {s['buy_ratio'] * 100:.0f}%",
        f"CA: {base.get('address', '?')}",
    ]
    if s["flags"]:
        lines.append("Red flags: " + "; ".join(s["flags"]))
    return "\n".join(lines)


def fetch_pairs(http: Any, chain: str, addresses: list[str]) -> list[dict]:
    """Best (most liquid) pair per token, batched 30 at a time as the API allows."""
    best: dict[str, dict] = {}
    for i in range(0, len(addresses), 30):
        chunk = ",".join(addresses[i:i + 30])
        pairs = Agent.get_json(http, f"{DEX}/tokens/v1/{chain}/{chunk}") or []
        for p in pairs:
            addr = p.get("baseToken", {}).get("address")
            if addr and _f(p, "liquidity", "usd") >= _f(best.get(addr), "liquidity", "usd"):
                best[addr] = p
    return list(best.values())


def rugcheck(http: Any, mint: str) -> dict | None:
    try:
        return Agent.get_json(http, RUGCHECK.format(mint=mint))
    except Exception:
        return None


class CryptoAgent(Agent):
    """Scans DexScreener for tokens that are ripping right now and CoinGecko for trending majors.

    It never trades for you: it sends the coin, the numbers, the red flags and a position size.
    """

    name = "crypto"
    default_interval_min = 5
    default_cooldown_h = 6

    def run(self, ctx: AgentContext) -> list[Alert]:
        c = self.cfg
        chains = set(c.get("chains", ["solana", "base", "ethereum", "bsc"]))
        min_score = float(c.get("min_score", 55))
        min_liq = float(c.get("min_liquidity_usd", 20_000))
        min_vol = float(c.get("min_volume_h1_usd", 25_000))

        candidates: dict[tuple[str, str], float] = {}
        for endpoint in ("/token-boosts/top/v1", "/token-boosts/latest/v1", "/token-profiles/latest/v1"):
            try:
                rows = self.get_json(ctx.http, DEX + endpoint) or []
            except Exception:
                continue
            for r in rows if isinstance(rows, list) else []:
                chain, addr = r.get("chainId"), r.get("tokenAddress")
                if chain in chains and addr:
                    candidates[(chain, addr)] = max(candidates.get((chain, addr), 0.0),
                                                    float(r.get("totalAmount") or r.get("amount") or 0))
        for entry in (c.get("watchlist") or []):  # "chain:address" coins you always want scored
            chain, addr = entry.split(":", 1)
            candidates.setdefault((chain, addr), 0.0)

        by_chain: dict[str, list[str]] = {}
        for chain, addr in candidates:
            by_chain.setdefault(chain, []).append(addr)

        alerts = []
        for chain, addrs in by_chain.items():
            for pair in fetch_pairs(ctx.http, chain, addrs):
                addr = pair["baseToken"]["address"]
                s = score_pair(pair, candidates.get((chain, addr), 0.0))
                if s["score"] < min_score or s["liq"] < min_liq or s["vol_h1"] < min_vol:
                    continue
                if chain == "solana" and c.get("use_rugcheck", True):
                    rc = rugcheck(ctx.http, addr)
                    if rc:
                        danger = [r.get("name") for r in rc.get("risks", []) if r.get("level") == "danger"]
                        if danger:
                            s["flags"].append("RugCheck danger: " + ", ".join(danger))
                if c.get("hide_flagged", False) and s["flags"]:
                    continue
                body = describe_pair(pair, s) + "\n" + trade_plan(
                    _f(pair, "priceUsd"), float(c.get("bankroll_usd", 500)),
                    float(c.get("risk_per_trade_pct", 2)), float(c.get("stop_loss_pct", 30)), s["flags"])
                prio = URGENT if s["score"] >= 80 and not s["flags"] else HIGH if s["score"] >= 65 else NORMAL
                sym = pair["baseToken"].get("symbol", "?")
                alerts.append(Alert(
                    agent=self.name, key=f"{chain}:{addr}",
                    title=f"{'🚀' if not s['flags'] else '⚠️'} ${sym} momentum {s['score']:.0f}/100 "
                          f"({s['ch_h1']:+.0f}% 1h)",
                    body=body, priority=prio, url=pair.get("url"),
                    data={"symbol": sym, "chain": chain, "address": addr, **s}))

        if c.get("coingecko_trending", True):
            alerts += self._trending(ctx)
        alerts.sort(key=lambda a: a.data.get("score", 0), reverse=True)
        return alerts[: int(c.get("max_alerts_per_run", 5))]

    def _trending(self, ctx: AgentContext) -> list[Alert]:
        try:
            data = self.get_json(ctx.http, COINGECKO_TRENDING)
        except Exception:
            return []
        items = [c["item"] for c in data.get("coins", [])]
        if not items:
            return []
        lines = []
        for it in items[:7]:
            ch = _f(it, "data", "price_change_percentage_24h", "usd")
            lines.append(f"{it.get('name')} (${it.get('symbol')}) rank #{it.get('market_cap_rank') or '-'}"
                         f" 24h {ch:+.1f}%")
        key = "trending:" + ",".join(sorted(it.get("id", "") for it in items[:7]))
        return [Alert(agent=self.name, key=key, title="CoinGecko trending list changed",
                      body="\n".join(lines), priority=NORMAL, data={"score": 0})]

    def digest_section(self, alerts: list[dict]) -> str:
        hits = [a for a in alerts if a["data"].get("symbol")]
        if not hits:
            return "  no momentum coins passed your filters"
        best = sorted(hits, key=lambda a: a["data"].get("score", 0), reverse=True)[:5]
        return "\n".join(f"  - ${a['data']['symbol']} ({a['data']['chain']}) score {a['data']['score']:.0f}, "
                         f"{len(a['data'].get('flags', []))} red flags" for a in best)
