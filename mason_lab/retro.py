"""Retro holiday collection: illustrated designs built for Etsy's biggest season (Oct-Dec).

Everything is drawn at 2x (7200 px wide) and scaled down so edges come out smooth, then exported
at 3600 px = 12 inches at 300 DPI. Fonts are SIL Open Font License, free for commercial use.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .designs import PALETTES, TEMPLATES, Design, _rgba, arc

FONT_DIR = Path(__file__).parent / "fonts"
CW = 7200  # working width (2x)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / f"{name}.woff"), size)


def finish(img: Image.Image) -> Image.Image:
    return img.resize((img.width // 2, img.height // 2), Image.LANCZOS)


# --- retro text ------------------------------------------------------------------------------
def _layout(text: str, f, tracking: float, wave: float, wave_len: float, bend: float):
    adv = [f.getlength(c) + tracking for c in text]
    total = sum(adv) - tracking
    out, x = [], -total / 2
    for c, a in zip(text, adv):
        cx = x + (a - tracking) / 2
        u = cx / (total / 2) if total else 0  # -1..1 across the word

        def y_at(xx, uu):
            return wave * math.sin(2 * math.pi * xx / wave_len) - bend * (1 - uu * uu)

        dx = 1.0
        slope = (y_at(cx + dx, (cx + dx) / (total / 2 or 1)) - y_at(cx, u)) / dx
        out.append((c, cx, y_at(cx, u), math.degrees(math.atan(slope))))
        x += a
    return out, total


def _mask(layout, f, stroke: int, size: tuple[int, int], origin: tuple[float, float]) -> Image.Image:
    m = Image.new("L", size, 0)
    asc, desc = f.getmetrics()
    pad = stroke + 8
    for c, x, y, ang in layout:
        if c == " ":
            continue
        g = Image.new("L", (int(f.getlength(c)) + 2 * pad, asc + desc + 2 * pad), 0)
        ImageDraw.Draw(g).text((pad, pad), c, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
        g = g.rotate(-ang, resample=Image.BICUBIC, expand=True)
        m.paste(255, (int(origin[0] + x - g.width / 2), int(origin[1] + y - g.height / 2)), g)
    return m


def retro_text(canvas: Image.Image, text: str, f, cx: float, cy: float, fill: str, outline: str | None = None,
               ow: int = 0, shadow: str | None = None, depth: int = 0, tracking: float = 0,
               wave: float = 0, wave_len: float = 3000, bend: float = 0, inner: str | None = None,
               iw: int = 0, direction: tuple[int, int] = (1, 1)) -> tuple[int, int]:
    """70s-style lettering: fill, optional inner + outer outline, and a solid extruded drop shadow.
    Returns (width, height) of the drawn block."""
    lay, total = _layout(text, f, tracking, wave, wave_len, bend)
    asc, desc = f.getmetrics()
    margin = ow + iw + depth + 60
    w = int(total + 2 * margin + 200)
    h = int(asc + desc + 2 * abs(wave) + abs(bend) + 2 * margin + 200)
    origin = (w / 2, h / 2 + bend / 2)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    outer_w = ow + iw
    outer = _mask(lay, f, outer_w, (w, h), origin)
    if shadow and depth:
        sh = Image.new("L", (w, h), 0)
        step = 6
        for k in range(step, depth + 1, step):
            sh.paste(255, (direction[0] * k, direction[1] * k), outer)
        layer.paste(Image.new("RGBA", (w, h), _rgba(shadow)), (0, 0), sh)
    if outline and ow:
        layer.paste(Image.new("RGBA", (w, h), _rgba(outline)), (0, 0), outer)
    if inner and iw:
        layer.paste(Image.new("RGBA", (w, h), _rgba(inner)), (0, 0), _mask(lay, f, iw, (w, h), origin))
    layer.paste(Image.new("RGBA", (w, h), _rgba(fill)), (0, 0), _mask(lay, f, 0, (w, h), origin))
    box = layer.getchannel("A").getbbox()
    canvas.alpha_composite(layer, (int(cx - w / 2), int(cy - h / 2)))
    return (box[2] - box[0], box[3] - box[1]) if box else (0, 0)


# --- illustration helpers --------------------------------------------------------------------
def sticker(layer: Image.Image, width: int, color: str) -> Image.Image:
    """Thick rounded outline around everything drawn on the layer (the cute 'sticker' look)."""
    a = layer.getchannel("A")
    grown = a.filter(ImageFilter.GaussianBlur(width / 2)).point(lambda v: 255 if v > 10 else 0)
    grown = grown.filter(ImageFilter.GaussianBlur(2))
    base = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    base.paste(Image.new("RGBA", layer.size, _rgba(color)), (0, 0), grown)
    base.alpha_composite(layer)
    return base


def new_layer(w: float, h: float, pad: int = 160) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    img = Image.new("RGBA", (int(w) + 2 * pad, int(h) + 2 * pad), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), pad


def place(canvas: Image.Image, layer: Image.Image, cx: float, cy: float, rotate: float = 0) -> None:
    if rotate:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def sparkle(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: str) -> None:
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.22
        pts.append((cx + rr * math.sin(a), cy - rr * math.cos(a)))
    d.polygon(pts, fill=_rgba(color))


def star5(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: str, rot: float = 0) -> None:
    pts = []
    for i in range(10):
        a = math.radians(rot) + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.sin(a), cy - rr * math.cos(a)))
    d.polygon(pts, fill=_rgba(color))


def ghost(S: float, body: str, ink: str, blush: str, ow: int) -> Image.Image:
    img, d, p = new_layer(S, S * 1.2)
    o = lambda x, y: (p + x * S, p + y * S)  # noqa: E731
    d.ellipse([*o(0.1, 0.05), *o(0.9, 0.85)], fill=_rgba(body))
    d.rectangle([*o(0.1, 0.45), *o(0.9, 1.0)], fill=_rgba(body))
    for i in range(3):
        cx = 0.1 + 0.8 / 6 * (2 * i + 1)
        d.ellipse([*o(cx - 0.8 / 6, 0.9), *o(cx + 0.8 / 6, 1.12)], fill=_rgba(body))
    d.ellipse([*o(-0.02, 0.55), *o(0.2, 0.72)], fill=_rgba(body))  # arms
    d.ellipse([*o(0.8, 0.5), *o(1.02, 0.67)], fill=_rgba(body))
    img = sticker(img, ow, ink)
    d = ImageDraw.Draw(img)
    for ex in (0.36, 0.64):
        d.ellipse([*o(ex - 0.045, 0.4), *o(ex + 0.045, 0.52)], fill=_rgba(ink))
        d.ellipse([*o(ex - 0.018, 0.415), *o(ex + 0.012, 0.45)], fill=_rgba(body))
    for bx in (0.27, 0.73):
        d.ellipse([*o(bx - 0.06, 0.54), *o(bx + 0.06, 0.59)], fill=_rgba(blush))
    d.arc([*o(0.45, 0.49), *o(0.55, 0.59)], 20, 160, fill=_rgba(ink), width=int(S * 0.018))
    return img


def pumpkin(S: float, body: str, shade: str, stem: str, leaf: str, ink: str, ow: int, face: bool = False) -> Image.Image:
    img, d, p = new_layer(S, S)
    o = lambda x, y: (p + x * S, p + y * S)  # noqa: E731
    d.ellipse([*o(0.02, 0.28), *o(0.56, 0.96)], fill=_rgba(shade))
    d.ellipse([*o(0.44, 0.28), *o(0.98, 0.96)], fill=_rgba(shade))
    d.ellipse([*o(0.2, 0.24), *o(0.8, 0.98)], fill=_rgba(body))
    d.polygon([o(0.45, 0.3), o(0.43, 0.08), o(0.5, 0.02), o(0.58, 0.06), o(0.55, 0.3)], fill=_rgba(stem))
    d.ellipse([*o(0.56, 0.08), *o(0.86, 0.22)], fill=_rgba(leaf))
    img = sticker(img, ow, ink)
    d = ImageDraw.Draw(img)
    lw = int(S * 0.016)
    d.arc([*o(0.2, 0.24), *o(0.5, 0.98)], 110, 250, fill=_rgba(ink), width=lw)
    d.arc([*o(0.5, 0.24), *o(0.8, 0.98)], -70, 70, fill=_rgba(ink), width=lw)
    d.arc([*o(0.56, 0.08), *o(0.86, 0.22)], 180, 360, fill=_rgba(ink), width=lw // 2 + 2)
    d.ellipse([*o(0.3, 0.38), *o(0.36, 0.56)], fill=(255, 255, 255, 90))  # highlight
    if face:
        d.polygon([o(0.36, 0.5), o(0.42, 0.6), o(0.3, 0.6)], fill=_rgba(ink))
        d.polygon([o(0.64, 0.5), o(0.7, 0.6), o(0.58, 0.6)], fill=_rgba(ink))
        d.chord([*o(0.33, 0.58), *o(0.67, 0.84)], 0, 180, fill=_rgba(ink))
    return img


def mug(S: float, body: str, band: str, coffee: str, heart: str, ink: str, steam: str, ow: int) -> Image.Image:
    img, d, p = new_layer(S, S * 1.3)
    o = lambda x, y: (p + x * S, p + y * S)  # noqa: E731
    top = 0.45
    d.ellipse([*o(0.6, top + 0.15), *o(0.98, top + 0.55)], outline=_rgba(body), width=int(S * 0.08))
    d.rounded_rectangle([*o(0.08, top), *o(0.78, top + 0.8)], radius=int(S * 0.1), fill=_rgba(body))
    d.rectangle([*o(0.08, top + 0.52), *o(0.78, top + 0.62)], fill=_rgba(band))
    img = sticker(img, ow, ink)
    d = ImageDraw.Draw(img)
    d.ellipse([*o(0.12, top - 0.02), *o(0.74, top + 0.1)], fill=_rgba(coffee))
    hx, hy, hr = 0.43, top + 0.3, 0.08
    d.ellipse([*o(hx - hr, hy - hr * 0.8), *o(hx, hy + hr * 0.2)], fill=_rgba(heart))
    d.ellipse([*o(hx, hy - hr * 0.8), *o(hx + hr, hy + hr * 0.2)], fill=_rgba(heart))
    d.polygon([o(hx - hr * 0.98, hy - hr * 0.2), o(hx + hr * 0.98, hy - hr * 0.2), o(hx, hy + hr * 1.2)], fill=_rgba(heart))
    for i, sx in enumerate((0.26, 0.43, 0.6)):
        pts = [o(sx + 0.035 * math.sin(t / 6 * math.pi * 2 + i), top - 0.08 - 0.33 * t / 6) for t in range(0, 7)]
        d.line(pts, fill=_rgba(steam), width=int(S * 0.035), joint="curve")
    return img


def tree(S: float, green: str, dark: str, trunk: str, star: str, balls: list[str], garland: str, ink: str,
         ow: int) -> Image.Image:
    img, d, p = new_layer(S, S * 1.3)
    o = lambda x, y: (p + x * S, p + y * S)  # noqa: E731
    d.rectangle([*o(0.42, 1.02), *o(0.58, 1.22)], fill=_rgba(trunk))
    tiers = [(0.14, 0.52, 0.34), (0.36, 0.8, 0.43), (0.6, 1.08, 0.5)]
    for top_y, base_y, half in tiers:
        d.polygon([o(0.5, top_y), o(0.5 + half, base_y), o(0.5 - half, base_y)], fill=_rgba(green))
        d.polygon([o(0.5, top_y), o(0.5 + half, base_y), o(0.5, base_y)], fill=_rgba(dark))
    img = sticker(img, ow, ink)
    d = ImageDraw.Draw(img)
    lw = int(S * 0.02)
    for (a, b, c) in [(0.3, 0.45, 0.38), (0.55, 0.72, 0.62), (0.8, 1.0, 0.9)]:
        d.line([o(0.5 - (a - 0.1) * 0.9, a + 0.06), o(0.5, c), o(0.5 + (b - 0.1) * 0.62, b - 0.04)],
               fill=_rgba(garland), width=lw, joint="curve")
    spots = [(0.42, 0.44), (0.6, 0.4), (0.33, 0.7), (0.52, 0.66), (0.7, 0.74), (0.26, 0.98), (0.46, 0.95),
             (0.64, 0.98), (0.82, 1.0)]
    for i, (x, y) in enumerate(spots):
        r = 0.04
        d.ellipse([*o(x - r, y - r), *o(x + r, y + r)], fill=_rgba(balls[i % len(balls)]), outline=_rgba(ink),
                  width=max(lw // 2, 4))
    star5(d, p + 0.5 * S, p + 0.12 * S, 0.13 * S, ink)
    star5(d, p + 0.5 * S, p + 0.12 * S, 0.1 * S, star)
    return img


def holly(S: float, leaf: str, berry: str, ink: str, ow: int) -> Image.Image:
    img, d, p = new_layer(S, S * 0.7)
    for ang, cx in ((-28, 0.3), (28, 0.7)):
        pts = []
        for i in range(21):
            t = i / 20
            w = math.sin(math.pi * t) * 0.16 * (1.25 if i % 4 == 2 else 1)
            pts.append((t * 0.55, -w))
        for i in range(20, -1, -1):
            t = i / 20
            w = math.sin(math.pi * t) * 0.16 * (1.25 if i % 4 == 2 else 1)
            pts.append((t * 0.55, w))
        a = math.radians(ang + (180 if cx < 0.5 else 0))
        rot = [(0.5 + (x * math.cos(a) - y * math.sin(a)) * (1), 0.42 + (x * math.sin(a) + y * math.cos(a))) for x, y in pts]
        d.polygon([(p + x * S, p + y * S) for x, y in rot], fill=_rgba(leaf))
    for bx, by in ((0.44, 0.44), (0.56, 0.44), (0.5, 0.34)):
        r = 0.07
        d.ellipse([p + (bx - r) * S, p + (by - r) * S, p + (bx + r) * S, p + (by + r) * S], fill=_rgba(berry))
    img = sticker(img, ow, ink)
    d = ImageDraw.Draw(img)
    for bx, by in ((0.44, 0.44), (0.56, 0.44), (0.5, 0.34)):
        d.ellipse([p + (bx - 0.035) * S, p + (by - 0.04) * S, p + (bx - 0.005) * S, p + (by - 0.01) * S],
                  fill=(255, 255, 255, 150))
    return img


def gingerbread(S: float, dough: str, icing: str, buttons: list[str], ink: str, ow: int, bitten: bool = True) -> Image.Image:
    img, d, p = new_layer(S, S * 1.1)
    o = lambda x, y: (p + x * S, p + y * S)  # noqa: E731
    lw = int(S * 0.2)
    d.line([o(0.3, 0.48), o(0.08, 0.36)], fill=_rgba(dough), width=lw)
    d.line([o(0.7, 0.48), o(0.92, 0.36)], fill=_rgba(dough), width=lw)
    for x, y in ((0.08, 0.36), (0.92, 0.36)):
        d.ellipse([*o(x - 0.1, y - 0.1), *o(x + 0.1, y + 0.1)], fill=_rgba(dough))
    legs = [((0.4, 0.78), (0.3, 0.98))] + ([] if bitten else [((0.6, 0.78), (0.7, 0.98))])
    for a, b in legs:
        d.line([o(*a), o(*b)], fill=_rgba(dough), width=lw)
        d.ellipse([*o(b[0] - 0.1, b[1] - 0.1), *o(b[0] + 0.1, b[1] + 0.1)], fill=_rgba(dough))
    if bitten:  # a stub where the leg got eaten
        d.ellipse([*o(0.5, 0.7), *o(0.72, 0.9)], fill=_rgba(dough))
    d.rounded_rectangle([*o(0.28, 0.36), *o(0.72, 0.84)], radius=int(S * 0.12), fill=_rgba(dough))
    d.ellipse([*o(0.3, 0.02), *o(0.7, 0.42)], fill=_rgba(dough))
    if bitten:
        for bx, by, r in ((0.7, 0.93, 0.055), (0.77, 0.86, 0.05), (0.66, 1.0, 0.05)):
            d.ellipse([*o(bx - r, by - r), *o(bx + r, by + r)], fill=(0, 0, 0, 0))
    img = sticker(img, ow, ink)
    d = ImageDraw.Draw(img)
    iw = int(S * 0.02)
    for x, y in ((0.08, 0.36), (0.92, 0.36)):
        d.arc([*o(x - 0.07, y - 0.1), *o(x + 0.03, y + 0.1)], -60, 60, fill=_rgba(icing), width=iw)
    for a, b in legs:
        d.arc([*o(b[0] - 0.1, b[1] - 0.13), *o(b[0] + 0.1, b[1] - 0.01)], 20, 160, fill=_rgba(icing), width=iw)
    for i, by in enumerate((0.5, 0.64)):
        d.ellipse([*o(0.46, by - 0.04), *o(0.54, by + 0.04)], fill=_rgba(buttons[i % len(buttons)]))
    for ex in (0.42, 0.58):
        d.ellipse([*o(ex - 0.028, 0.17), *o(ex + 0.028, 0.23)], fill=_rgba(ink))
    d.arc([*o(0.4, 0.2), *o(0.6, 0.33)], 20, 160, fill=_rgba(icing), width=iw)
    return img


def sunset(S: float, colors: list[str], stripes: int = 4) -> Image.Image:
    img, d, p = new_layer(S, S / 2 + 10)
    n = len(colors)
    for i, c in enumerate(colors):
        r = S / 2 * (1 - i / (n + 0.4))
        d.pieslice([p + S / 2 - r, p + S / 2 - r, p + S / 2 + r, p + S / 2 + r], 180, 360, fill=_rgba(c))
    y = p + S / 2
    for i in range(stripes):  # the classic 70s horizontal cut-outs
        gap = S * 0.012 * (i + 1)
        y -= S * 0.06
        d.rectangle([0, y - gap, img.width, y], fill=(0, 0, 0, 0))
        y -= gap
    return img


def sunburst(S: float, color: str, n: int = 24) -> Image.Image:
    img, d, p = new_layer(S, S)
    for i in range(n):
        a0 = 360 / n * i
        d.pieslice([p, p, p + S, p + S], a0, a0 + 360 / n / 2, fill=_rgba(color))
    return img


# --- palettes (Comfort Colors 1717 color names) -------------------------------------------------
RETRO_PALETTES = {
    "spooky_pepper":  {"shirt": "#4a4845", "ink": "#e8742a", "accent": "#f4ead6", "shadow": "#2a1a12",
                       "extra": "#b9a6d9", "colors": ["Pepper", "Black"]},
    "boo_ivory":      {"shirt": "#efe8d8", "ink": "#e8742a", "accent": "#2a1d14", "shadow": "#6b3f8f",
                       "extra": "#f4a6a0", "colors": ["Ivory"]},
    "pumpkin_ivory":  {"shirt": "#efe8d8", "ink": "#c9571b", "accent": "#2a1d14", "shadow": "#e7b04b",
                       "extra": "#6f8f3a", "colors": ["Ivory", "Butter"]},
    "cozy_espresso":  {"shirt": "#5a4034", "ink": "#f4ead6", "accent": "#2a1d14", "shadow": "#c9571b",
                       "extra": "#e7b04b", "colors": ["Espresso", "Brown"]},
    "thankful_ivory": {"shirt": "#efe8d8", "ink": "#8a3a1e", "accent": "#f4ead6", "shadow": "#e7b04b",
                       "extra": "#c9571b", "colors": ["Ivory", "Khaki"]},
    "merry_ivory":    {"shirt": "#efe8d8", "ink": "#c0282d", "accent": "#f7f1e3", "shadow": "#1f5c3a",
                       "extra": "#e7b04b", "colors": ["Ivory"]},
    "jolly_pepper":   {"shirt": "#4a4845", "ink": "#e0453a", "accent": "#f4ead6", "shadow": "#1f5c3a",
                       "extra": "#e7b04b", "colors": ["Pepper"]},
    "family_red":     {"shirt": "#a4262c", "ink": "#f4ead6", "accent": "#2a1d14", "shadow": "#1f5c3a",
                       "extra": "#e7b04b", "colors": ["Crimson", "Red"]},
    "family_ivory":   {"shirt": "#efe8d8", "ink": "#b3232f", "accent": "#2a1d14", "shadow": "#1f5c3a",
                       "extra": "#e7b04b", "colors": ["Ivory"]},
    "snap_butter":    {"shirt": "#f3dfa2", "ink": "#b3232f", "accent": "#2a1d14", "shadow": "#1f5c3a",
                       "extra": "#f7f1e3", "colors": ["Butter", "Ivory"]},
    "treefarm_moss":  {"shirt": "#6b7152", "ink": "#f4ead6", "accent": "#2a1d14", "shadow": "#b3232f",
                       "extra": "#e7b04b", "colors": ["Moss", "Sage"]},
}
PALETTES.update(RETRO_PALETTES)

TREE_BALLS = ["#b3232f", "#e7b04b", "#3f6fa8", "#f4ead6"]


# --- templates ---------------------------------------------------------------------------------
def _t_spooky(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 7000), (0, 0, 0, 0))
    g = ghost(2300, "#f7f3ea", p["shadow"], "#f4a6a0", 70)
    place(c, g, CW / 2, 1500, rotate=6)
    dr = ImageDraw.Draw(c)
    for x, y, r in ((1500, 900, 170), (5600, 1300, 130), (1900, 2300, 100), (5300, 500, 90)):
        sparkle(dr, x, y, r, p["extra"])
    retro_text(c, d.text.get("main", "Spooky"), font("shrikhand", 1500), CW / 2, 3600, p["ink"], p["accent"], 55,
               p["shadow"], 150, tracking=10, wave=110, wave_len=2600)
    retro_text(c, d.text.get("sub", "SEASON"), font("alfa-slab-one", 640), CW / 2, 5000, p["accent"],
               tracking=190)
    for sx in (-1, 1):
        star5(dr, CW / 2 + sx * 2750, 5000, 150, p["ink"])
    return finish(c)


def _t_boo(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 6200), (0, 0, 0, 0))
    for x, s, rot, y in ((1850, 1500, 12, 1500), (3600, 2000, 0, 1250), (5350, 1250, -12, 1650)):
        place(c, ghost(s, "#fbf8f1", p["accent"], p["extra"], 60), x, y, rotate=rot)
    retro_text(c, d.text.get("main", "Boo Crew"), font("cherry-bomb-one", 1450), CW / 2, 3500, p["ink"],
               p["accent"], 60, p["shadow"], 130, tracking=20, bend=260)
    tag = d.text.get("tag", "")
    if tag:
        retro_text(c, tag, font("alfa-slab-one", 480), CW / 2, 4650, p["accent"], tracking=150)
    return finish(c)


def _t_pumpkin(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 6400), (0, 0, 0, 0))
    burst = sunburst(4200, p["shadow"])
    circle = Image.new("L", burst.size, 0)
    ImageDraw.Draw(circle).ellipse([160, 160, burst.width - 160, burst.height - 160], fill=255)
    burst.putalpha(ImageChops.multiply(burst.getchannel("A"), circle))
    place(c, burst, CW / 2, 2400)
    place(c, pumpkin(2600, "#e8742a", "#c95a1c", "#6b4a2b", p["extra"], p["accent"], 65), CW / 2, 2350)
    retro_text(c, d.text.get("main", "Hey Pumpkin"), font("pacifico", 1050), CW / 2, 4500, p["ink"],
               "#f7f1e3", 60, p["accent"], 110, tracking=10, wave=70, wave_len=4200)
    return finish(c)


def _t_cozy(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 6600), (0, 0, 0, 0))
    retro_text(c, d.text.get("main", "Cozy"), font("shrikhand", 1500), CW / 2, 1100, p["ink"], p["accent"], 55,
               p["shadow"], 140, tracking=20, bend=220)
    place(c, mug(2100, "#f4ead6", p["shadow"], "#6b4a2b", p["shadow"], p["accent"], p["extra"], 60), CW / 2, 3350)
    retro_text(c, d.text.get("sub", "SEASON"), font("alfa-slab-one", 620), CW / 2, 5300, p["ink"],
               tracking=200)
    dr = ImageDraw.Draw(c)
    for sx in (-1, 1):
        sparkle(dr, CW / 2 + sx * 2600, 5300, 170, p["extra"])
    return finish(c)


def _t_thankful(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 5200), (0, 0, 0, 0))
    place(c, sunset(5600, ["#8a3a1e", "#c9571b", "#e7b04b", "#f0cf85"]), CW / 2, 1750)
    retro_text(c, d.text.get("main", "Thankful"), font("pacifico", 1500), CW / 2, 3150, p["ink"], p["accent"], 70,
               "#2a1d14", 110, tracking=10)
    retro_text(c, d.text.get("sub", "GRATEFUL  •  BLESSED"), font("alfa-slab-one", 400), CW / 2, 4450,
               p["ink"], tracking=110)
    return finish(c)


def _t_merry(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 6000), (0, 0, 0, 0))
    retro_text(c, d.text.get("main", "Merry"), font("shrikhand", 1700), CW / 2, 1500, p["ink"], p["accent"], 60,
               p["shadow"], 150, tracking=15, wave=120, wave_len=2800)
    retro_text(c, d.text.get("sub", "& Bright"), font("shrikhand", 1450), CW / 2, 3400, p["shadow"], p["accent"],
               60, p["ink"], 130, tracking=15, wave=-110, wave_len=2800)
    dr = ImageDraw.Draw(c)
    for x, y, r, col in ((700, 700, 230, p["extra"]), (6500, 1100, 180, p["extra"]), (900, 3700, 150, p["ink"]),
                         (6300, 3900, 220, p["extra"]), (3600, 4900, 170, p["ink"]), (5200, 250, 120, p["ink"])):
        sparkle(dr, x, y, r, col)
    return finish(c)


def _t_jolly(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 5800), (0, 0, 0, 0))
    f = font("bagel-fat-one", 1600)
    retro_text(c, d.text.get("main", "Holly"), f, CW / 2, 1300, p["ink"], p["accent"], 55, p["shadow"], 140,
               tracking=30)
    retro_text(c, d.text.get("sub", "Jolly"), f, CW / 2, 3300, p["ink"], p["accent"], 55, p["shadow"], 140,
               tracking=30)
    h = holly(1600, "#2f7a45", "#d6322c", p["accent"], 45)
    place(c, h, 1000, 2300, rotate=25)
    place(c, h, 6200, 2300, rotate=-25)
    tag = d.text.get("tag", "VIBES ONLY")
    retro_text(c, tag, font("alfa-slab-one", 420), CW / 2, 4700, p["accent"], tracking=180)
    return finish(c)


def _t_family(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 7400), (0, 0, 0, 0))
    retro_text(c, d.text.get("top", "The Smith Family"), font("pacifico", 950), CW / 2, 900, p["ink"],
               tracking=5, bend=180)
    t = tree(2600, "#2f7a45", "#246339", "#6b4a2b", p["extra"], TREE_BALLS, "#f4ead6", p["accent"], 55)
    place(c, t, CW / 2, 3300)
    retro_text(c, d.text.get("main", "CHRISTMAS"), font("alfa-slab-one", 900), CW / 2, 5600, p["ink"],
               p["accent"], 30, p["shadow"], 90, tracking=120)
    retro_text(c, d.text.get("sub", "2026"), font("alfa-slab-one", 560), CW / 2, 6650, p["ink"], tracking=260)
    dr = ImageDraw.Draw(c)
    for x, y, r in ((1300, 2200, 170), (5900, 2600, 140), (1700, 4300, 110), (5500, 4200, 180)):
        sparkle(dr, x, y, r, p["extra"])
    return finish(c)


def _t_snap(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, 6800), (0, 0, 0, 0))
    retro_text(c, d.text.get("main", "Oh Snap!"), font("cherry-bomb-one", 1350), CW / 2, 1000, p["ink"],
               p["extra"], 55, p["accent"], 120, tracking=20, bend=200)
    place(c, gingerbread(3000, "#b9713a", "#fbf6ea", ["#b3232f", "#2f7a45"], p["accent"], 60), CW / 2, 3900,
          rotate=-6)
    return finish(c)


def _t_treefarm(d: Design, p: dict, fonts: dict) -> Image.Image:
    c = Image.new("RGBA", (CW, CW), (0, 0, 0, 0))
    dr = ImageDraw.Draw(c)
    cx = cy = CW / 2
    for r, w in ((3450, 70), (2500, 40)):
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=_rgba(p["ink"]), width=w)
    fr = font("alfa-slab-one", 430)
    arc(d.text.get("top", "CHRISTMAS TREE FARM"), fr, p["ink"], 2960, (cx, cy), tracking=55, canvas=c)
    arc(d.text.get("bottom", "FRESH CUT • EST. 1994"), fr, p["ink"], 2960, (cx, cy), tracking=55, bottom=True,
        canvas=c)
    for sx in (-1, 1):
        star5(dr, cx + sx * 2960, cy, 170, p["extra"])
    t = tree(2900, "#2f7a45", "#246339", "#6b4a2b", p["extra"], TREE_BALLS, "#f4ead6", p["accent"], 55)
    place(c, t, cx, cy + 60)
    return finish(c)


RETRO_TEMPLATES = {"spooky": _t_spooky, "boo": _t_boo, "pumpkin": _t_pumpkin, "cozy": _t_cozy,
                   "thankful": _t_thankful, "merry": _t_merry, "jolly": _t_jolly, "family_xmas": _t_family,
                   "snap": _t_snap, "treefarm": _t_treefarm}
TEMPLATES.update(RETRO_TEMPLATES)


def holiday_collection(surname: str = "Smith", year: str = "2026") -> list[Design]:
    """The launch line, in the order to list them: Halloween first (sells until ~Oct 25),
    then fall, then Christmas (Etsy's biggest weeks are mid-Nov to mid-Dec)."""
    fam = f"The {surname.title()} Family"
    return [
        Design("spooky_season", "spooky", "spooky_pepper", {"main": "Spooky", "sub": "SEASON"},
               ["spooky season shirt", "halloween shirt", "cute ghost shirt", "retro halloween", "fall shirt",
                "ghost tee", "halloween tee women"],
               title="Spooky Season Shirt, Cute Ghost Halloween Tee, Retro Halloween Shirt, Comfort Colors "
                     "Spooky Shirt, Fall Shirt for Women", wear=0.06),
        Design("boo_crew", "boo", "boo_ivory", {"main": "Boo Crew", "tag": f"{surname.upper()} FAMILY"},
               ["boo crew shirt", "family halloween", "matching halloween", "ghost shirt", "halloween shirt",
                "custom halloween", "kids halloween shirt"],
               personalizable=True,
               title="Boo Crew Shirt, Matching Family Halloween Shirts, Personalized Halloween Tee, Cute Ghost "
                     "Shirt, Custom Family Name Halloween", wear=0.05),
        Design("hey_pumpkin", "pumpkin", "pumpkin_ivory", {"main": "Hey Pumpkin"},
               ["pumpkin shirt", "fall shirt", "hey pumpkin", "thanksgiving shirt", "autumn tee",
                "retro fall shirt", "pumpkin patch shirt"],
               title="Hey Pumpkin Shirt, Retro Fall Tee, Cute Pumpkin Shirt, Thanksgiving Shirt, Comfort Colors "
                     "Autumn Shirt, Pumpkin Patch Tee", wear=0.05),
        Design("cozy_season", "cozy", "cozy_espresso", {"main": "Cozy", "sub": "SEASON"},
               ["cozy season shirt", "fall shirt", "coffee shirt", "autumn tee", "cozy shirt", "fall vibes",
                "coffee lover gift"],
               title="Cozy Season Shirt, Retro Fall Coffee Tee, Autumn Shirt for Women, Cozy Vibes Tee, Comfort "
                     "Colors Fall Shirt, Coffee Lover Gift", wear=0.06),
        Design("thankful", "thankful", "thankful_ivory", {"main": "Thankful", "sub": "GRATEFUL  •  BLESSED"},
               ["thankful shirt", "thanksgiving shirt", "grateful shirt", "fall shirt", "retro sunset tee",
                "blessed shirt", "thanksgiving tee"],
               title="Thankful Shirt, Retro Thanksgiving Tee, Grateful Blessed Shirt, 70s Sunset Fall Shirt, "
                     "Comfort Colors Thanksgiving Shirt", wear=0.06),
        Design("merry_and_bright", "merry", "merry_ivory", {"main": "Merry", "sub": "& Bright"},
               ["merry and bright", "christmas shirt", "retro christmas", "holiday shirt", "xmas tee",
                "christmas tee women", "cute christmas shirt"],
               title="Merry and Bright Shirt, Retro Christmas Tee, Cute Christmas Shirt for Women, Holiday Shirt, "
                     "Comfort Colors Xmas Tee", wear=0.05),
        Design("holly_jolly", "jolly", "jolly_pepper", {"main": "Holly", "sub": "Jolly", "tag": "VIBES ONLY"},
               ["holly jolly shirt", "christmas shirt", "holly jolly vibes", "retro christmas", "holiday tee",
                "xmas shirt", "christmas gift"],
               title="Holly Jolly Vibes Shirt, Retro Christmas Tee, Holly Jolly Shirt, Holiday Party Shirt, "
                     "Comfort Colors Christmas Shirt", wear=0.05),
        Design("family_christmas_red", "family_xmas", "family_red",
               {"top": fam, "main": "CHRISTMAS", "sub": year},
               ["family christmas", "matching christmas", "custom christmas", "christmas 2026",
                "family pajama tee", "personalized xmas", "christmas shirt"],
               personalizable=True,
               title=f"Family Christmas Shirts {year}, Matching Family Christmas Tee, Personalized Christmas "
                     f"Shirt, Custom Last Name Christmas Shirts", wear=0.04),
        Design("family_christmas_ivory", "family_xmas", "family_ivory",
               {"top": fam, "main": "CHRISTMAS", "sub": year},
               ["family christmas", "matching christmas", "custom christmas", "christmas 2026",
                "family pajama tee", "personalized xmas", "christmas shirt"],
               personalizable=True,
               title=f"Matching Family Christmas Shirts {year}, Personalized Christmas Tree Tee, Custom Family "
                     f"Name Christmas Shirt", wear=0.04),
        Design("oh_snap", "snap", "snap_butter", {"main": "Oh Snap!"},
               ["oh snap shirt", "gingerbread shirt", "funny christmas", "christmas shirt", "gingerbread man",
                "holiday tee", "christmas gift"],
               title="Oh Snap Gingerbread Shirt, Funny Christmas Tee, Cute Gingerbread Man Shirt, Holiday Shirt, "
                     "Comfort Colors Christmas Tee", wear=0.04),
        Design("christmas_tree_farm", "treefarm", "treefarm_moss",
               {"top": "CHRISTMAS TREE FARM", "bottom": "FRESH CUT • EST. 1994"},
               ["tree farm shirt", "christmas tree farm", "christmas shirt", "vintage christmas",
                "holiday shirt", "xmas tee", "christmas tree shirt"],
               title="Christmas Tree Farm Shirt, Vintage Christmas Tee, Fresh Cut Christmas Tree Shirt, Holiday "
                     "Shirt, Comfort Colors Xmas Tee", wear=0.1),
    ]
