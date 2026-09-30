"""CLI for the controller.

  python -m mason_lab run               # start the controller (runs forever)
  python -m mason_lab once crypto       # run one agent right now and send its alerts
  python -m mason_lab digest            # print + send the daily briefing now
  python -m mason_lab test-notify       # check your phone/Discord/Telegram setup
"""
from __future__ import annotations

import argparse
import logging

from .config import load_config, load_dotenv
from .models import HIGH
from .orchestrator import Controller


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
    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    ctl = Controller(load_config(args.config))

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


if __name__ == "__main__":
    main()
