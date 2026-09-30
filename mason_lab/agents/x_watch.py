from __future__ import annotations

import re
from typing import Any

from ..config import env
from ..models import HIGH, URGENT, Alert
from .base import Agent, AgentContext
from .crypto import DEX, describe_pair, score_pair

X_API = "https://api.x.com/2"

EVM_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
# Solana mints are base58, 32-44 chars; require a digit+letter mix so plain words don't match
SOL_RE = re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b")
CASHTAG_RE = re.compile(r"(?<![\w$])\$([A-Za-z][A-Za-z0-9]{1,9})\b")
IGNORE_TAGS = {"BTC", "ETH", "SOL", "USDT", "USDC", "BNB", "XRP", "SPX", "SPY", "QQQ", "USD"}


def extract_tokens(text: str) -> dict[str, list[str]]:
    evm = EVM_RE.findall(text)
    sol = [m for m in SOL_RE.findall(text)
           if any(ch.isdigit() for ch in m) and any(ch.isalpha() for ch in m) and not m.startswith("0x")]
    tags = [t.upper() for t in CASHTAG_RE.findall(text) if t.upper() not in IGNORE_TAGS]
    return {"addresses": list(dict.fromkeys(evm + sol)), "cashtags": list(dict.fromkeys(tags))}


class XWatchAgent(Agent):
    """Watches the X accounts you list and alerts when one posts a coin (contract address or $TICKER),
    with live DexScreener numbers attached so you can judge it in seconds.

    Needs an X API bearer token (X_BEARER_TOKEN); reading timelines requires a paid X API tier.
    """

    name = "x_watch"
    default_interval_min = 2
    default_cooldown_h = 72

    def run(self, ctx: AgentContext) -> list[Alert]:
        token = env("X_BEARER_TOKEN")
        accounts = [a.lstrip("@") for a in (self.cfg.get("accounts") or [])]
        if not token or not accounts:
            return []
        hdr = {"Authorization": f"Bearer {token}"}
        ids = ctx.store.get(self.name, "user_ids", {})
        missing = [a for a in accounts if a.lower() not in ids]
        for i in range(0, len(missing), 100):
            res = self.get_json(ctx.http, f"{X_API}/users/by", headers=hdr,
                                params={"usernames": ",".join(missing[i:i + 100])})
            for u in res.get("data", []):
                ids[u["username"].lower()] = u["id"]
        ctx.store.put(self.name, "user_ids", ids)

        alerts = []
        for handle in accounts:
            uid = ids.get(handle.lower())
            if not uid:
                continue
            since = ctx.store.get(self.name, f"since:{uid}")
            params = {"max_results": 10, "tweet.fields": "created_at", "exclude": "replies"}
            if since:
                params["since_id"] = since
            res = self.get_json(ctx.http, f"{X_API}/users/{uid}/tweets", headers=hdr, params=params)
            tweets = res.get("data", [])
            if tweets:
                ctx.store.put(self.name, f"since:{uid}", max(tweets, key=lambda t: int(t["id"]))["id"])
            if not since:
                continue  # first run just sets the cursor so you don't get flooded with old posts
            for tw in tweets:
                alerts += self._alerts_for_tweet(ctx, handle, tw)
        return alerts

    def _alerts_for_tweet(self, ctx: AgentContext, handle: str, tw: dict) -> list[Alert]:
        found = extract_tokens(tw.get("text", ""))
        queries = found["addresses"] + [f"${t}" for t in found["cashtags"]]
        out = []
        for q in queries[:3]:
            pair = self._lookup(ctx.http, q.lstrip("$"))
            tweet_url = f"https://x.com/{handle}/status/{tw['id']}"
            body = [f"@{handle} posted: \"{tw.get('text', '')[:280]}\"", tweet_url, ""]
            if pair:
                s = score_pair(pair)
                body.append(describe_pair(pair, s))
                prio = URGENT if s["liq"] >= 50_000 and not s["flags"] else HIGH
            else:
                body.append("No DEX pair found yet - could be pre-launch or a CEX coin. Don't ape blind.")
                prio = HIGH
            body.append("Reminder: influencer coin posts are often paid promos; early holders frequently "
                        "sell into the follower rush. Size small, use a stop.")
            out.append(Alert(agent=self.name, key=f"{tw['id']}:{q}", title=f"@{handle} posted {q[:12]}",
                             body="\n".join(body), priority=prio, url=pair.get("url") if pair else tweet_url,
                             data={"handle": handle, "query": q}))
        return out

    def _lookup(self, http: Any, q: str) -> dict | None:
        try:
            pairs = self.get_json(http, f"{DEX}/latest/dex/search", params={"q": q}).get("pairs") or []
        except Exception:
            return None
        if not q.startswith("0x") and len(q) < 30:  # ticker: only accept exact symbol matches
            pairs = [p for p in pairs if p.get("baseToken", {}).get("symbol", "").upper() == q.upper()]
        return max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0, default=None)

    def digest_section(self, alerts: list[dict]) -> str:
        if not alerts:
            return "  none of your watched accounts posted a coin"
        return "\n".join(f"  - @{a['data']['handle']}: {a['data']['query']}" for a in alerts[:10])
