"""
Trader level helpers (PHASE5 rules).
"""

from __future__ import annotations

import os
import re
import time
from typing import Dict, List, Optional

import httpx


ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
DATA_API_BASE = os.getenv("POLYMARKET_DATA_API_BASE", "https://data-api.polymarket.com")
MAX_TRADES_FOR_LEVEL = int(os.getenv("TRADER_LEVEL_MAX_TRADES", "10000"))
LEVEL_CACHE_TTL_SEC = int(os.getenv("TRADER_LEVEL_CACHE_TTL_SEC", "600"))

_level_cache: Dict[str, tuple[float, Optional[str]]] = {}


def _normalize_address(address: str) -> str:
    return address.lower()


def _calc_whale_level(max_trade: float, max_market: float) -> Optional[str]:
    if max_trade >= 10000 and max_market >= 50000:
        return "whale"
    if max_trade >= 5000 and max_market >= 10000:
        return "shark"
    if (500 <= max_trade < 5000) or (2000 <= max_market < 10000):
        return "dolphin"
    return "fish"


def _fetch_trades(address: str, limit: int) -> List[Dict]:
    response = httpx.get(
        f"{DATA_API_BASE}/trades",
        params={
            "user": address,
            "takerOnly": False,
            "limit": limit,
            "offset": 0,
        },
        timeout=20.0,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def compute_whale_level(address: str) -> Optional[str]:
    if not address or not ADDRESS_RE.match(address):
        return None
    normalized = _normalize_address(address)

    now = time.time()
    cached = _level_cache.get(normalized)
    if cached and (now - cached[0]) < LEVEL_CACHE_TTL_SEC:
        return cached[1]

    trades = _fetch_trades(normalized, MAX_TRADES_FOR_LEVEL)
    if not trades:
        level = None
    else:
        max_trade_value = 0.0
        market_totals: Dict[str, float] = {}
        for trade in trades:
            price = float(trade.get("price") or 0)
            size = float(trade.get("size") or 0)
            usd_value = price * size
            max_trade_value = max(max_trade_value, usd_value)

            condition_id = trade.get("conditionId")
            if condition_id:
                market_totals[condition_id] = market_totals.get(condition_id, 0.0) + usd_value

        max_market_volume = max(market_totals.values()) if market_totals else 0.0
        level = _calc_whale_level(max_trade_value, max_market_volume)

    _level_cache[normalized] = (now, level)
    return level
