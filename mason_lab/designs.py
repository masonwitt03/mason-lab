"""Vintage-style shirt designs: print-ready PNGs (300 DPI, transparent), mockups and listing copy.

Everything here is original artwork built from type and shapes, so you own it. College names,
team logos and brand names are blocked on purpose: printing those without a license is trademark
infringement and gets Etsy shops shut down.
"""
from __future__ import annotations

import json
import math
import random
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .agents.etsy import IP_RISK
from .vintage import SCHOOLS

# Slab-serif fonts that ship with most Linux boxes. For a truer varsity look, drop an OFL font like
# "Graduate" or "Alfa Slab One" (free for commercial use at fonts.google.com) into fonts/ and set
# designs.font / designs.script_font in config.yaml.
FONT_CANDIDATES = ["fonts/display.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
                   "/Library/Fonts/Rockwell.ttc", "C:/Windows/Fonts/rockb.ttf"]
SANS_CANDIDATES = ["fonts/sans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]

# name -> shirt color (for mockups), ink, accent, and Printify color names to enable
PALETTES: dict[str, dict[str, Any]] = {
    "cream_on_navy":   {"shirt": "#1f2a44", "ink": "#efe6d2", "accent": "#c8a24a", "colors": ["Navy", "True Navy"]},
    "navy_on_ivory":   {"shirt": "#efe8d8", "ink": "#1f2a44", "accent": "#9e2b25", "colors": ["Ivory", "Natural"]},
    "cream_on_forest": {"shirt": "#2f4a3a", "ink": "#efe6d2", "accent": "#d9a441", "colors": ["Forest Green", "Hemp"]},
    "gold_on_black":   {"shirt": "#1c1c1c", "ink": "#e0b84b", "accent": "#efe6d2", "colors": ["Black"]},
    "brick_on_ivory":  {"shirt": "#efe8d8", "ink": "#9b3a2e", "accent": "#2b2b2b", "colors": ["Ivory", "Natural"]},
    "white_on_pepper": {"shirt": "#4a4a48", "ink": "#f2efe8", "accent": "#b9b2a3", "colors": ["Pepper", "Charcoal"]},
    # Game-day color pairs: fans pick the combo that matches their team - no names needed
    "red_black":       {"shirt": "#f4f1ea", "ink": "#b3232f", "accent": "#1c1c1c", "colors": ["White", "Ivory"]},
    "crimson_white":   {"shirt": "#8c1d2c", "ink": "#f4f1ea", "accent": "#c9c3b6", "colors": ["Crimson", "Maroon"]},
    "orange_navy":     {"shirt": "#f4f1ea", "ink": "#e0701f", "accent": "#1f2a44", "colors": ["White", "Ivory"]},
    "orange_white":    {"shirt": "#e0701f", "ink": "#f4f1ea", "accent": "#1f2a44", "colors": ["Orange", "Burnt Orange"]},
    "purple_gold":     {"shirt": "#f4f1ea", "ink": "#4b2e83", "accent": "#c9a646", "colors": ["White", "Ivory"]},
    "green_gold":      {"shirt": "#f4f1ea", "ink": "#1f5c3a", "accent": "#c9a646", "colors": ["White", "Ivory"]},
    "royal_white":     {"shirt": "#1f4aa8", "ink": "#f4f1ea", "accent": "#c9c3b6", "colors": ["Royal", "True Royal"]},
    "maroon_gold":     {"shirt": "#f4f1ea", "ink": "#6b1f2a", "accent": "#c9a646", "colors": ["White", "Ivory"]},
    "navy_orange":     {"shirt": "#1f2a44", "ink": "#e0701f", "accent": "#f4f1ea", "colors": ["Navy", "True Navy"]},
    "black_gold":      {"shirt": "#e9e4d8", "ink": "#1c1c1c", "accent": "#c9a646", "colors": ["White", "Ivory"]},
}

W = 3600  # 12 inches at 300 DPI - standard chest print width


class TrademarkError(ValueError):
    pass


def check_text(*texts: str) -> None:
    """Refuse college names and big brands - the fastest way to lose an Etsy shop."""
    for t in texts:
        low = (t or "").lower()
        hit = IP_RISK.search(low)
        school = next((s for s in sorted(SCHOOLS, key=len, reverse=True)
                       if len(s) > 3 and re.search(rf"\b{re.escape(s)}\b", low)), None)
        if hit or school:
            raise TrademarkError(f"'{t}' contains '{(hit.group(0) if hit else school)}', which is trademarked. "
                                 f"Use a hometown, a family name, or a made-up club instead.")


@dataclass
class Design:
    name: str
    template: str
    palette: str
    text: dict[str, str]
    keywords: list[str] = field(default_factory=list)  # search terms for the listing
    personalizable: bool = False


# --- low-level drawing -------------------------------------------------------------------------
def _font(size: int, sans: bool = False, override: str | None = None) -> ImageFont.FreeTypeFont:
    for p in ([override] if override else []) + (SANS_CANDIDATES if sans else FONT_CANDIDATES):
        if p and Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _rgba(hex_: str, a: int = 255) -> tuple[int, int, int, int]:
    h = hex_.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a


def text_masks(text: str, font, tracking: float = 0, strokes: tuple[int, ...] = (0,)) -> list[Image.Image]:
    """Masks of the same text at several stroke widths (for fill + outline rings), with letter spacing."""
    pad = max(strokes) + 4
    asc, desc = font.getmetrics()
    widths = [font.getlength(ch) for ch in text]
    width = int(sum(widths) + tracking * max(len(text) - 1, 0)) + 2 * pad
    height = asc + desc + 2 * pad
    out = []
    for sw in strokes:
        m = Image.new("L", (max(width, 1), height), 0)
        d = ImageDraw.Draw(m)
        x = pad
        for ch, w in zip(text, widths):
            d.text((x, pad), ch, font=font, fill=255, stroke_width=sw, stroke_fill=255)
            x += w + tracking
        out.append(m)
    return out


def varsity(text: str, font, ink: str, accent: str | None, tracking: float = 0,
            gap: int = 0, outline: int = 0) -> Image.Image:
    """Filled letters, optionally with a transparent gap and an accent outline (the classic varsity look)."""
    if not accent or not outline:
        m = text_masks(text, font, tracking)[0]
        img = Image.new("RGBA", m.size, _rgba(ink, 0))
        img.putalpha(m)
        return Image.composite(Image.new("RGBA", m.size, _rgba(ink)), img, m)
    fill, inner, outer = text_masks(text, font, tracking, (0, gap, gap + outline))
    ring = ImageChops.subtract(outer, inner)
    img = Image.new("RGBA", fill.size, (0, 0, 0, 0))
    img.paste(Image.new("RGBA", fill.size, _rgba(accent)), (0, 0), ring)
    img.paste(Image.new("RGBA", fill.size, _rgba(ink)), (0, 0), fill)
    return img


def arc(text: str, font, color: str, radius: float, center: tuple[float, float], tracking: float = 0,
        bottom: bool = False, accent: str | None = None, outline: int = 0, gap: int = 0,
        canvas: Image.Image | None = None) -> None:
    """Draw text around a circle: over the top (reads left to right) or under the bottom."""
    glyphs = [varsity(ch, font, color, accent, 0, gap, outline) for ch in text]
    advances = [font.getlength(ch) + tracking for ch in text]
    total = sum(advances) - tracking
    angle = -total / 2 / radius
    cx, cy = center
    for g, adv in zip(glyphs, advances):
        mid = angle + (adv - tracking) / 2 / radius
        if bottom:
            x, y, rot = cx - radius * math.sin(-mid), cy + radius * math.cos(mid), math.degrees(mid)
        else:
            x, y, rot = cx + radius * math.sin(mid), cy - radius * math.cos(mid), -math.degrees(mid)
        rg = g.rotate(rot, resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(rg, (int(x - rg.width / 2), int(y - rg.height / 2)))
        angle += adv / radius


def paste_center(canvas: Image.Image, img: Image.Image, y: int) -> int:
    """Paste horizontally centered with its top at y; returns the y below it."""
    canvas.alpha_composite(img, ((canvas.width - img.width) // 2, y))
    return y + img.height


def fit_font(text: str, max_w: int, start: int, tracking_em: float = 0.0, sans: bool = False,
             override: str | None = None):
    size = start
    while size > 40:
        f = _font(size, sans, override)
        if sum(f.getlength(c) for c in text) + tracking_em * size * (len(text) - 1) <= max_w:
            return f
        size = int(size * 0.94)
    return _font(size, sans, override)


def star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: str) -> None:
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
    draw.polygon(pts, fill=_rgba(color))


def football(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float, color: str, lace: str) -> None:
    h = w * 0.58
    draw.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=_rgba(color))
    lw = max(int(w * 0.035), 4)
    draw.line([cx - w * 0.22, cy, cx + w * 0.22, cy], fill=_rgba(lace), width=lw)
    for i in range(-3, 4):
        x = cx + i * w * 0.06
        draw.line([x, cy - h * 0.12, x, cy + h * 0.12], fill=_rgba(lace), width=lw)


def distress(img: Image.Image, amount: float = 0.22, seed: int = 7) -> Image.Image:
    """Worn, cracked-print texture: knocks random blotches and specks out of the ink."""
    if amount <= 0:
        return img
    random.seed(seed)
    w, h = img.size
    # large soft blotches
    small = Image.effect_noise((max(w // 40, 2), max(h // 40, 2)), 64).resize((w, h), Image.BICUBIC)
    blotch = small.point(lambda v: 255 if v > 255 * (1 - amount * 0.55) else 0).filter(ImageFilter.GaussianBlur(3))
    # fine speckle
    fine = Image.effect_noise((w // 3, h // 3), 90).resize((w, h), Image.NEAREST)
    speck = fine.point(lambda v: 255 if v > 255 * (1 - amount * 0.35) else 0)
    holes = ImageChops.lighter(blotch, speck)
    alpha = ImageChops.subtract(img.getchannel("A"), holes)
    out = img.copy()
    out.putalpha(alpha)
    return out


# --- templates ---------------------------------------------------------------------------------
def _t_arch(d: Design, p: dict, fonts: dict) -> Image.Image:
    """TOP WORD arched, BIG WORD straight, 'EST. YEAR' with rules - the classic college tee layout."""
    c = Image.new("RGBA", (W, 3300), (0, 0, 0, 0))
    top, main, est = d.text.get("top", ""), d.text.get("main", ""), d.text.get("est", "")
    f_top = fit_font(top, int(W * 0.9), 560, 0.08, override=fonts.get("display"))
    arc(top, f_top, p["ink"], radius=2300, center=(W / 2, 2300 + 260), tracking=f_top.size * 0.08,
        accent=p["accent"], outline=26, gap=22, canvas=c)
    f_main = fit_font(main, int(W * 0.94), 900, 0.02, override=fonts.get("display"))
    img = varsity(main, f_main, p["ink"], p["accent"], f_main.size * 0.02, gap=26, outline=32)
    y = paste_center(c, img, 1050)
    if est:
        f_est = _font(260, sans=True, override=fonts.get("sans"))
        e = varsity(est, f_est, p["accent"], None, 260 * 0.25)
        ey = y + 70
        paste_center(c, e, ey)
        d_ = ImageDraw.Draw(c)
        mid = ey + e.height // 2
        half = e.width // 2 + 80
        for sx in (-1, 1):
            d_.line([W / 2 + sx * half, mid, W / 2 + sx * (half + 520), mid], fill=_rgba(p["accent"]), width=22)
    return c


def _t_dept(d: Design, p: dict, fonts: dict) -> Image.Image:
    """PROPERTY OF / NAME / ATHLETIC DEPT. - the old gym-class tee. Great for personalization."""
    c = Image.new("RGBA", (W, 3000), (0, 0, 0, 0))
    dr = ImageDraw.Draw(c)
    f_small = _font(250, sans=True, override=fonts.get("sans"))
    y = paste_center(c, varsity(d.text.get("top", "PROPERTY OF"), f_small, p["accent"], None, 250 * 0.3), 60)
    dr.rectangle([W * 0.08, y + 50, W * 0.92, y + 72], fill=_rgba(p["accent"]))
    main = d.text.get("main", "")
    f_main = fit_font(main, int(W * 0.9), 1000, 0.03, override=fonts.get("display"))
    y = paste_center(c, varsity(main, f_main, p["ink"], p["accent"], f_main.size * 0.03, 26, 32), y + 120)
    dr.rectangle([W * 0.08, y + 40, W * 0.92, y + 62], fill=_rgba(p["accent"]))
    sub = d.text.get("sub", "ATHLETIC DEPT.")
    f_sub = fit_font(sub, int(W * 0.84), 380, 0.18, sans=True, override=fonts.get("sans"))
    paste_center(c, varsity(sub, f_sub, p["ink"], None, f_sub.size * 0.18), y + 120)
    return c


def _t_gameday(d: Design, p: dict, fonts: dict) -> Image.Image:
    """GAME / (football) / DAY stacked with stars. Sold in team-color pairs, no team names."""
    c = Image.new("RGBA", (W, 3600), (0, 0, 0, 0))
    dr = ImageDraw.Draw(c)
    l1, l2 = d.text.get("main", "GAME"), d.text.get("sub", "DAY")
    f = fit_font(max(l1, l2, key=len), int(W * 0.92), 1300, 0.04, override=fonts.get("display"))
    y = paste_center(c, varsity(l1, f, p["ink"], p["accent"], f.size * 0.04, 28, 36), 80)
    mid = y + 260
    football(dr, W / 2, mid, 560, p["accent"], p["shirt"])
    for sx in (-1, 1):
        dr.line([W / 2 + sx * 380, mid, W / 2 + sx * 1500, mid], fill=_rgba(p["accent"]), width=26)
        for i, r in enumerate((95, 70)):
            star(dr, W / 2 + sx * (1650 + i * 190), mid, r, p["accent"])
    y = paste_center(c, varsity(l2, f, p["ink"], p["accent"], f.size * 0.04, 28, 36), mid + 250)
    tag = d.text.get("tag", "")
    if tag:
        f_tag = _font(230, sans=True, override=fonts.get("sans"))
        paste_center(c, varsity(tag, f_tag, p["accent"], None, 230 * 0.3), y + 90)
    return c


def _t_badge(d: Design, p: dict, fonts: dict) -> Image.Image:
    """Round badge: text around the top and bottom, big center letters or year."""
    c = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dr = ImageDraw.Draw(c)
    cx = cy = W / 2
    for r, w in ((1700, 40), (1180, 24)):
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_rgba(p["accent"]), width=w)
    f_ring = _font(300, override=fonts.get("display"))
    arc(d.text.get("top", ""), f_ring, p["ink"], 1440, (cx, cy), tracking=300 * 0.18, canvas=c)
    arc(d.text.get("bottom", ""), f_ring, p["ink"], 1440, (cx, cy), tracking=300 * 0.18, bottom=True, canvas=c)
    for sx in (-1, 1):
        star(dr, cx + sx * 1440, cy, 90, p["accent"])
    main = d.text.get("main", "")
    f_main = fit_font(main, 1900, 1100, 0.02, override=fonts.get("display"))
    img = varsity(main, f_main, p["ink"], p["accent"], f_main.size * 0.02, 22, 28)
    c.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2) - 40))
    return c


TEMPLATES = {"arch": _t_arch, "dept": _t_dept, "gameday": _t_gameday, "badge": _t_badge}


def render(d: Design, fonts: dict | None = None, wear: float = 0.22) -> Image.Image:
    """Render one design as a tight-cropped, transparent, 300 DPI print file."""
    if d.template not in TEMPLATES:
        raise ValueError(f"unknown template {d.template}; choose from {', '.join(TEMPLATES)}")
    if d.palette not in PALETTES:
        raise ValueError(f"unknown palette {d.palette}; choose from {', '.join(PALETTES)}")
    check_text(*d.text.values())
    img = TEMPLATES[d.template](d, PALETTES[d.palette], fonts or {})
    img = distress(img, wear, seed=sum(map(ord, d.name)))
    bbox = img.getchannel("A").getbbox()
    if bbox:
        pad = 40
        img = img.crop((max(bbox[0] - pad, 0), max(bbox[1] - pad, 0),
                        min(bbox[2] + pad, img.width), min(bbox[3] + pad, img.height)))
    return img


def mockup(design_img: Image.Image, shirt_hex: str, size: int = 1600) -> Image.Image:
    """Flat-lay tee preview for your listing photos (the print shop's own mockups are better for the main photo)."""
    bg = Image.new("RGB", (size, size), "#e7e3dc")
    s = size / 100
    tee = [(33, 10), (43, 7), (50, 9), (57, 7), (67, 10), (88, 25), (79, 35), (72, 31),
           (73, 92), (27, 92), (28, 31), (21, 35), (12, 25)]
    shadow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(shadow).polygon([(x * s + 10, y * s + 14) for x, y in tee], fill=90)
    bg.paste((150, 145, 138), (0, 0), shadow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(bg)
    d.polygon([(x * s, y * s) for x, y in tee], fill=shirt_hex)
    r, g, b, _ = _rgba(shirt_hex)
    collar = tuple(int(v * 0.78) for v in (r, g, b))
    d.arc([42 * s, 2 * s, 58 * s, 13 * s], 25, 155, fill=collar, width=int(s * 1.2))
    max_w, max_h = int(36 * s), int(36 * s)
    art = design_img.copy()
    art.thumbnail((max_w, max_h), Image.LANCZOS)
    bg.paste(art, (int(50 * s - art.width / 2), int(20 * s)), art)
    return bg


# --- listing copy ------------------------------------------------------------------------------
def listing_for(d: Design) -> dict[str, Any]:
    words = " ".join(v for v in d.text.values() if v).title()
    kw = d.keywords or []
    color_name = d.palette.replace("_on_", " on ").replace("_", " and ").title()
    title_parts = [words, *[k.title() for k in kw[:3]], "Vintage Style Tee", "Retro Varsity Shirt"]
    title = ""
    for part in title_parts:
        cand = f"{title} | {part}" if title else part
        if len(cand) > 140:
            break
        title = cand
    tags = []
    for t in [*kw, "vintage style tee", "retro shirt", "varsity shirt", "college style tee", "oversized tee",
              "comfort colors", "gift for him", "gift for her", "90s style shirt", "trendy tee"]:
        t = t.lower().strip()
        if t and len(t) <= 20 and t not in tags:
            tags.append(t)
    desc = [
        f"{words} - a vintage-inspired varsity tee with a worn-in print look.",
        "",
        "- Soft, garment-dyed style tee, relaxed fit (size up for oversized)",
        "- Printed to order just for you by our production partner",
        "- The distressed texture is part of the design",
        f"- Colorway: {color_name}",
    ]
    if d.personalizable:
        desc += ["", "PERSONALIZE IT: add your name, town or year in the personalization box."]
    desc += ["", "Care: wash inside out, cold, hang dry to keep the print looking great."]
    return {"title": title, "tags": tags[:13], "description": "\n".join(desc), "personalizable": d.personalizable}


def save(d: Design, out_dir: str | Path, fonts: dict | None = None, wear: float = 0.22) -> dict[str, str]:
    out = Path(out_dir) / d.name
    out.mkdir(parents=True, exist_ok=True)
    art = render(d, fonts, wear)
    art.save(out / "print.png", dpi=(300, 300))
    mockup(art, PALETTES[d.palette]["shirt"]).save(out / "mockup.jpg", quality=90)
    (out / "design.json").write_text(json.dumps({**asdict(d), "listing": listing_for(d)}, indent=2))
    return {"print": str(out / "print.png"), "mockup": str(out / "mockup.jpg"), "json": str(out / "design.json")}


def load(path: str | Path) -> Design:
    data = json.loads((Path(path) / "design.json").read_text())
    data.pop("listing", None)
    return Design(**data)


# --- starter collection ------------------------------------------------------------------------
GAMEDAY_PALETTES = ["red_black", "crimson_white", "orange_navy", "orange_white", "purple_gold", "green_gold",
                    "royal_white", "maroon_gold", "navy_orange", "black_gold"]


def starter_collection(surname: str = "SMITH", town: str = "HOMETOWN", year: str = "1994") -> list[Design]:
    """A launch line built around what sells on Etsy: game-day tees in team colors, personalized
    'athletic dept' tees, and social-club varsity tees."""
    gd_kw = ["game day shirt", "football shirt", "game day tee", "football season", "tailgate shirt"]
    designs = [Design(f"gameday_{p}", "gameday", p, {"main": "GAME", "sub": "DAY", "tag": "SATURDAYS"},
                      gd_kw + [p.replace("_", " and ") + " shirt"]) for p in GAMEDAY_PALETTES]
    designs += [
        Design("family_athletic_dept", "dept", "navy_on_ivory",
               {"top": "PROPERTY OF", "main": surname.upper(), "sub": "ATHLETIC DEPT."},
               ["custom family shirt", "family reunion", "personalized shirt", "last name shirt"], True),
        Design("girl_dad_athletic_dept", "dept", "cream_on_forest",
               {"top": "PROPERTY OF", "main": "GIRL DAD", "sub": "ATHLETIC DEPT."},
               ["girl dad shirt", "fathers day gift", "dad shirt", "new dad gift"]),
        Design("mom_athletic_dept", "dept", "brick_on_ivory",
               {"top": "PROPERTY OF", "main": "MAMA", "sub": "ATHLETIC DEPT."},
               ["mama shirt", "mom shirt", "mothers day gift", "sports mom shirt"]),
        Design("hometown_est", "arch", "cream_on_navy", {"top": town.upper(), "main": "ATHLETICS", "est": f"EST. {year}"},
               ["hometown shirt", "custom city shirt", "personalized town", "state pride shirt"], True),
        Design("weekend_athletic_club", "arch", "navy_on_ivory",
               {"top": "WEEKEND", "main": "ATHLETIC CLUB", "est": "EST. 1994"},
               ["weekend shirt", "athletic club shirt", "preppy shirt", "social club shirt"]),
        Design("coffee_club", "arch", "brick_on_ivory", {"top": "COFFEE CLUB", "main": "VARSITY", "est": "EST. 1987"},
               ["coffee shirt", "coffee lover gift", "coffee club shirt", "social club shirt"]),
        Design("lake_rowing_club", "badge", "cream_on_forest",
               {"top": "LAKE LIFE", "bottom": "ROWING CLUB", "main": year},
               ["lake shirt", "lake life shirt", "rowing shirt", "summer shirt"]),
        Design("bachelorette_social_club", "badge", "gold_on_black",
               {"top": "BACHELORETTE", "bottom": "SOCIAL CLUB", "main": "BRIDE"},
               ["bachelorette shirts", "bride shirt", "bridal party", "social club shirt"], True),
    ]
    return designs
