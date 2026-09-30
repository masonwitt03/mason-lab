import json

import pytest

from mason_lab.designs import (Design, TrademarkError, check_text, listing_for, load, render, save,
                               starter_collection)
from mason_lab.printify import Printify

from fakes import FakeHTTP


def test_trademarks_are_blocked():
    for bad in ["MICHIGAN", "Ohio State Athletics", "Disney Club", "NFL Sundays"]:
        with pytest.raises(TrademarkError):
            check_text(bad)
    check_text("AUSTIN ATHLETICS", "SMITH", "GAME DAY", "COFFEE CLUB")


@pytest.mark.parametrize("template,text", [
    ("arch", {"top": "WEEKEND", "main": "CLUB", "est": "EST. 1994"}),
    ("dept", {"top": "PROPERTY OF", "main": "SMITH", "sub": "ATHLETIC DEPT."}),
    ("gameday", {"main": "GAME", "sub": "DAY", "tag": "SATURDAYS"}),
    ("badge", {"top": "LAKE LIFE", "bottom": "ROWING CLUB", "main": "94"}),
])
def test_templates_render_transparent_print_files(template, text):
    img = render(Design("t", template, "navy_on_ivory", text), wear=0.1)
    assert img.mode == "RGBA" and 1500 < img.width <= 3600
    assert img.getpixel((0, 0))[3] == 0  # transparent background
    assert img.getchannel("A").getbbox() is not None


def test_save_writes_print_mockup_and_listing(tmp_path):
    d = starter_collection(surname="garcia")[10]
    files = save(d, tmp_path, wear=0)
    data = json.loads(open(files["json"]).read())
    assert data["text"]["main"] == "GARCIA" and data["listing"]["personalizable"]
    assert load(tmp_path / d.name) == d
    lst = listing_for(d)
    assert len(lst["title"]) <= 140 and len(lst["tags"]) <= 13 and all(len(t) <= 20 for t in lst["tags"])
    assert "production partner" in lst["description"]


def test_starter_collection_is_trademark_clean():
    for d in starter_collection():
        check_text(*d.text.values())


def test_printify_creates_draft_with_matching_colors(tmp_path):
    d = Design("gd", "gameday", "red_black", {"main": "GAME", "sub": "DAY"})
    files = save(d, tmp_path, wear=0)
    variants = [{"id": 1, "options": {"color": "White", "size": "M"}},
                {"id": 2, "options": {"color": "Black", "size": "M"}},
                {"id": 3, "options": {"color": "White", "size": "2XL"}},
                {"id": 4, "options": {"color": "White", "size": "XS"}}]
    http = FakeHTTP({r"variants\.json": {"variants": variants}, r"uploads/images": {"id": "img1"},
                     r"shops/9/products": {"id": "prod1"}})
    res = Printify(http, "tok").create_product(9, d, files["print"], 5, 6, 29.99)
    assert res["id"] == "prod1"
    body = json.loads(next(c for c in http.calls if "products.json" in c[1])[2]["data"])
    assert {v["id"]: v["price"] for v in body["variants"]} == {1: 2999, 3: 3299}
    assert body["print_areas"][0]["placeholders"][0]["images"][0]["id"] == "img1"
