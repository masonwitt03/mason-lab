from datetime import datetime

from mason_lab.agents.base import AgentContext
from mason_lab.agents.vintage import VintageAgent
from mason_lab.store import Store
from mason_lab.vintage import Inventory, listing_copy, parse_note, profit, stale_actions, stats, suggest_price

DAY = 86400


def test_parse_note_pulls_out_the_details():
    i = parse_note("90s Champion Michigan State tee, L, small stain")
    assert (i.school, i.brand, i.decade, i.size, i.kind, i.flaws) == \
        ("Michigan State", "Champion", "90s", "L", "T-Shirt", ["stain"])
    j = parse_note("80s single stitch Notre Dame national champions Velva Sheen crewneck XL")
    assert j.single_stitch and j.event == "National Champions" and j.kind == "Crewneck Sweatshirt"
    assert parse_note("xxl texas a&m tee").size == "2XL"
    assert parse_note("usc tee", school="UCLA", size="M").school == "UCLA"


def test_listing_copy_fits_platform_limits():
    c = listing_copy(parse_note("80s single stitch Notre Dame national champions Velva Sheen tee XL"))
    assert c["title"].startswith("Vintage 80s Notre Dame Fighting Irish")
    assert len(c["ebay_title"]) <= 80 and "Notre Dame" in c["ebay_title"]
    assert len(c["hashtags"]) <= 5 and len(c["depop_description"]) <= 1000
    assert len(c["etsy_tags"]) <= 13 and all(len(t) <= 20 for t in c["etsy_tags"])
    assert "not a reproduction" in c["depop_description"]


def test_pricing_rewards_value_signals_and_penalizes_flaws():
    plain = suggest_price(parse_note("michigan tee"))
    premium = suggest_price(parse_note("80s single stitch champion michigan rose bowl tee"))
    flawed = suggest_price(parse_note("michigan tee stain hole"))
    assert flawed < plain < premium


def test_inventory_sales_profit_and_rankings():
    inv = Inventory(Store(":memory:").db)
    t0 = 1_700_000_000
    for note, cost, sale, days in [("90s michigan champion tee L", 4, 35, 3), ("90s michigan starter tee M", 5, 40, 5),
                                   ("ohio state tee L", 3, 15, 30), ("ohio state crewneck", 6, 25, 20),
                                   ("duke tee", 4, None, 0)]:
        item = inv.add(parse_note(note, cost=cost), now=t0)
        if sale:
            inv.sell(item.id, sale, "depop", shipping=0, now=t0 + days * DAY)
    sold = inv.get(1)
    assert sold.fees == round(35 * 0.033 + 0.45, 2) and profit(sold) == round(35 - sold.fees - 4, 2)
    s = stats(inv.all())
    assert s["sold"] == 4 and s["active"] == 1 and s["sell_through"] == 80.0
    assert [r["name"] for r in s["by"]["school"]] == ["Michigan", "Ohio State"]
    assert s["by"]["school"][0]["avg_days"] == 4.0


def test_stale_pieces_get_markdown_advice():
    inv = Inventory(Store(":memory:").db)
    now = 1_700_000_000
    fresh = inv.add(parse_note("duke tee", cost=4, price=30), now=now - 5 * DAY)
    stale = inv.add(parse_note("unc tee", cost=4, price=40), now=now - 25 * DAY)
    dead = inv.add(parse_note("uconn tee", cost=4, price=40), now=now - 60 * DAY)
    acts = {i.id: (stage, advice) for i, stage, advice in stale_actions(inv.all(), now, 21, 45, 15)}
    assert fresh.id not in acts
    assert acts[stale.id][0] == "stale" and "$33.99" in acts[stale.id][1]
    assert acts[dead.id][0] == "dead" and "$28" in acts[dead.id][1]


def test_vintage_agent_weekly_report_and_stale_alert():
    store = Store(":memory:")
    inv = Inventory(store.db)
    sunday = datetime(2026, 10, 4, 12).timestamp()
    a = inv.add(parse_note("michigan tee", cost=4), now=sunday - 30 * DAY)
    b = inv.add(parse_note("michigan crewneck", cost=5), now=sunday - 10 * DAY)
    inv.sell(b.id, 45, "ebay", now=sunday - DAY)
    alerts = VintageAgent({}).run(AgentContext(store=store, http=None), now=sunday)
    titles = {x.title: x for x in alerts}
    assert "Vintage: 1 pieces need a price cut" in titles and f"#{a.id}" in titles[
        "Vintage: 1 pieces need a price cut"].body
    report = titles["Vintage weekly report"].body
    assert "Profit $" in report and "sweatshirt weather" in report
    saturday = VintageAgent({}).run(AgentContext(store=store, http=None), now=sunday - DAY)
    assert [x.title for x in saturday] == ["Vintage: 1 pieces need a price cut"]  # no report on Saturday
