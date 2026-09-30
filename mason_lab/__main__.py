"""CLI for the controller.

  python -m mason_lab run               # start the controller (runs forever)
  python -m mason_lab once crypto       # run one agent right now and send its alerts
  python -m mason_lab digest            # print + send the daily briefing now
  python -m mason_lab test-notify       # check your phone/Discord/Telegram setup

Vintage inventory:
  python -m mason_lab vintage add "90s Champion Michigan tee, L, small stain" --cost 4
  python -m mason_lab vintage sold 12 38 --platform depop --shipping 0
  python -m mason_lab vintage price 12 32.99
  python -m mason_lab vintage list | stats | listing 12 | delete 12

Shirt designs (print-on-demand):
  python -m mason_lab shirts collection --surname SMITH --town AUSTIN
  python -m mason_lab shirts make my_tee --template arch --palette cream_on_navy --top AUSTIN --main ATHLETICS --est "EST. 1839"
  python -m mason_lab shirts options
  python -m mason_lab shirts printify-setup
  python -m mason_lab shirts upload gameday_red_black
"""
from __future__ import annotations

import argparse
import logging

from .config import load_config, load_dotenv
from .models import HIGH
from .orchestrator import Controller
from .store import Store
from .vintage import DEFAULT_FEES, Inventory, listing_copy, parse_note, profit, stats


def main() -> None:
    ap = argparse.ArgumentParser(prog="mason_lab")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    one = sub.add_parser("once")
    one.add_argument("agent")
    sub.add_parser("digest")
    sub.add_parser("test-notify")
    v = sub.add_parser("vintage").add_subparsers(dest="vcmd", required=True)
    va = v.add_parser("add", help="log a piece you bought and print its listing copy")
    va.add_argument("note")
    va.add_argument("--cost", type=float, default=0.0)
    va.add_argument("--price", type=float, help="asking price (default: suggested)")
    for f in ("school", "brand", "decade", "size", "kind", "event"):
        va.add_argument(f"--{f}")
    va.add_argument("--p2p", type=float, help="pit to pit, inches")
    va.add_argument("--length", type=float, help="length, inches")
    vs = v.add_parser("sold")
    vs.add_argument("id", type=int)
    vs.add_argument("price", type=float)
    vs.add_argument("--platform", default="depop", choices=sorted(DEFAULT_FEES))
    vs.add_argument("--fees", type=float, help="actual fees if you know them (default: estimated)")
    vs.add_argument("--shipping", type=float, default=0.0, help="shipping you paid")
    vp = v.add_parser("price")
    vp.add_argument("id", type=int)
    vp.add_argument("price", type=float)
    for name in ("listing", "delete"):
        v.add_parser(name).add_argument("id", type=int)
    v.add_parser("list")
    v.add_parser("stats")
    sh = sub.add_parser("shirts").add_subparsers(dest="scmd", required=True)
    sc = sh.add_parser("collection", help="make the starter collection of designs")
    sc.add_argument("--surname", default="SMITH")
    sc.add_argument("--town", default="HOMETOWN")
    sc.add_argument("--year", default="1994")
    sm = sh.add_parser("make", help="make one custom design")
    sm.add_argument("name")
    sm.add_argument("--template", required=True)
    sm.add_argument("--palette", required=True)
    for f in ("top", "main", "sub", "est", "bottom", "tag"):
        sm.add_argument(f"--{f}")
    sm.add_argument("--keywords", default="", help="comma separated search words for the listing")
    sm.add_argument("--personalizable", action="store_true")
    sub.add_parser("youtube-auth", help="one-time YouTube login; prints your YT_REFRESH_TOKEN")
    sh.add_parser("options", help="list templates and color palettes")
    sh.add_parser("printify-setup", help="find your Printify shop id and shirt ids")
    su = sh.add_parser("upload", help="send a design to Printify as a draft product")
    su.add_argument("name")
    su.add_argument("--price", type=float)
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    cfg = load_config(args.config)
    if args.cmd == "vintage":
        return vintage_cmd(args, cfg)
    if args.cmd == "shirts":
        return shirts_cmd(args, cfg)
    if args.cmd == "youtube-auth":
        from .publish import youtube_auth
        print("\nSuccess! Copy this whole line into your .env file:\n\nYT_REFRESH_TOKEN=" + youtube_auth())
        return
    ctl = Controller(cfg)

    if args.cmd == "run":
        ctl.run_forever()
    elif args.cmd == "once":
        if args.agent not in ctl.agents:
            raise SystemExit(f"agent '{args.agent}' is not enabled; enabled: {', '.join(ctl.agents) or 'none'}")
        alerts = ctl.run_agent(args.agent)
        print(f"{len(alerts)} new alerts from {args.agent}")
    elif args.cmd == "digest":
        print(ctl.send_digest())
    elif args.cmd == "test-notify":
        ctl.notifier.send_text("Mason Lab test", "If you can read this, notifications work.", HIGH)


def print_listing(item) -> None:
    c = listing_copy(item)
    print(f"\n#{item.id}  ask ${item.price:.2f}  (suggested ${c['suggested_price']:.2f}, cost ${item.cost:.2f})")
    print(f"\nTITLE: {c['title']}\neBay title ({len(c['ebay_title'])}/80): {c['ebay_title']}")
    print(f"\n--- Depop description ---\n{c['depop_description']}")
    print(f"\nEtsy tags: {', '.join(c['etsy_tags'])}")


def vintage_cmd(args, cfg) -> None:
    inv = Inventory(Store(cfg.get("database", "data/mason_lab.db")).db)
    fee_table = {k: tuple(v) for k, v in ((cfg.get("agents", {}).get("vintage") or {}).get("fees") or {}).items()}
    if args.vcmd == "add":
        item = parse_note(args.note, cost=args.cost, price=args.price, school=args.school, brand=args.brand,
                          decade=args.decade, size=args.size, kind=args.kind, event=args.event,
                          p2p=args.p2p, length=args.length)
        print_listing(inv.add(item))
        missing = [f for f in ("school", "decade", "size") if not getattr(item, f)]
        if missing:
            print(f"\n(couldn't detect {', '.join(missing)} - pass e.g. --{missing[0]} ... to fill it in)")
    elif args.vcmd == "sold":
        item = inv.sell(args.id, args.price, args.platform, args.fees, args.shipping, {**DEFAULT_FEES, **fee_table})
        print(f"#{item.id} sold for ${item.sold_price:.2f} on {item.platform}: fees ${item.fees:.2f}, "
              f"profit ${profit(item):.2f}")
    elif args.vcmd == "price":
        inv.set_price(args.id, args.price)
        print(f"#{args.id} now ${args.price:.2f}")
    elif args.vcmd == "listing":
        print_listing(inv.get(args.id))
    elif args.vcmd == "delete":
        inv.delete(args.id)
        print(f"deleted #{args.id}")
    elif args.vcmd == "list":
        import time
        for i in inv.all(active=True):
            print(f"#{i.id:<4} ${i.price:>7.2f}  {(time.time() - i.listed_at) / 86400:>4.0f}d  "
                  f"{' '.join(filter(None, [i.decade, i.school, i.brand, i.kind, i.size]))}")
    elif args.vcmd == "stats":
        from datetime import datetime
        from .agents.vintage import format_report
        print(format_report(stats(inv.all()), datetime.now().month))


def shirts_cmd(args, cfg) -> None:
    from .designs import PALETTES, TEMPLATES, Design, TrademarkError, load, save, starter_collection

    dcfg = cfg.get("designs") or {}
    out = dcfg.get("output_dir", "data/designs")
    fonts = {"display": dcfg.get("font"), "sans": dcfg.get("sans_font")}
    wear = float(dcfg.get("wear", 0.22))
    if args.scmd == "options":
        print("Templates:", ", ".join(TEMPLATES))
        print("  arch    = arched word on top, big word, 'EST. year'   (text: --top --main --est)")
        print("  dept    = PROPERTY OF / NAME / ATHLETIC DEPT.         (text: --top --main --sub)")
        print("  gameday = GAME (football) DAY + small tag line         (text: --main --sub --tag)")
        print("  badge   = round badge, text around, big middle        (text: --top --bottom --main)")
        print("Palettes:", ", ".join(PALETTES))
        return
    if args.scmd in ("collection", "make"):
        if args.scmd == "collection":
            designs = starter_collection(args.surname, args.town, args.year)
        else:
            text = {k: getattr(args, k) for k in ("top", "main", "sub", "est", "bottom", "tag") if getattr(args, k)}
            kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
            designs = [Design(args.name, args.template, args.palette, text, kws, args.personalizable)]
        for d in designs:
            try:
                files = save(d, out, fonts, wear)
                print(f"made {d.name}: {files['print']}  (preview: {files['mockup']})")
            except TrademarkError as e:
                print(f"SKIPPED {d.name}: {e}")
        return

    from .agents.base import default_http
    from .printify import Printify

    pf = Printify(default_http())
    if args.scmd == "printify-setup":
        for shop in pf.shops():
            print(f"Shop: {shop.get('title')}  id={shop['id']}  ({shop.get('sales_channel')})")
        for term in ("Comfort Colors", "Bella"):
            for b in pf.blueprints(term)[:4]:
                print(f"Shirt: {b['title']} ({b.get('brand')} {b.get('model')})  blueprint_id={b['id']}")
        bp = dcfg.get("printify_blueprint_id")
        if bp:
            for p in pf.providers(int(bp)):
                print(f"  Printer for {bp}: {p['title']}  provider_id={p['id']}")
        print("\nPut shop id, blueprint_id and provider_id under 'designs:' in config.yaml.")
        return
    if args.scmd == "upload":
        need = ("printify_shop_id", "printify_blueprint_id", "printify_provider_id")
        missing = [k for k in need if not dcfg.get(k)]
        if missing:
            raise SystemExit(f"set {', '.join(missing)} under designs: in config.yaml (run 'shirts printify-setup')")
        from pathlib import Path
        folder = next((Path(b) / args.name for b in (out, "shirts") if (Path(b) / args.name / "design.json").exists()),
                      None)
        if not folder:
            raise SystemExit(f"no design called '{args.name}' in {out}/ or shirts/")
        d = load(folder)
        prod = pf.create_product(int(dcfg["printify_shop_id"]), d, folder / "print.png",
                                 int(dcfg["printify_blueprint_id"]), int(dcfg["printify_provider_id"]),
                                 args.price or float(dcfg.get("price", 29.99)))
        print(f"Created draft product {prod.get('id')} in Printify. Open Printify > My Products to check the "
              f"mockups, then press Publish to send it to Etsy.")


if __name__ == "__main__":
    main()
