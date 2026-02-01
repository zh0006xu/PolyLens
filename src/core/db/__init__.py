"""
Database module
"""

from .schema import init_db, reset_db
from .store import (
    upsert_event,
    upsert_market,
    fetch_market_by_slug,
    fetch_market_by_token_id,
    insert_trade,
    get_sync_state,
    set_sync_state,
)

__all__ = [
    "init_db",
    "reset_db",
    "upsert_event",
    "upsert_market",
    "fetch_market_by_slug",
    "fetch_market_by_token_id",
    "insert_trade",
    "get_sync_state",
    "set_sync_state",
]