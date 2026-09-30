from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def load_dotenv(path: str | Path = ".env") -> None:
    """Minimal .env loader so secrets never have to live in config.yaml."""
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} not found - copy config.example.yaml to config.yaml and edit it")
    return yaml.safe_load(p.read_text()) or {}


def env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    return val if val else default
