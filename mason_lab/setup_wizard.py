"""`python -m mason_lab setup`: answers a few questions and fills in config.yaml and .env for you."""
from __future__ import annotations

import os
import random
import re
import shutil
import string
from pathlib import Path


def set_env(key: str, value: str, path: Path = Path(".env")) -> None:
    lines = path.read_text().splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")
    os.environ[key] = value


def set_config(key: str, value: str, section: str | None = None, path: Path = Path("config.yaml")) -> bool:
    """Change `key: value` in config.yaml, keeping comments. With section, only inside that block."""
    text = path.read_text()
    start = 0
    if section:
        m = re.search(rf"^\s*{re.escape(section)}:\s*(#.*)?$", text, re.M)
        if not m:
            return False
        start = m.end()
    m = re.compile(rf"^(\s*{re.escape(key)}:)[^\n#]*?(\s*#.*)?$", re.M).search(text, start)
    if not m:
        return False
    text = text[:m.start()] + f"{m.group(1)} {value}" + (m.group(2) or "") + text[m.end():]
    path.write_text(text)
    return True


def ask(question: str, default: str = "") -> str:
    hint = f" [{default}]" if default else " (press Enter to skip)"
    ans = input(f"\n{question}{hint}\n> ").strip()
    return ans or default


def yes(question: str) -> bool:
    return ask(question + " (y/n)", "n").lower().startswith("y")


def run() -> None:
    print("=" * 60)
    print(" Mason Lab setup. Answer each question and press Enter.")
    print(" You can run this again any time to change your answers.")
    print("=" * 60)
    for src, dst in (("config.example.yaml", "config.yaml"), (".env.example", ".env")):
        if not Path(dst).exists():
            shutil.copy(src, dst)
            print(f"Created {dst}")

    # 1. phone alerts
    current = os.environ.get("NTFY_TOPIC", "")
    if not current or "change-this" in current:
        current = "mason-lab-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    print("\nSTEP 1 of 4: PHONE ALERTS")
    print(" 1. Install the free 'ntfy' app on your phone.")
    print(" 2. Open it, tap +, type the topic name below, tap Subscribe.")
    topic = ask("Your topic name (keep this one, or type your own):", current)
    set_env("NTFY_TOPIC", topic)
    set_config("enabled", "true", "ntfy:")
    if yes("Subscribed in the app? Send a test alert to your phone now?"):
        from .config import load_config
        from .models import HIGH
        from .notify import Notifier
        Notifier(load_config().get("notify", {})).send_text("Mason Lab test", "Your phone alerts work!", HIGH)
        print("Sent! Your phone should buzz in a few seconds. If not, check the topic name matches exactly.")

    # 2. shirts
    print("\nSTEP 2 of 4: SHIRT SHOP (Printify)")
    print(" Get the token at printify.com > profile > Connections > API tokens > Generate.")
    tok = ask("Paste your Printify token:")
    if tok:
        set_env("PRINTIFY_TOKEN", tok)
        try:
            from .agents.base import default_http
            from .printify import Printify
            shops = Printify(default_http(), tok).shops()
            if shops:
                set_config("printify_shop_id", str(shops[0]["id"]))
                print(f"Connected to your shop '{shops[0].get('title')}'.")
            else:
                print("Token works, but no shop is connected yet. Connect Etsy in Printify, then run setup again.")
        except Exception as e:
            print(f"Couldn't reach Printify with that token ({e}). Check it and run setup again.")

    # 3. crypto
    print("\nSTEP 3 of 4: CRYPTO ALERTS")
    money = ask("How much money are you OK losing completely on crypto? (number only, e.g. 200)", "200")
    if re.fullmatch(r"\d+(\.\d+)?", money):
        set_config("bankroll_usd", money)

    # 4. clipping
    print("\nSTEP 4 of 4: CLIPPING (Twitch)")
    print(" Get these at dev.twitch.tv/console > Register Your Application (see GUIDE.md, Part 4).")
    cid = ask("Twitch Client ID:")
    if cid:
        set_env("TWITCH_CLIENT_ID", cid)
        secret = ask("Twitch Client Secret:")
        if secret:
            set_env("TWITCH_CLIENT_SECRET", secret)

    print("\n" + "=" * 60)
    print(" All set! To start everything, run:  python -m mason_lab run")
    print(" (or double-click Start-Mac.command / Start-Windows.bat)")
    print("=" * 60)
