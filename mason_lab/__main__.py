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
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    cfg = load_config(args.config)
    if args.cmd == "vintage":
        return vintage_cmd(args, cfg)
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


if __name__ == "__main__":
    main()
