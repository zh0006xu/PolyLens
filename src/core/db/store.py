"""
数据存储层 - CRUD 操作封装
"""

import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone


def _get_status(data: Dict[str, Any]) -> str:
    """从 Gamma API 数据推断状态"""
    if data.get("status"):
        return data["status"]
    if data.get("archived"):
        return "archived"
    if data.get("closed"):
        return "closed"
    if data.get("active") is False:
        return "closed"
    return "active"


# =============================================================================
# Events CRUD
# =============================================================================


def upsert_event(conn: sqlite3.Connection, event: Dict[str, Any]) -> int:
    """插入或更新事件"""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM events WHERE slug = ?", (event.get("slug"),))
    row = cursor.fetchone()

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status = _get_status(event)

    if row:
        event_id = row[0]
        cursor.execute(
            """
            UPDATE events SET
                title = COALESCE(?, title),
                description = COALESCE(?, description),
                category = COALESCE(?, category),
                start_date = COALESCE(?, start_date),
                end_date = COALESCE(?, end_date),
                image = COALESCE(?, image),
                icon = COALESCE(?, icon),
                status = COALESCE(?, status),
                enable_neg_risk = COALESCE(?, enable_neg_risk),
                updated_at = ?
            WHERE id = ?
            """,
            (
                event.get("title"),
                event.get("description"),
                event.get("category"),
                event.get("start_date") or event.get("startDate"),
                event.get("end_date") or event.get("endDate"),
                event.get("image"),
                event.get("icon"),
                status,
                event.get("enable_neg_risk") or event.get("enableNegRisk"),
                now,
                event_id,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO events (
                slug, title, description, category, start_date, end_date,
                image, icon, status, enable_neg_risk,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.get("slug"),
                event.get("title"),
                event.get("description"),
                event.get("category"),
                event.get("start_date") or event.get("startDate"),
                event.get("end_date") or event.get("endDate"),
                event.get("image"),
                event.get("icon"),
                status,
                event.get("enable_neg_risk") or event.get("enableNegRisk") or False,
                now,
                now,
            ),
        )
        event_id = cursor.lastrowid

    conn.commit()
    return event_id


def fetch_event_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[Dict]:
    """按 slug 查询事件"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM events WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    return dict(row) if row else None


# =============================================================================
# Markets CRUD
# =============================================================================


def upsert_market(conn: sqlite3.Connection, market: Dict[str, Any]) -> int:
    """插入或更新市场"""
    cursor = conn.cursor()

    condition_id = market.get("condition_id") or market.get("conditionId")
    if not condition_id:
        raise ValueError("market must have condition_id")

    cursor.execute("SELECT id FROM markets WHERE condition_id = ?", (condition_id,))
    row = cursor.fetchone()

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 解析数值字段
    def parse_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    if row:
        market_id = row[0]
        cursor.execute(
            """
            UPDATE markets SET
                event_id = COALESCE(?, event_id),
                slug = COALESCE(?, slug),
                question_id = COALESCE(?, question_id),
                oracle = COALESCE(?, oracle),
                collateral_token = COALESCE(?, collateral_token),
                yes_token_id = COALESCE(?, yes_token_id),
                no_token_id = COALESCE(?, no_token_id),
                enable_neg_risk = COALESCE(?, enable_neg_risk),
                status = COALESCE(?, status),
                question = COALESCE(?, question),
                description = COALESCE(?, description),
                outcomes = COALESCE(?, outcomes),
                outcome_prices = COALESCE(?, outcome_prices),
                end_date = COALESCE(?, end_date),
                image = COALESCE(?, image),
                icon = COALESCE(?, icon),
                category = COALESCE(?, category),
                volume = COALESCE(?, volume),
                volume_24h = COALESCE(?, volume_24h),
                liquidity = COALESCE(?, liquidity),
                best_bid = COALESCE(?, best_bid),
                best_ask = COALESCE(?, best_ask),
                sync_warning = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                market.get("event_id"),
                market.get("slug"),
                market.get("question_id") or market.get("questionID"),
                market.get("oracle") or market.get("resolvedBy"),
                market.get("collateral_token") or market.get("collateralToken"),
                market.get("yes_token_id") or market.get("yesTokenId"),
                market.get("no_token_id") or market.get("noTokenId"),
                market.get("enable_neg_risk") or market.get("negRisk"),
                _get_status(market),
                market.get("question"),
                market.get("description"),
                market.get("outcomes"),
                market.get("outcome_prices") or market.get("outcomePrices"),
                market.get("end_date") or market.get("endDate"),
                market.get("image"),
                market.get("icon"),
                market.get("category"),
                parse_float(market.get("volume") or market.get("volumeNum")),
                parse_float(market.get("volume_24h") or market.get("volume24hr")),
                parse_float(market.get("liquidity") or market.get("liquidityNum")),
                parse_float(market.get("best_bid") or market.get("bestBid")),
                parse_float(market.get("best_ask") or market.get("bestAsk")),
                market.get("sync_warning"),
                now,
                market_id,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO markets (
                event_id, slug, condition_id, question_id, oracle,
                collateral_token, yes_token_id, no_token_id, enable_neg_risk,
                status, question, description, outcomes, outcome_prices,
                end_date, image, icon, category, volume, volume_24h,
                liquidity, best_bid, best_ask, sync_warning,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market.get("event_id"),
                market.get("slug"),
                condition_id,
                market.get("question_id") or market.get("questionID"),
                market.get("oracle") or market.get("resolvedBy"),
                market.get("collateral_token") or market.get("collateralToken"),
                market.get("yes_token_id") or market.get("yesTokenId"),
                market.get("no_token_id") or market.get("noTokenId"),
                market.get("enable_neg_risk") or market.get("negRisk") or False,
                _get_status(market),
                market.get("question"),
                market.get("description"),
                market.get("outcomes"),
                market.get("outcome_prices") or market.get("outcomePrices"),
                market.get("end_date") or market.get("endDate"),
                market.get("image"),
                market.get("icon"),
                market.get("category"),
                parse_float(market.get("volume") or market.get("volumeNum")),
                parse_float(market.get("volume_24h") or market.get("volume24hr")),
                parse_float(market.get("liquidity") or market.get("liquidityNum")),
                parse_float(market.get("best_bid") or market.get("bestBid")),
                parse_float(market.get("best_ask") or market.get("bestAsk")),
                market.get("sync_warning"),
                now,
                now,
            ),
        )
        market_id = cursor.lastrowid

    conn.commit()
    return market_id


def fetch_market_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[Dict]:
    """按 slug 查询市场"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM markets WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    return dict(row) if row else None


def fetch_market_by_condition_id(conn: sqlite3.Connection, condition_id: str) -> Optional[Dict]:
    """按 condition_id 查询市场"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM markets WHERE condition_id = ?", (condition_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def fetch_market_by_token_id(conn: sqlite3.Connection, token_id: str) -> Optional[Dict]:
    """按 token_id 查询市场"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM markets WHERE yes_token_id = ? OR no_token_id = ?",
        (token_id, token_id),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def fetch_markets_by_event_id(conn: sqlite3.Connection, event_id: int) -> List[Dict]:
    """获取事件下的所有市场"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM markets WHERE event_id = ?", (event_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def fetch_all_markets(conn: sqlite3.Connection, limit: int = 100, offset: int = 0) -> List[Dict]:
    """获取所有市场 (分页)"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM markets ORDER BY id LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_all_condition_ids(conn: sqlite3.Connection) -> set:
    """获取数据库中所有市场的 condition_id 集合"""
    cursor = conn.cursor()
    cursor.execute("SELECT condition_id FROM markets")
    rows = cursor.fetchall()
    return {row[0] for row in rows}


# =============================================================================
# Sync State CRUD
# =============================================================================


def get_sync_state(conn: sqlite3.Connection, key: str) -> Optional[int]:
    """获取同步状态"""
    cursor = conn.cursor()
    cursor.execute("SELECT last_block FROM sync_state WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def set_sync_state(conn: sqlite3.Connection, key: str, last_block: int) -> None:
    """设置同步状态"""
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    cursor.execute(
        """
        INSERT INTO sync_state (key, last_block, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            last_block = excluded.last_block,
            updated_at = excluded.updated_at
        """,
        (key, last_block, now),
    )
    conn.commit()


# =============================================================================
# Trades CRUD
# =============================================================================


def insert_trade(conn: sqlite3.Connection, trade: Dict[str, Any]) -> Optional[int]:
    """插入交易记录 (幂等，重复插入会被忽略)"""
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO trades (
                market_id, tx_hash, log_index, block_number,
                maker, taker, side, outcome, price, size, fee,
                token_id, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.get("market_id"),
                trade.get("tx_hash"),
                trade.get("log_index"),
                trade.get("block_number"),
                trade.get("maker"),
                trade.get("taker"),
                trade.get("side"),
                trade.get("outcome"),
                trade.get("price"),
                trade.get("size"),
                trade.get("fee"),
                trade.get("token_id"),
                trade.get("timestamp"),
            ),
        )
        # Update trade_count in markets table
        market_id = trade.get("market_id")
        if market_id:
            cursor.execute(
                "UPDATE markets SET trade_count = trade_count + 1 WHERE id = ?",
                (market_id,),
            )
        # conn.commit()  <-- Defer commit to caller
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def insert_trades(conn: sqlite3.Connection, trades: List[Dict[str, Any]]) -> int:
    """批量插入交易记录 (幂等)"""
    inserted = 0
    for trade in trades:
        if insert_trade(conn, trade) is not None:
            inserted += 1
    conn.commit()
    return inserted


def fetch_trades_for_market(
    conn: sqlite3.Connection,
    market_id: int,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict]:
    """获取市场的交易记录 (分页)"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM trades WHERE market_id = ?
        ORDER BY block_number, log_index LIMIT ? OFFSET ?
        """,
        (market_id, limit, offset),
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def fetch_trades_by_token_id(
    conn: sqlite3.Connection,
    token_id: str,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict]:
    """按 token_id 获取交易记录"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM trades
        WHERE token_id = ?
        ORDER BY block_number, log_index
        LIMIT ? OFFSET ?
        """,
        (token_id, limit, offset),
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]