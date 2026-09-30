"""Vintage reselling: inventory, profit tracking, and listing copy for Depop / eBay / Etsy."""
from __future__ import annotations

import re
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# school -> mascot. Mascot goes in titles because buyers search both.
SCHOOLS = {
    "alabama": "Crimson Tide", "arizona": "Wildcats", "arizona state": "Sun Devils", "arkansas": "Razorbacks",
    "auburn": "Tigers", "baylor": "Bears", "boston college": "Eagles", "byu": "Cougars", "clemson": "Tigers",
    "colorado": "Buffaloes", "duke": "Blue Devils", "florida": "Gators", "florida state": "Seminoles",
    "georgetown": "Hoyas", "georgia": "Bulldogs", "georgia tech": "Yellow Jackets", "gonzaga": "Bulldogs",
    "illinois": "Fighting Illini", "indiana": "Hoosiers", "iowa": "Hawkeyes", "iowa state": "Cyclones",
    "kansas": "Jayhawks", "kansas state": "Wildcats", "kentucky": "Wildcats", "lsu": "Tigers",
    "louisville": "Cardinals", "maryland": "Terrapins", "miami": "Hurricanes", "michigan": "Wolverines",
    "michigan state": "Spartans", "minnesota": "Golden Gophers", "mississippi state": "Bulldogs",
    "missouri": "Tigers", "nebraska": "Cornhuskers", "north carolina": "Tar Heels", "unc": "Tar Heels",
    "nc state": "Wolfpack", "notre dame": "Fighting Irish", "ohio state": "Buckeyes", "oklahoma": "Sooners",
    "oklahoma state": "Cowboys", "ole miss": "Rebels", "oregon": "Ducks", "oregon state": "Beavers",
    "penn state": "Nittany Lions", "pitt": "Panthers", "purdue": "Boilermakers", "south carolina": "Gamecocks",
    "stanford": "Cardinal", "syracuse": "Orange", "tennessee": "Volunteers", "texas": "Longhorns",
    "texas a&m": "Aggies", "tcu": "Horned Frogs", "texas tech": "Red Raiders", "ucla": "Bruins",
    "unlv": "Runnin' Rebels", "usc": "Trojans", "utah": "Utes", "villanova": "Wildcats", "virginia": "Cavaliers",
    "virginia tech": "Hokies", "wake forest": "Demon Deacons", "washington": "Huskies", "west virginia":
    "Mountaineers", "wisconsin": "Badgers", "uconn": "Huskies", "army": "Black Knights", "navy": "Midshipmen",
    "harvard": "Crimson", "yale": "Bulldogs", "princeton": "Tigers", "hawaii": "Rainbow Warriors",
}
BRANDS = ["champion", "russell athletic", "russell", "starter", "nutmeg", "the game", "galt sand", "jostens",
          "velva sheen", "artex", "hanes", "fruit of the loom", "screen stars", "salem", "logo 7", "nike", "adidas",
          "tultex", "lee", "jerzees", "signal", "anvil", "delta", "gildan", "majestic", "mitchell & ness"]
TYPES = {"crewneck": "Crewneck Sweatshirt", "sweatshirt": "Crewneck Sweatshirt", "hoodie": "Hoodie",
         "jersey": "Jersey", "jacket": "Jacket", "windbreaker": "Windbreaker", "hat": "Hat", "snapback": "Snapback Hat",
         "polo": "Polo", "tank": "Tank Top", "long sleeve": "Long Sleeve Tee", "tee": "T-Shirt", "t-shirt": "T-Shirt",
         "shirt": "T-Shirt"}
EVENTS = ["national champions", "champions", "championship", "bowl", "final four", "march madness", "homecoming",
          "tournament", "rose bowl", "sugar bowl", "orange bowl", "fiesta bowl", "cotton bowl"]
FLAWS = ["stain", "hole", "crack", "cracking", "fade", "faded", "distressed", "pilling", "tear", "yellowing", "paint"]
SIZE_RE = re.compile(r"\b(xxs|xs|s|m|l|xl|xxl|xxxl|[2-5]xl|small|medium|large|x-large)\b", re.I)
SIZE_NORM = {"small": "S", "medium": "M", "large": "L", "x-large": "XL", "xxl": "2XL", "xxxl": "3XL"}
DECADE_RE = re.compile(r"\b(?:19)?([5-9]0)'?s\b|\b(y2k|00s|2000s)\b", re.I)

# (percent, fixed $) taken per sale. Check these against the platforms - they change.
DEFAULT_FEES = {"depop": (3.3, 0.45), "ebay": (13.6, 0.40), "etsy": (9.5, 0.45), "other": (0.0, 0.0)}
SEASONS = {  # month -> nudge for the weekly report
    8: "Football season is starting: list school tees now.", 9: "Peak football season: school tees move fastest.",
    10: "Football + sweatshirt weather: crewnecks sell for top dollar.", 11: "Rivalry week + holiday gifts: bump prices.",
    12: "Bowl season and gifts: list bowl-game shirts.", 1: "Bowl/playoff shirts peak; crewnecks still strong.",
    2: "Basketball heats up: stock hoops schools (Duke, UNC, Kentucky, Kansas).",
    3: "March Madness: list Final Four / hoops-school pieces now.", 4: "Spring: tees over sweatshirts.",
    5: "Slow season for college gear: buy cheap, hold for August.", 6: "Stockpile college pieces for fall.",
    7: "Get fall inventory photographed and listed before August."}


@dataclass
class Item:
    note: str
    cost: float = 0.0
    school: str | None = None
    brand: str | None = None
    decade: str | None = None
    size: str | None = None
    kind: str = "T-Shirt"
    event: str | None = None
    single_stitch: bool = False
    flaws: list[str] = field(default_factory=list)
    p2p: float | None = None     # pit to pit, inches
    length: float | None = None  # inches
    price: float | None = None   # current asking price
    id: int | None = None
    listed_at: float | None = None
    sold_at: float | None = None
    sold_price: float | None = None
    platform: str | None = None
    fees: float | None = None
    shipping: float | None = None


def _find(text: str, options) -> str | None:
    for opt in sorted(options, key=len, reverse=True):  # longest first: "michigan state" before "michigan"
        if re.search(rf"(?<![\w]){re.escape(opt)}(?![\w])", text):
            return opt
    return None


def parse_note(note: str, **overrides) -> Item:
    """Turn a quick note like '90s Champion Michigan tee, L, small stain' into a structured item."""
    t = note.lower()
    school = _find(t, SCHOOLS)
    brand = _find(t, BRANDS)
    kind_key = _find(t, TYPES)
    event = _find(t, EVENTS)
    d = DECADE_RE.search(note)
    decade = (f"{d.group(1)}s" if d.group(1) else "Y2K") if d else None
    # letter sizes ("L", "2XL") win over words, since "small stain" describes a flaw, not the size
    size_text = re.sub(r"\b[5-9]0'?s\b", " ", note)
    if school:  # e.g. the "m" in "texas a&m"
        size_text = re.sub(re.escape(school), " ", size_text, flags=re.I)
    found = [m.group(1) for m in SIZE_RE.finditer(size_text)]
    letters = [x for x in found if x.lower() not in SIZE_NORM or x.lower() in ("xxl", "xxxl")]
    words = [x for x in found if x not in letters]
    size = None
    if letters or words:
        pick = (letters or words)[-1].lower()
        size = SIZE_NORM.get(pick, pick.upper())
    item = Item(
        note=note,
        school=school.title() if school and len(school) > 4 else (school.upper() if school else None),
        brand=brand.title() if brand else None, decade=decade, size=size,
        kind=TYPES[kind_key] if kind_key else "T-Shirt", event=event.title() if event else None,
        single_stitch=bool(re.search(r"single[- ]?stitch", t)),
        flaws=[f for f in FLAWS if re.search(rf"\b{f}\b", t)],
    )
    for k, v in overrides.items():
        if v is not None:
            setattr(item, k, v)
    if item.school and item.school.lower() == "texas a&m":
        item.school = "Texas A&M"
    return item


def mascot(item: Item) -> str | None:
    return SCHOOLS.get((item.school or "").lower())


def listing_copy(item: Item) -> dict[str, Any]:
    """Titles/descriptions sized for each platform: eBay title <=80 chars, Depop 5 hashtags, Etsy 13 tags."""
    parts = ["Vintage", item.decade, item.school, mascot(item), item.event, item.brand,
             "Single Stitch" if item.single_stitch else None, item.kind,
             f"Size {item.size}" if item.size else None]
    words = [p for p in parts if p]
    title = " ".join(words)
    ebay = title
    for drop in ("Single Stitch", item.event, item.brand, mascot(item)):  # trim least important first
        if len(ebay) <= 80:
            break
        if drop:
            ebay = " ".join(w for w in ebay.split(" ") if w not in drop.split(" "))
    ebay = ebay[:80].rstrip()

    school_tag = re.sub(r"[^a-z0-9]", "", (item.school or "college").lower())
    hashtags = [f"#{school_tag}", "#vintage", f"#{(item.decade or 'vintage').lower()}",
                f"#{re.sub(r'[^a-z0-9]', '', (item.brand or 'collegiate').lower())}", "#collegeshirt"]
    hashtags = list(dict.fromkeys(hashtags))[:5]

    cond = ("Flaws: " + ", ".join(item.flaws) + " - see photos.") if item.flaws else "Great vintage condition, no major flaws."
    meas = []
    if item.p2p:
        meas.append(f'Pit to pit: {item.p2p:g}"')
    if item.length:
        meas.append(f'Length: {item.length:g}"')
    desc_lines = [
        title,
        "",
        f"Tagged size {item.size or '?'}. " + (" | ".join(meas) if meas else "Measurements in photos."),
        cond,
        "Authentic vintage, not a reproduction." + (" Single stitch." if item.single_stitch else ""),
        "Ships within 1 business day. Bundle for a discount!",
        "",
        " ".join(hashtags),
    ]
    etsy_tags = [t for t in dict.fromkeys([
        "vintage college", f"vintage {item.school or 'college'}".lower(), (item.school or "").lower(),
        (mascot(item) or "").lower(), f"{item.decade} vintage".lower() if item.decade else "",
        (item.brand or "").lower(), "college shirt", "vintage tee" if "T-Shirt" in item.kind else "vintage crewneck",
        "retro sports", "game day", "vintage sportswear", "football shirt", "gift for him"]) if t and len(t) <= 20][:13]
    return {"title": title, "ebay_title": ebay, "depop_description": "\n".join(desc_lines)[:1000],
            "hashtags": hashtags, "etsy_tags": etsy_tags, "suggested_price": suggest_price(item)}


def suggest_price(item: Item) -> float:
    """Starting ask from the attributes buyers pay up for. Log real sales and the stats will refine this."""
    base = {"Crewneck Sweatshirt": 45, "Hoodie": 45, "Jacket": 55, "Windbreaker": 45, "Jersey": 50}.get(item.kind, 30)
    mult = 1.0
    mult *= {"70s": 1.5, "80s": 1.35, "90s": 1.15}.get(item.decade or "", 1.0)
    if item.single_stitch:
        mult *= 1.2
    if item.event:
        mult *= 1.2
    if (item.brand or "").lower() in {"champion", "starter", "nutmeg", "russell athletic", "velva sheen", "artex"}:
        mult *= 1.15
    mult *= max(0.6, 1 - 0.12 * len(item.flaws))
    return float(round(base * mult / 5) * 5 - 0.01) if base * mult >= 10 else 9.99


class Inventory:
    COLS = [f for f in Item.__dataclass_fields__ if f not in ("id",)]

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute("""CREATE TABLE IF NOT EXISTS vintage_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, note TEXT, cost REAL, school TEXT, brand TEXT, decade TEXT,
            size TEXT, kind TEXT, event TEXT, single_stitch INT, flaws TEXT, p2p REAL, length REAL, price REAL,
            listed_at REAL, sold_at REAL, sold_price REAL, platform TEXT, fees REAL, shipping REAL)""")
        self.db.commit()

    def _row(self, r) -> Item:
        d = dict(zip(["id"] + self.COLS, r))
        d["flaws"] = [f for f in (d["flaws"] or "").split(",") if f]
        d["single_stitch"] = bool(d["single_stitch"])
        return Item(**d)

    def add(self, item: Item, now: float | None = None) -> Item:
        item.listed_at = item.listed_at or now or time.time()
        if item.price is None:
            item.price = suggest_price(item)
        vals = [",".join(v) if isinstance(v, list) else v for v in (getattr(item, c) for c in self.COLS)]
        cur = self.db.execute(f"INSERT INTO vintage_items ({','.join(self.COLS)}) VALUES "
                              f"({','.join('?' * len(self.COLS))})", vals)
        self.db.commit()
        item.id = cur.lastrowid
        return item

    def get(self, item_id: int) -> Item:
        r = self.db.execute(f"SELECT id,{','.join(self.COLS)} FROM vintage_items WHERE id=?", (item_id,)).fetchone()
        if not r:
            raise KeyError(f"no item #{item_id}")
        return self._row(r)

    def all(self, active: bool | None = None) -> list[Item]:
        where = "" if active is None else ("WHERE sold_at IS NULL" if active else "WHERE sold_at IS NOT NULL")
        return [self._row(r) for r in self.db.execute(
            f"SELECT id,{','.join(self.COLS)} FROM vintage_items {where} ORDER BY id")]

    def set_price(self, item_id: int, price: float) -> None:
        self.db.execute("UPDATE vintage_items SET price=? WHERE id=?", (price, item_id))
        self.db.commit()

    def sell(self, item_id: int, price: float, platform: str = "depop", fees: float | None = None,
             shipping: float = 0.0, fee_table: dict | None = None, now: float | None = None) -> Item:
        item = self.get(item_id)
        if item.sold_at:
            raise ValueError(f"item #{item_id} is already marked sold")
        if fees is None:
            pct, fixed = (fee_table or DEFAULT_FEES).get(platform, DEFAULT_FEES["other"])
            fees = round(price * pct / 100 + fixed, 2)
        self.db.execute("UPDATE vintage_items SET sold_at=?, sold_price=?, platform=?, fees=?, shipping=? WHERE id=?",
                        (now or time.time(), price, platform, fees, shipping, item_id))
        self.db.commit()
        return self.get(item_id)

    def delete(self, item_id: int) -> None:
        self.db.execute("DELETE FROM vintage_items WHERE id=?", (item_id,))
        self.db.commit()


def profit(item: Item) -> float:
    return (item.sold_price or 0) - (item.fees or 0) - (item.shipping or 0) - (item.cost or 0)


def stats(items: list[Item], min_sales: int = 2) -> dict[str, Any]:
    """Money numbers plus which schools/brands/decades/types earn the most per piece and sell the fastest."""
    sold = [i for i in items if i.sold_at]
    active = [i for i in items if not i.sold_at]
    out: dict[str, Any] = {
        "sold": len(sold), "active": len(active),
        "revenue": round(sum(i.sold_price or 0 for i in sold), 2),
        "profit": round(sum(profit(i) for i in sold), 2),
        "cost_all": round(sum(i.cost or 0 for i in items), 2),
        "inventory_cost": round(sum(i.cost or 0 for i in active), 2),
        "inventory_value": round(sum(i.price or 0 for i in active), 2),
        "sell_through": round(len(sold) / len(items) * 100, 1) if items else 0.0,
        "avg_days_to_sell": round(sum((i.sold_at - i.listed_at) / 86400 for i in sold) / len(sold), 1) if sold else None,
        "roi": round(sum(profit(i) for i in sold) / max(sum(i.cost or 0 for i in sold), 0.01) * 100) if sold else None,
        "by": {},
    }
    for attr in ("school", "brand", "decade", "kind", "platform"):
        groups: dict[str, list[Item]] = defaultdict(list)
        for i in sold:
            if getattr(i, attr):
                groups[getattr(i, attr)].append(i)
        rows = [{"name": k, "n": len(v), "avg_profit": round(sum(map(profit, v)) / len(v), 2),
                 "avg_days": round(sum((i.sold_at - i.listed_at) / 86400 for i in v) / len(v), 1)}
                for k, v in groups.items() if len(v) >= min_sales]
        out["by"][attr] = sorted(rows, key=lambda r: r["avg_profit"], reverse=True)
    return out


def stale_actions(items: list[Item], now: float, stale_days: int, dead_days: int,
                  markdown_pct: float) -> list[tuple[Item, str, str]]:
    """(item, stage, advice) for unsold pieces sitting too long."""
    out = []
    for i in items:
        if i.sold_at:
            continue
        age = (now - (i.listed_at or now)) / 86400
        if age >= dead_days:
            floor = max((i.cost or 0) * 2, 10)
            out.append((i, "dead", f"{age:.0f} days unsold. Drop to ${max(floor, (i.price or 0) * 0.7):.0f}, "
                                   f"offer it in a bundle, or delete + relist with new photos for a fresh boost."))
        elif age >= stale_days:
            new = round((i.price or 0) * (1 - markdown_pct / 100)) - 0.01
            out.append((i, "stale", f"{age:.0f} days unsold. Cut from ${i.price:.2f} to ${new:.2f} "
                                    f"and send offers to likers."))
    return out
