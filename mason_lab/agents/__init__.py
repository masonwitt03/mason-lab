from .base import Agent, AgentContext
from .clipper import ClipperAgent
from .crypto import CryptoAgent
from .etsy import EtsyAgent
from .vintage import VintageAgent
from .x_watch import XWatchAgent

REGISTRY: dict[str, type[Agent]] = {
    "vintage": VintageAgent,
    "etsy": EtsyAgent,
    "clipper": ClipperAgent,
    "crypto": CryptoAgent,
    "x_watch": XWatchAgent,
}

__all__ = ["Agent", "AgentContext", "REGISTRY"]
