"""
API Routes
"""

from .markets import router as markets_router
from .klines import router as klines_router
from .whales import router as whales_router
from .ws import router as ws_router
from .metrics import router as metrics_router
from .categories import router as categories_router
from .traders import router as traders_router

__all__ = [
    "markets_router",
    "klines_router",
    "whales_router",
    "ws_router",
    "metrics_router",
    "categories_router",
    "traders_router",
]
