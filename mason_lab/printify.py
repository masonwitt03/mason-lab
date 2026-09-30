"""Printify: turns a design into a real product that gets printed and shipped when someone orders.

Printify connects to your Etsy shop. We create the product as a draft; you check it in Printify
and press Publish, which puts the listing on Etsy.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from .config import env
from .designs import PALETTES, Design, listing_for

API = "https://api.printify.com/v1"


class Printify:
    def __init__(self, http: Any, token: str | None = None):
        self.http = http
        self.hdr = {"Authorization": f"Bearer {token or env('PRINTIFY_TOKEN')}", "Content-Type": "application/json"}

    def _get(self, path: str, **kw) -> Any:
        r = self.http.get(API + path, headers=self.hdr, timeout=30, **kw)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> Any:
        r = self.http.post(API + path, headers=self.hdr, data=json.dumps(body), timeout=120)
        r.raise_for_status()
        return r.json()

    def shops(self) -> list[dict]:
        return self._get("/shops.json")

    def blueprints(self, search: str = "") -> list[dict]:
        items = self._get("/catalog/blueprints.json")
        s = search.lower()
        return [b for b in items if s in (b.get("title", "") + " " + b.get("brand", "") + " "
                                          + b.get("model", "")).lower()]

    def providers(self, blueprint_id: int) -> list[dict]:
        return self._get(f"/catalog/blueprints/{blueprint_id}/print_providers.json")

    def variants(self, blueprint_id: int, provider_id: int) -> list[dict]:
        res = self._get(f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json")
        return res.get("variants", res) if isinstance(res, dict) else res

    def upload(self, path: str | Path) -> str:
        data = base64.b64encode(Path(path).read_bytes()).decode()
        return self._post("/uploads/images.json", {"file_name": Path(path).name, "contents": data})["id"]

    def create_product(self, shop_id: int, d: Design, print_png: str | Path, blueprint_id: int, provider_id: int,
                       price_usd: float, sizes: list[str] | None = None, y: float = 0.38, scale: float = 0.85) -> dict:
        """Create a draft product with only the shirt colors that match the design's palette."""
        wanted_colors = {c.lower() for c in PALETTES[d.palette]["colors"]}
        wanted_sizes = {s.upper() for s in (sizes or ["S", "M", "L", "XL", "2XL", "3XL"])}
        variants = self.variants(blueprint_id, provider_id)
        chosen = [v for v in variants
                  if (v.get("options", {}).get("color", "")).lower() in wanted_colors
                  and (v.get("options", {}).get("size", "")).upper() in wanted_sizes]
        if not chosen:
            colors = sorted({v.get("options", {}).get("color", "?") for v in variants})
            raise ValueError(f"none of {sorted(wanted_colors)} offered here. Available colors: {', '.join(colors)}")
        image_id = self.upload(print_png)
        listing = listing_for(d)
        cents = int(round(price_usd * 100))
        body = {
            "title": listing["title"], "description": listing["description"], "tags": listing["tags"],
            "blueprint_id": blueprint_id, "print_provider_id": provider_id,
            "variants": [{"id": v["id"], "price": cents + (300 if v["options"].get("size", "").upper() in
                                                            ("2XL", "3XL", "4XL") else 0), "is_enabled": True}
                         for v in chosen],
            "print_areas": [{"variant_ids": [v["id"] for v in chosen], "placeholders": [
                {"position": "front", "images": [{"id": image_id, "x": 0.5, "y": y, "scale": scale, "angle": 0}]}]}],
        }
        return self._post(f"/shops/{shop_id}/products.json", body)
