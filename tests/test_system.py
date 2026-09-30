import time


from mason_lab.agents.base import Agent, AgentContext
from mason_lab.agents.clipper import ClipperAgent, caption_for, pick_clips
from mason_lab.agents.crypto import CryptoAgent, score_pair, trade_plan
from mason_lab.agents.etsy import EtsyAgent, analyze_niche, draft_listing
from mason_lab.agents.x_watch import XWatchAgent, extract_tokens
from mason_lab.models import HIGH, NORMAL, Alert
from mason_lab.notify import Notifier
from mason_lab.orchestrator import Controller
from mason_lab.store import Store

from fakes import FakeHTTP

NOW_MS = time.time() * 1000


def pair(addr="Mint1111", sym="PUMP", **over):
    p = {
        "chainId": "solana", "dexId": "raydium", "url": f"https://dexscreener.com/solana/{addr}",
        "baseToken": {"address": addr, "name": "Pump", "symbol": sym}, "priceUsd": "0.0012",
        "priceChange": {"m5": 12, "h1": 80, "h6": 150}, "volume": {"h1": 300_000, "h6": 600_000, "h24": 900_000},
        "txns": {"h1": {"buys": 900, "sells": 300}}, "liquidity": {"usd": 150_000}, "marketCap": 1_200_000,
        "pairCreatedAt": NOW_MS - 10 * 3.6e6,
    }
    p.update(over)
    return p


# --- crypto -----------------------------------------------------------------------------------
def test_momentum_score_rewards_pumps_and_flags_risk():
    hot = score_pair(pair())
    dead = score_pair(pair(priceChange={"m5": -5, "h1": -20, "h6": -40}, txns={"h1": {"buys": 100, "sells": 400}},
                           volume={"h1": 5_000, "h6": 60_000, "h24": 100_000}))
    assert hot["score"] > 60 > dead["score"]
    assert hot["flags"] == []
    risky = score_pair(pair(liquidity={"usd": 5_000}, pairCreatedAt=NOW_MS - 0.2 * 3.6e6))
    assert any("liquidity" in f for f in risky["flags"]) and any("min old" in f for f in risky["flags"])


def test_trade_plan_halves_size_with_red_flags():
    clean = trade_plan(1.0, 1000, 2, 25, [])
    flagged = trade_plan(1.0, 1000, 2, 25, ["x"])
    assert "Max size $80 " in clean and "Max size $40 " in flagged


def test_crypto_agent_end_to_end():
    http = FakeHTTP({
        r"token-boosts/top": [{"chainId": "solana", "tokenAddress": "Mint1111", "totalAmount": 500}],
        r"token-boosts/latest": [{"chainId": "solana", "tokenAddress": "Mint2222", "amount": 10}],
        r"token-profiles": [],
        r"tokens/v1/solana/": [pair(), pair("Mint2222", "DUD", priceChange={"m5": 0, "h1": 1, "h6": 2},
                                           txns={"h1": {"buys": 50, "sells": 60}})],
        r"rugcheck": {"risks": [{"name": "Mint authority enabled", "level": "danger"}]},
        r"coingecko": {"coins": []},
    })
    agent = CryptoAgent({"min_score": 55})
    alerts = agent.run(AgentContext(store=Store(":memory:"), http=http))
    assert [a.data["symbol"] for a in alerts] == ["PUMP"]
    assert "RugCheck danger: Mint authority enabled" in alerts[0].body
    assert "Max size" in alerts[0].body


# --- X watch ----------------------------------------------------------------------------------
def test_extract_tokens():
    t = ("just aped $BONKER and $BTC lol CA: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU "
         "also 0x6982508145454Ce325dDbE47a25d4ec3d2311933 buy the dip")
    f = extract_tokens(t)
    assert f["cashtags"] == ["BONKER"]
    assert "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU" in f["addresses"]
    assert "0x6982508145454Ce325dDbE47a25d4ec3d2311933" in f["addresses"]
    assert extract_tokens("gm everyone, great day")["addresses"] == []


def test_x_watch_skips_backlog_then_alerts(monkeypatch):
    monkeypatch.setenv("X_BEARER_TOKEN", "t")
    tweets = {"data": [{"id": "100", "text": "old post $OLDCOIN"}]}
    http = FakeHTTP({
        r"users/by": {"data": [{"id": "42", "username": "whale"}]},
        r"users/42/tweets": lambda url, kw: __import__("fakes").Resp(tweets),
        r"dex/search": {"pairs": [pair(sym="NEWCOIN")]},
    })
    ctx = AgentContext(store=Store(":memory:"), http=http)
    agent = XWatchAgent({"accounts": ["@whale"]})
    assert agent.run(ctx) == []  # first run only sets the cursor
    tweets["data"] = [{"id": "101", "text": "this one is going to 1B $NEWCOIN"}]
    alerts = agent.run(ctx)
    assert len(alerts) == 1 and alerts[0].title == "@whale posted $NEWCOIN"
    assert "x.com/whale/status/101" in alerts[0].body


# --- Etsy -------------------------------------------------------------------------------------
def listing(favs, days_old, price_cents, tags):
    return {"num_favorers": favs, "original_creation_timestamp": time.time() - days_old * 86400,
            "price": {"amount": price_cents, "divisor": 100}, "tags": tags}


def test_niche_analysis_and_draft_fit_etsy_limits():
    ls = [listing(300, 30, 1500 + i * 100, ["digital planner", "goodnotes planner", "ipad planner",
                                             "2027 planner", "disney planner"]) for i in range(8)]
    n = analyze_niche("digital planner", ls, 50_000)
    assert n["demand_fav_per_day"] == 10 and n["median_price"] == 18.5
    assert "disney planner" not in n["top_tags"]  # IP-risky tags stripped
    d = draft_listing(n)
    assert len(d["title"]) <= 140 and len(d["tags"]) <= 13 and all(len(t) <= 20 for t in d["tags"])
    assert d["suggested_price"] < n["price_p75"]
    assert analyze_niche("disney shirt", ls, 10)["ip_risk"]


def test_etsy_agent_ranks_and_detects_spike(monkeypatch):
    monkeypatch.setenv("ETSY_API_KEY", "k:s")
    favs = {"stickers": 50, "svg bundle": 500}

    def route(url, kw):
        from fakes import Resp
        kw_ = kw["params"]["keywords"]
        return Resp({"count": 1000, "results": [listing(favs[kw_], 50, 500, [kw_])] * 5})

    http = FakeHTTP({r"listings/active": route})
    ctx = AgentContext(store=Store(":memory:"), http=http)
    agent = EtsyAgent({"seed_keywords": ["stickers", "svg bundle"]})
    first = agent.run(ctx)
    assert first[0].data["niches"][0]["keyword"] == "svg bundle"
    favs["stickers"] = 200
    second = agent.run(ctx)
    assert any(a.title == "Etsy demand spike: stickers" for a in second)


# --- clipper ----------------------------------------------------------------------------------
def clip(i, views, dur=30):
    return {"id": f"c{i}", "view_count": views, "duration": dur, "title": f"insane play {i}",
            "url": f"https://clips.twitch.tv/c{i}", "broadcaster_name": "Streamer"}


def test_pick_clips_filters_and_sorts():
    clips = [clip(1, 100), clip(2, 9000), clip(3, 5000, dur=90), clip(4, 3000), clip(5, 8000)]
    picked = pick_clips(clips, already={"c5"}, min_views=500, max_n=2)
    assert [c["id"] for c in picked] == ["c2", "c4"]
    title, desc, tags = caption_for(clip(2, 9000), {"login": "streamer"})
    assert "twitch.tv/streamer" in desc and "clips.twitch.tv/c2" in desc and len(title) <= 100


def test_clipper_only_clips_permitted_streamers(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "id")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "secret")
    http = FakeHTTP({
        r"oauth2/token": {"access_token": "tok", "expires_in": 3600},
        r"helix/streams": {"data": [{"user_login": "bigguy", "user_name": "BigGuy", "game_name": "GTA V",
                                     "viewer_count": 50000}]},
        r"helix/users": {"data": [{"login": "okstreamer", "id": "1"}]},
        r"helix/clips": {"data": [clip(1, 6000)]},
    })
    agent = ClipperAgent({"streamers": [{"login": "okstreamer", "permission": True},
                                        {"login": "noperm", "permission": False}]})
    ctx = AgentContext(store=Store(":memory:"), http=http, dry_run=True)
    alerts = agent.run(ctx)
    keys = {a.key.split(":")[0] for a in alerts}
    assert keys == {"scout", "clip"}
    user_call = next(c for c in http.calls if "helix/users" in c[1])
    assert user_call[2]["params"] == [("login", "okstreamer")]
    assert agent.run(ctx) == [a for a in agent.run(ctx) if a.key.startswith("scout")]  # clip not reposted


# --- controller -------------------------------------------------------------------------------
class Echo(Agent):
    name = "echo"

    def __init__(self, alerts, boom=False):
        super().__init__({"interval_minutes": 10})
        self.alerts, self.boom, self.runs = alerts, boom, 0

    def run(self, ctx):
        self.runs += 1
        if self.boom:
            raise RuntimeError("api down")
        return self.alerts


class Capture(Notifier):
    def __init__(self):
        super().__init__({})
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)


def test_controller_dedupes_schedules_and_survives_failures():
    a = Alert("echo", "k1", "Hot thing", "body", HIGH)
    good, bad = Echo([a]), Echo([], boom=True)
    note = Capture()
    ctl = Controller({"daily_digest_hour": None}, store=Store(":memory:"), notifier=note, http=FakeHTTP({}),
                     agents={"echo": good, "bad": bad})
    ctl.tick(now=1000)
    ctl.tick(now=1100)          # before interval: no rerun
    assert good.runs == 1 and bad.runs == 1
    ctl.tick(now=1000 + 601)    # rerun, but same key is deduped
    assert good.runs == 2 and [x.key for x in note.sent] == ["k1"]
    digest = ctl.build_digest()
    assert "ECHO: 1 updates" in digest and "BAD: 0 updates (2 failed runs" in digest and "TOP PRIORITIES" in digest


def test_notifier_respects_min_priority():
    http = FakeHTTP({r"ntfy": {}})
    n = Notifier({"ntfy": {"enabled": True, "topic": "t", "min_priority": HIGH}}, http)
    n.send(Alert("x", "1", "meh", "b", NORMAL))
    n.send(Alert("x", "2", "big", "b", HIGH, url="https://e.x"))
    assert len(http.calls) == 1 and http.calls[0][2]["headers"]["Click"] == "https://e.x"
