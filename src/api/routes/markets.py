"""
Markets API Routes
"""

import sqlite3
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from ..deps import get_db
from ..utils.trader_levels import compute_whale_level

# Polymarket Data API base URL
POLYMARKET_DATA_API = "https://data-api.polymarket.com"

router = APIRouter(prefix="/markets", tags=["markets"])


class MarketResponse(BaseModel):
    id: int
    slug: str
    question: Optional[str] = None
    status: Optional[str] = None
    yes_token_id: Optional[str] = None
    no_token_id: Optional[str] = None
    outcomes: Optional[str] = None
    outcome_prices: Optional[str] = None
    trade_count: int = 0
    volume_24h: float = 0.0
    # Extended fields for frontend
    image: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    end_date: Optional[str] = None
    volume: float = 0.0
    liquidity: float = 0.0
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    # Latest trade prices
    latest_yes_price: Optional[float] = None
    latest_no_price: Optional[float] = None
    # Event slug for Polymarket URL
    event_slug: Optional[str] = None


class MarketListResponse(BaseModel):
    markets: List[MarketResponse]
    total: int
    has_more: bool = False


class HolderResponse(BaseModel):
    proxyWallet: Optional[str] = None
    pseudonym: Optional[str] = None
    amount: float = 0.0
    outcomeIndex: Optional[int] = None
    profileImage: Optional[str] = None
    name: Optional[str] = None
    displayUsernamePublic: Optional[bool] = None
    whale_level: Optional[str] = None


class MarketHoldersResponse(BaseModel):
    token: Optional[str] = None
    holders: List[HolderResponse]
    yes_holders: List[HolderResponse] = []
    no_holders: List[HolderResponse] = []


SortOption = Literal["volume_desc", "volume_asc", "trades_desc", "trades_asc", "newest", "ending_soon"]


@router.get("", response_model=MarketListResponse)
def get_markets(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
    category: Optional[str] = Query(default=None, description="Filter by category"),
    sort: Optional[SortOption] = Query(default="volume_desc", description="Sort by: volume_desc, volume_asc, trades_desc, trades_asc, newest, ending_soon"),
    search: Optional[str] = Query(default=None, description="Search in question text"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取市场列表（支持分类、排序、搜索）"""
    cursor = conn.cursor()

    # Query with latest trade prices via subqueries and event_slug
    query = """
        SELECT
            m.*,
            e.slug as event_slug,
            (SELECT price FROM trades WHERE market_id = m.id AND outcome = 'YES' ORDER BY timestamp DESC LIMIT 1) as latest_yes_price,
            (SELECT price FROM trades WHERE market_id = m.id AND outcome = 'NO' ORDER BY timestamp DESC LIMIT 1) as latest_no_price
        FROM markets m
        LEFT JOIN events e ON m.event_id = e.id
    """

    # Build WHERE clause
    where_clauses = []
    params = []

    if status:
        where_clauses.append("m.status = ?")
        params.append(status)

    if category:
        where_clauses.append("m.category = ?")
        params.append(category)

    if search:
        where_clauses.append("m.question LIKE ?")
        params.append(f"%{search}%")

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    # Build ORDER BY clause based on sort option
    if sort == "newest":
        query += " ORDER BY m.created_at DESC, m.id DESC"
    elif sort == "ending_soon":
        query += " ORDER BY CASE WHEN m.end_date IS NULL THEN 1 ELSE 0 END, m.end_date ASC, m.id DESC"
    elif sort == "volume_asc":
        query += " ORDER BY COALESCE(m.volume, 0) ASC, m.id DESC"
    elif sort == "trades_desc":
        query += " ORDER BY COALESCE(m.trade_count, 0) DESC, m.id DESC"
    elif sort == "trades_asc":
        query += " ORDER BY COALESCE(m.trade_count, 0) ASC, m.id DESC"
    else:  # default: volume_desc
        query += " ORDER BY COALESCE(m.volume, 0) DESC, m.id DESC"

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # 获取总数
    count_query = "SELECT COUNT(*) FROM markets m"
    count_params = []

    if where_clauses:
        count_query += " WHERE " + " AND ".join(where_clauses)
        # Rebuild params for count query (without limit/offset)
        count_params = []
        if status:
            count_params.append(status)
        if category:
            count_params.append(category)
        if search:
            count_params.append(f"%{search}%")

    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]

    markets = []
    for row in rows:
        markets.append(
            MarketResponse(
                id=row["id"],
                slug=row["slug"],
                question=row["question"],
                status=row["status"],
                yes_token_id=row["yes_token_id"],
                no_token_id=row["no_token_id"],
                outcomes=row["outcomes"],
                outcome_prices=row["outcome_prices"],
                trade_count=row["trade_count"] or 0,
                volume_24h=row["volume_24h"] or 0.0,
                # Extended fields
                image=row["image"],
                icon=row["icon"],
                category=row["category"],
                end_date=row["end_date"],
                volume=row["volume"] or 0.0,
                liquidity=row["liquidity"] or 0.0,
                best_bid=row["best_bid"],
                best_ask=row["best_ask"],
                # Latest trade prices
                latest_yes_price=row["latest_yes_price"],
                latest_no_price=row["latest_no_price"],
                # Event slug for Polymarket URL
                event_slug=row["event_slug"],
            )
        )

    has_more = offset + len(markets) < total
    return MarketListResponse(markets=markets, total=total, has_more=has_more)


@router.get("/{market_id}", response_model=MarketResponse)
def get_market(
    market_id: int,
    token_id: Optional[str] = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取单个市场详情 (使用预存储的 trade_count)"""
    cursor = conn.cursor()

    # Query with event_slug and latest trade prices
    cursor.execute("""
        SELECT
            m.*,
            e.slug as event_slug,
            (SELECT price FROM trades WHERE market_id = m.id AND outcome = 'YES' ORDER BY timestamp DESC LIMIT 1) as latest_yes_price,
            (SELECT price FROM trades WHERE market_id = m.id AND outcome = 'NO' ORDER BY timestamp DESC LIMIT 1) as latest_no_price
        FROM markets m
        LEFT JOIN events e ON m.event_id = e.id
        WHERE m.id = ?
    """, (market_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Market not found")

    return MarketResponse(
        id=row["id"],
        slug=row["slug"],
        question=row["question"],
        status=row["status"],
        yes_token_id=row["yes_token_id"],
        no_token_id=row["no_token_id"],
        outcomes=row["outcomes"],
        outcome_prices=row["outcome_prices"],
        trade_count=row["trade_count"] or 0,
        volume_24h=row["volume_24h"] or 0.0,
        # Extended fields
        image=row["image"],
        icon=row["icon"],
        category=row["category"],
        end_date=row["end_date"],
        volume=row["volume"] or 0.0,
        liquidity=row["liquidity"] or 0.0,
        best_bid=row["best_bid"],
        best_ask=row["best_ask"],
        # Latest trade prices
        latest_yes_price=row["latest_yes_price"],
        latest_no_price=row["latest_no_price"],
        # Event slug for Polymarket URL
        event_slug=row["event_slug"],
    )


@router.get("/{market_id}/price")
def get_market_price(
    market_id: int,
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取市场当前价格 (基于最近交易)"""
    cursor = conn.cursor()

    # 获取市场 token IDs
    cursor.execute(
        "SELECT yes_token_id, no_token_id FROM markets WHERE id = ?",
        (market_id,),
    )
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # 获取 YES token 最近价格
    cursor.execute(
        """
        SELECT price FROM trades
        WHERE market_id = ? AND outcome = 'YES'
        ORDER BY timestamp DESC LIMIT 1
        """,
        (market_id,),
    )
    yes_row = cursor.fetchone()
    yes_price = yes_row["price"] if yes_row else None

    # 获取 NO token 最近价格
    cursor.execute(
        """
        SELECT price FROM trades
        WHERE market_id = ? AND outcome = 'NO'
        ORDER BY timestamp DESC LIMIT 1
        """,
        (market_id,),
    )
    no_row = cursor.fetchone()
    no_price = no_row["price"] if no_row else None

    return {
        "market_id": market_id,
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_token_id": market["yes_token_id"],
        "no_token_id": market["no_token_id"],
    }


@router.get("/{market_id}/holders", response_model=MarketHoldersResponse)
def get_market_holders(
    market_id: int,
    limit: int = Query(default=10, le=20, description="每个 outcome 返回数量"),
    includeLevels: bool = Query(default=False, description="是否附带鲸鱼等级"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取市场 Top Holders (代理 Polymarket Data API)"""
    cursor = conn.cursor()
    cursor.execute("SELECT condition_id FROM markets WHERE id = ?", (market_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Market not found")

    condition_id = row["condition_id"]

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{POLYMARKET_DATA_API}/holders",
                params={"market": condition_id, "limit": limit},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch holders: {exc}") from exc

    data = response.json()
    if isinstance(data, list):
        # Data API returns a list per token; preserve API order per outcome.
        holders: List[dict] = []
        yes_ordered: List[dict] = []
        no_ordered: List[dict] = []
        for entry in data:
            if isinstance(entry, dict):
                entry_holders = entry.get("holders") or []
                if isinstance(entry_holders, list):
                    holders.extend(entry_holders)
                    for holder in entry_holders:
                        outcome_idx = holder.get("outcomeIndex")
                        if outcome_idx == 0 and len(yes_ordered) < limit:
                            yes_ordered.append(holder)
                        elif outcome_idx == 1 and len(no_ordered) < limit:
                            no_ordered.append(holder)
        if includeLevels and holders:
            _attach_holder_levels(holders)
        return MarketHoldersResponse(token=None, holders=holders, yes_holders=yes_ordered, no_holders=no_ordered)
    if not isinstance(data, dict):
        return MarketHoldersResponse(token=None, holders=[])
    holders = data.get("holders") or []
    if not isinstance(holders, list):
        holders = []
    yes_ordered: List[dict] = []
    no_ordered: List[dict] = []
    for holder in holders:
        outcome_idx = holder.get("outcomeIndex")
        if outcome_idx == 0 and len(yes_ordered) < limit:
            yes_ordered.append(holder)
        elif outcome_idx == 1 and len(no_ordered) < limit:
            no_ordered.append(holder)
    if includeLevels and holders:
        _attach_holder_levels(holders)
    return MarketHoldersResponse(
        token=data.get("token"),
        holders=holders,
        yes_holders=yes_ordered,
        no_holders=no_ordered,
    )


def _attach_holder_levels(holders: List[dict]) -> None:
    addresses = {holder.get("proxyWallet") for holder in holders if holder.get("proxyWallet")}
    if not addresses:
        return
    level_map: Dict[str, Optional[str]] = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(compute_whale_level, addr): addr for addr in addresses}
        for future in as_completed(futures):
            addr = futures[future]
            try:
                level_map[addr] = future.result()
            except Exception:
                level_map[addr] = None
    for holder in holders:
        addr = holder.get("proxyWallet")
        if addr:
            holder["whale_level"] = level_map.get(addr)
