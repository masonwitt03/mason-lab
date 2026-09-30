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


def test_holiday_collection_renders_and_lists(tmp_path):
    from mason_lab.retro import holiday_collection
    designs = holiday_collection("garcia", "2027")
    assert len(designs) == 11
    fam = next(d for d in designs if d.name == "family_christmas_red")
    assert fam.text["top"] == "The Garcia Family" and fam.text["sub"] == "2027" and fam.personalizable
    for d in designs:
        check_text(*d.text.values())
        lst = listing_for(d)
        assert lst["title"] == d.title[:140] and len(lst["tags"]) == 13
        assert all(len(t) <= 20 for t in lst["tags"])
    files = save(next(d for d in designs if d.name == "oh_snap"), tmp_path)
    img = __import__("PIL.Image", fromlist=["Image"]).open(files["print"])
    assert img.mode == "RGBA" and img.width <= 3600 and img.info.get("dpi", (0,))[0] > 299


def test_setup_wizard_edits_files_in_place(tmp_path, monkeypatch):
    from mason_lab.setup_wizard import set_config, set_env
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "notify:\n  ntfy:     {enabled: true}\ndesigns:\n  printify_shop_id:          # fill in\n"
        "agents:\n  crypto:\n    bankroll_usd: 500          # money\n")
    assert set_config("bankroll_usd", "250") and set_config("printify_shop_id", "42")
    text = (tmp_path / "config.yaml").read_text()
    assert "    bankroll_usd: 250          # money" in text and "  printify_shop_id: 42          # fill in" in text
    (tmp_path / ".env").write_text("NTFY_TOPIC=old\nPRINTIFY_TOKEN=\n")
    set_env("NTFY_TOPIC", "new")
    set_env("X_BEARER_TOKEN", "t")
    assert (tmp_path / ".env").read_text() == "NTFY_TOPIC=new\nPRINTIFY_TOKEN=\nX_BEARER_TOKEN=t\n"
