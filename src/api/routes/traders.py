"""
Trader Profile API Routes - Polymarket Data API proxy
"""

import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..utils.trader_levels import _calc_whale_level, compute_whale_level

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/traders", tags=["traders"])

ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
DATA_API_BASE = os.getenv("POLYMARKET_DATA_API_BASE", "https://data-api.polymarket.com")
GAMMA_API_BASE = os.getenv("POLYMARKET_GAMMA_API_BASE", "https://gamma-api.polymarket.com")
MAX_TRADES_FOR_STATS = int(os.getenv("TRADER_STATS_MAX_TRADES", "10000"))

# In-memory cache for event slug -> category mapping (TTL: process lifetime)
_event_category_cache: Dict[str, str] = {}


def _normalize_address(address: str) -> str:
    return address.lower()


def _validate_address(address: str) -> str:
    if not ADDRESS_RE.match(address):
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    return _normalize_address(address)


def _data_api_get(path: str, params: Dict) -> List[Dict]:
    url = f"{DATA_API_BASE}{path}"
    try:
        response = httpx.get(url, params=params, timeout=20.0)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Data API request failed: {exc}")
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _data_api_get_raw(path: str, params: Dict) -> Union[Dict, List]:
    url = f"{DATA_API_BASE}{path}"
    try:
        response = httpx.get(url, params=params, timeout=20.0)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Data API request failed: {exc}")
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _gamma_api_get(path: str, params: Dict) -> Dict:
    url = f"{GAMMA_API_BASE}{path}"
    try:
        response = httpx.get(url, params=params, timeout=20.0)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Gamma API request failed: {exc}")
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _fetch_trades_for_stats(address: str, max_records: int) -> List[Dict]:
    limit = min(max_records, 10000)
    trades = _data_api_get(
        "/trades",
        {
            "user": address,
            "takerOnly": False,
            "limit": limit,
            "offset": 0,
        },
    )
    return trades[:max_records]


class TraderSummaryResponse(BaseModel):
    address: str
    # Core stats (from Polymarket APIs)
    positions_value: Optional[float]  # from /value
    predictions: Optional[int]  # from /traded (total markets traded)
    pnl: Optional[float]  # from leaderboard or positions
    biggest_win: Optional[float]  # max realizedPnl from positions
    win_rate: Optional[float]  # percentage of winning positions (0-100)
    # Calculated stats
    trade_count: Optional[int]
    total_volume: Optional[float]
    first_trade: Optional[str]
    last_trade: Optional[str]
    active_days: Optional[int]
    whale_level: Optional[str]
    max_trade_value: float
    max_market_volume: float
    # Profile info
    display_username_public: Optional[bool]
    name: Optional[str]
    pseudonym: Optional[str]
    bio: Optional[str]
    profile_image: Optional[str]
    x_username: Optional[str]
    verified_badge: Optional[bool]
    proxy_wallet: Optional[str]
    data_partial: bool


class TraderTradeResponse(BaseModel):
    proxyWallet: Optional[str]
    side: Optional[str]
    asset: Optional[str]
    conditionId: Optional[str]
    size: Optional[float]
    price: Optional[float]
    timestamp: Optional[int]
    title: Optional[str]
    slug: Optional[str]
    icon: Optional[str]
    eventSlug: Optional[str]
    outcome: Optional[str]
    outcomeIndex: Optional[int]
    name: Optional[str]
    pseudonym: Optional[str]
    bio: Optional[str]
    profileImage: Optional[str]
    profileImageOptimized: Optional[str]
    transactionHash: Optional[str]
    usdValue: Optional[float]


class TraderTradeListResponse(BaseModel):
    trades: List[TraderTradeResponse]
    has_more: bool
    offset: int
    limit: int


class TraderPositionResponse(BaseModel):
    proxyWallet: Optional[str]
    asset: Optional[str]
    conditionId: Optional[str]
    size: Optional[float]
    avgPrice: Optional[float]
    initialValue: Optional[float]
    currentValue: Optional[float]
    cashPnl: Optional[float]
    percentPnl: Optional[float]
    totalBought: Optional[float]
    realizedPnl: Optional[float]
    percentRealizedPnl: Optional[float]
    curPrice: Optional[float]
    redeemable: Optional[bool]
    mergeable: Optional[bool]
    title: Optional[str]
    slug: Optional[str]
    icon: Optional[str]
    eventSlug: Optional[str]
    outcome: Optional[str]
    outcomeIndex: Optional[int]
    oppositeOutcome: Optional[str]
    oppositeAsset: Optional[str]
    endDate: Optional[str]
    negativeRisk: Optional[bool]


class TraderPositionSummary(BaseModel):
    total_positions: int
    total_value: float
    total_unrealized_pnl: float


class TraderPositionsResponse(BaseModel):
    positions: List[TraderPositionResponse]
    summary: TraderPositionSummary


class TraderStatsResponse(BaseModel):
    buy_count: int
    sell_count: int
    buy_volume: float
    sell_volume: float
    yes_preference: float
    avg_trade_size: float
    categories: Dict[str, float]
    hourly_distribution: List[int]


class TraderLeaderboardEntry(BaseModel):
    rank: Optional[str]
    proxyWallet: Optional[str]
    userName: Optional[str]
    vol: Optional[float]
    pnl: Optional[float]
    profileImage: Optional[str]
    xUsername: Optional[str]
    verifiedBadge: Optional[bool]
    whale_level: Optional[str]


class TraderLeaderboardResponse(BaseModel):
    traders: List[TraderLeaderboardEntry]


class TraderSearchResponse(BaseModel):
    results: List[str]


class TraderValueResponse(BaseModel):
    value: Optional[float]


@router.get("/top", response_model=TraderLeaderboardResponse)
def get_trader_leaderboard(
    orderBy: str = Query(default="PNL", description="PNL|VOL"),
    category: str = Query(default="OVERALL", description="OVERALL|POLITICS|SPORTS|CRYPTO|CULTURE|MENTIONS|WEATHER|ECONOMICS|TECH|FINANCE"),
    timePeriod: str = Query(default="DAY", description="DAY|WEEK|MONTH|ALL"),
    limit: int = Query(default=25, ge=1, le=50, description="返回数量"),
    offset: int = Query(default=0, ge=0, le=1000, description="偏移量"),
    includeLevels: bool = Query(default=False, description="是否附带鲸鱼等级"),
):
    data = _data_api_get(
        "/v1/leaderboard",
        {
            "orderBy": orderBy,
            "category": category,
            "timePeriod": timePeriod,
            "limit": limit,
            "offset": offset,
        },
    )

    if includeLevels and data:
        addresses = {row.get("proxyWallet") for row in data if row.get("proxyWallet")}
        level_map: Dict[str, Optional[str]] = {}
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(compute_whale_level, addr): addr for addr in addresses}
            for future in as_completed(futures):
                addr = futures[future]
                try:
                    level_map[addr] = future.result()
                except Exception:
                    level_map[addr] = None
        for row in data:
            addr = row.get("proxyWallet")
            if addr:
                row["whale_level"] = level_map.get(addr)

    traders = [TraderLeaderboardEntry(**row) for row in data]
    return TraderLeaderboardResponse(traders=traders)


@router.get("/search", response_model=TraderSearchResponse)
def search_traders(
    q: str = Query(default="", description="地址前缀搜索"),
    limit: int = Query(default=20, le=50, description="返回数量"),
):
    query = q.strip()
    if not query:
        return TraderSearchResponse(results=[])

    if ADDRESS_RE.match(query):
        return TraderSearchResponse(results=[query.lower()])

    if query.startswith("0x"):
        return TraderSearchResponse(results=[query.lower()])

    return TraderSearchResponse(results=[])


@router.get("/{address}/value", response_model=TraderValueResponse)
def get_trader_value(
    address: str,
):
    normalized = _validate_address(address)
    data = _data_api_get_raw(
        "/value",
        {
            "user": normalized,
        },
    )
    if isinstance(data, dict):
        return TraderValueResponse(value=data.get("value"))
    return TraderValueResponse(value=None)


def _fetch_positions_value(address: str) -> Optional[float]:
    """Fetch total USD value of positions from /value endpoint, with fallback"""
    # Method 1: Try /value endpoint
    try:
        data = _data_api_get_raw("/value", {"user": address})
        if isinstance(data, dict) and data.get("value") is not None:
            return float(data.get("value"))
    except Exception as e:
        print(f"[WARN] /value endpoint failed for {address}: {e}")

    # Method 2: Fallback to sum of currentValue from /positions
    try:
        positions = _data_api_get("/positions", {"user": address, "limit": 500})
        if positions:
            total = sum(float(p.get("currentValue") or 0) for p in positions)
            return total if total > 0 else None
    except Exception as e:
        print(f"[WARN] positions fallback failed for {address}: {e}")

    return None


def _fetch_predictions_count(address: str) -> Optional[int]:
    """Fetch total markets traded from /traded endpoint"""
    try:
        data = _data_api_get_raw("/traded", {"user": address})
        if isinstance(data, dict):
            return data.get("traded")
    except Exception:
        pass
    return None


def _fetch_pnl_from_leaderboard(address: str) -> Optional[float]:
    """Fetch PnL from leaderboard (ALL time)"""
    try:
        data = _data_api_get(
            "/v1/leaderboard",
            {"user": address, "timePeriod": "ALL", "orderBy": "PNL", "limit": 1},
        )
        if data and len(data) > 0:
            return data[0].get("pnl")
    except Exception:
        pass
    return None


def _fetch_biggest_win(address: str) -> Optional[float]:
    """Fetch biggest win from closed positions (max realized profit)"""
    try:
        positions = _data_api_get(
            "/closed-positions",
            {
                "user": address,
                "limit": 500,
                "sortBy": "REALIZEDPNL",
                "sortDirection": "DESC",
            },
        )
        if positions:
            max_win = 0.0
            for pos in positions:
                realized = float(pos.get("realizedPnl") or 0)
                if realized > max_win:
                    max_win = realized
            return max_win if max_win > 0 else None
    except Exception as e:
        print(f"[WARN] biggest win calculation failed for {address}: {e}")
    return None


def _fetch_win_rate(address: str) -> Optional[float]:
    """Calculate win rate from positions (percentage of profitable positions)"""
    try:
        positions = _data_api_get(
            "/positions",
            {
                "user": address,
                "limit": 500,
            },
        )
        if not positions:
            return None

        # Count positions with any PnL (realized or unrealized)
        winning = 0
        losing = 0
        for pos in positions:
            realized = float(pos.get("realizedPnl") or 0)
            cash_pnl = float(pos.get("cashPnl") or 0)
            # Use cashPnl as it includes both realized and unrealized
            pnl = cash_pnl if cash_pnl != 0 else realized
            if pnl > 0:
                winning += 1
            elif pnl < 0:
                losing += 1

        total = winning + losing
        if total == 0:
            return None

        win_rate = (winning / total) * 100
        return round(win_rate, 1)
    except Exception as e:
        print(f"[WARN] win rate calculation failed for {address}: {e}")
    return None


@router.get("/{address}", response_model=TraderSummaryResponse)
def get_trader_summary(
    address: str,
    max_records: int = Query(default=MAX_TRADES_FOR_STATS, le=10000, description="用于统计的最大交易数"),
):
    normalized = _validate_address(address)
    logger.info(f"[SUMMARY] Fetching trader summary for {normalized}")

    # Fetch data from multiple Polymarket APIs in PARALLEL
    results = {}
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {
            executor.submit(_gamma_api_get, "/public-profile", {"address": normalized}): "profile",
            executor.submit(_fetch_positions_value, normalized): "positions_value",
            executor.submit(_fetch_predictions_count, normalized): "predictions",
            executor.submit(_fetch_pnl_from_leaderboard, normalized): "pnl",
            executor.submit(_fetch_biggest_win, normalized): "biggest_win",
            executor.submit(_fetch_win_rate, normalized): "win_rate",
            executor.submit(_fetch_trades_for_stats, normalized, max_records): "trades",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                logger.warning(f"[SUMMARY] Failed to fetch {key}: {e}")
                results[key] = None if key != "trades" else []

    profile = results.get("profile") or {}
    positions_value = results.get("positions_value")
    predictions = results.get("predictions")
    pnl = results.get("pnl")
    biggest_win = results.get("biggest_win")
    win_rate = results.get("win_rate")
    trades = results.get("trades") or []

    logger.info(f"[SUMMARY] Parallel fetch complete for {normalized}")

    if not trades:
        return TraderSummaryResponse(
            address=address,
            positions_value=positions_value,
            predictions=predictions,
            pnl=pnl,
            biggest_win=biggest_win,
            win_rate=win_rate,
            trade_count=0,
            total_volume=0.0,
            first_trade=None,
            last_trade=None,
            active_days=None,
            whale_level=None,
            max_trade_value=0.0,
            max_market_volume=0.0,
            display_username_public=profile.get("displayUsernamePublic"),
            name=profile.get("name"),
            pseudonym=profile.get("pseudonym"),
            bio=profile.get("bio"),
            profile_image=profile.get("profileImage"),
            x_username=profile.get("xUsername"),
            verified_badge=profile.get("verifiedBadge"),
            proxy_wallet=profile.get("proxyWallet"),
            data_partial=False,
        )

    total_volume = 0.0
    max_trade_value = 0.0
    market_totals: Dict[str, float] = {}
    timestamps: List[int] = []
    active_days_set = set()

    for trade in trades:
        price = float(trade.get("price") or 0)
        size = float(trade.get("size") or 0)
        usd_value = price * size
        total_volume += usd_value
        max_trade_value = max(max_trade_value, usd_value)

        condition_id = trade.get("conditionId")
        if condition_id:
            market_totals[condition_id] = market_totals.get(condition_id, 0.0) + usd_value

        ts = trade.get("timestamp")
        if ts is not None:
            timestamps.append(int(ts))
            active_days_set.add(datetime.fromtimestamp(int(ts), tz=timezone.utc).date())

    max_market_volume = max(market_totals.values()) if market_totals else 0.0

    first_trade = _to_iso(min(timestamps)) if timestamps else None
    last_trade = _to_iso(max(timestamps)) if timestamps else None

    is_partial = len(trades) >= max_records

    # Calculate whale level based on per-trade and per-market thresholds (PHASE5)
    whale_level = _calc_whale_level(max_trade_value, max_market_volume)

    return TraderSummaryResponse(
        address=address,
        positions_value=positions_value,
        predictions=predictions,
        pnl=pnl,
        biggest_win=biggest_win,
        win_rate=win_rate,
        trade_count=None if is_partial else len(trades),
        total_volume=None if is_partial else total_volume,
        first_trade=None if is_partial else first_trade,
        last_trade=None if is_partial else last_trade,
        active_days=None if is_partial else len(active_days_set),
        whale_level=whale_level,
        max_trade_value=max_trade_value,
        max_market_volume=max_market_volume,
        display_username_public=profile.get("displayUsernamePublic"),
        name=profile.get("name"),
        pseudonym=profile.get("pseudonym"),
        bio=profile.get("bio"),
        profile_image=profile.get("profileImage"),
        x_username=profile.get("xUsername"),
        verified_badge=profile.get("verifiedBadge"),
        proxy_wallet=profile.get("proxyWallet"),
        data_partial=is_partial,
    )


@router.get("/{address}/trades", response_model=TraderTradeListResponse)
def get_trader_trades(
    address: str,
    limit: int = Query(default=50, le=10000, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    side: Optional[str] = Query(default=None, description="BUY/SELL"),
    start_time: Optional[str] = Query(default=None, description="开始时间 (ISO)"),
    end_time: Optional[str] = Query(default=None, description="结束时间 (ISO)"),
    min_usd: Optional[float] = Query(default=None, description="最小 USD 价值"),
    max_usd: Optional[float] = Query(default=None, description="最大 USD 价值"),
):
    normalized = _validate_address(address)
    params: Dict[str, object] = {
        "user": normalized,
        "takerOnly": False,
        "limit": limit,
        "offset": offset,
    }
    if side:
        params["side"] = side.upper()

    trades = _data_api_get("/trades", params)

    if start_time or end_time:
        start_ts = None
        end_ts = None
        if start_time:
            start_ts = int(datetime.fromisoformat(start_time.replace("Z", "+00:00")).timestamp())
        if end_time:
            end_ts = int(datetime.fromisoformat(end_time.replace("Z", "+00:00")).timestamp())

        filtered = []
        for trade in trades:
            ts = trade.get("timestamp")
            if ts is None:
                continue
            ts_int = int(ts)
            if start_ts is not None and ts_int < start_ts:
                continue
            if end_ts is not None and ts_int > end_ts:
                continue
            filtered.append(trade)
        trades = filtered

    if min_usd is not None or max_usd is not None:
        filtered = []
        for trade in trades:
            price = float(trade.get("price") or 0)
            size = float(trade.get("size") or 0)
            usd_value = price * size
            if min_usd is not None and usd_value < min_usd:
                continue
            if max_usd is not None and usd_value > max_usd:
                continue
            filtered.append(trade)
        trades = filtered

    enriched = []
    for trade in trades:
        price = float(trade.get("price") or 0)
        size = float(trade.get("size") or 0)
        trade["usdValue"] = price * size
        enriched.append(TraderTradeResponse(**trade))

    has_more = len(trades) == limit

    return TraderTradeListResponse(
        trades=enriched,
        has_more=has_more,
        offset=offset,
        limit=limit,
    )


@router.get("/{address}/positions", response_model=TraderPositionsResponse)
def get_trader_positions(
    address: str,
    limit: int = Query(default=200, le=500, description="返回数量"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    sortBy: str = Query(default="TOKENS", description="CURRENT|INITIAL|TOKENS|CASHPNL|PERCENTPNL|TITLE|RESOLVING|PRICE|AVGPRICE"),
    sortDirection: str = Query(default="DESC", description="ASC|DESC"),
):
    normalized = _validate_address(address)
    positions = _data_api_get(
        "/positions",
        {
            "user": normalized,
            "limit": limit,
            "offset": offset,
            "sortBy": sortBy,
            "sortDirection": sortDirection,
        },
    )

    total_value = 0.0
    total_pnl = 0.0
    for pos in positions:
        total_value += float(pos.get("currentValue") or 0)
        total_pnl += float(pos.get("cashPnl") or 0)

    summary = TraderPositionSummary(
        total_positions=len(positions),
        total_value=total_value,
        total_unrealized_pnl=total_pnl,
    )

    return TraderPositionsResponse(
        positions=[TraderPositionResponse(**row) for row in positions],
        summary=summary,
    )


def _fetch_single_event_category(slug: str) -> tuple[str, Optional[str]]:
    """Fetch category for a single event slug"""
    try:
        data = _gamma_api_get("/events", {"slug": slug})
        if isinstance(data, list) and len(data) > 0:
            event = data[0]
            category = event.get("category")
            if not category:
                tags = event.get("tags", [])
                for tag in tags:
                    label = tag.get("label") if isinstance(tag, dict) else None
                    if label and label.lower() != "all":
                        category = label
                        break
            return slug, category or "Other"
    except Exception:
        pass
    return slug, "Other"


def _fetch_event_categories(event_slugs: List[str]) -> Dict[str, str]:
    """Batch fetch event categories from Gamma API with caching (parallel)"""
    global _event_category_cache

    if not event_slugs:
        return {}

    slug_to_category: Dict[str, str] = {}
    unique_slugs = list(set(event_slugs))

    # Check cache first
    slugs_to_fetch = []
    for slug in unique_slugs:
        if not slug:
            continue
        if slug in _event_category_cache:
            slug_to_category[slug] = _event_category_cache[slug]
        else:
            slugs_to_fetch.append(slug)

    if not slugs_to_fetch:
        return slug_to_category

    # Fetch uncached slugs from Gamma API in parallel
    logger.info(f"[STATS] Fetching {len(slugs_to_fetch)} event categories in parallel")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_single_event_category, slug) for slug in slugs_to_fetch]
        for future in as_completed(futures):
            try:
                slug, category = future.result()
                if category:
                    slug_to_category[slug] = category
                    _event_category_cache[slug] = category
            except Exception:
                continue

    return slug_to_category


@router.get("/{address}/stats", response_model=TraderStatsResponse)
def get_trader_stats(
    address: str,
    max_records: int = Query(default=MAX_TRADES_FOR_STATS, le=10000, description="用于统计的最大交易数"),
):
    normalized = _validate_address(address)
    trades = _fetch_trades_for_stats(normalized, max_records)

    logger.info(f"[STATS] Fetched {len(trades)} trades for {normalized}")

    buy_count = 0
    sell_count = 0
    buy_volume = 0.0
    sell_volume = 0.0
    yes_volume = 0.0
    total_volume = 0.0
    hourly_distribution = [0] * 24
    trade_by_event: Dict[str, float] = {}  # eventSlug -> volume

    # Debug: log first trade timestamp
    if trades and len(trades) > 0:
        first_ts = trades[0].get("timestamp")
        logger.info(f"[STATS] First trade timestamp: {first_ts}, type: {type(first_ts)}")

    for trade in trades:
        price = float(trade.get("price") or 0)
        size = float(trade.get("size") or 0)
        usd_value = price * size
        total_volume += usd_value

        side = (trade.get("side") or "").upper()
        if side == "BUY":
            buy_count += 1
            buy_volume += usd_value
        elif side == "SELL":
            sell_count += 1
            sell_volume += usd_value

        outcome = trade.get("outcome")
        outcome_index = trade.get("outcomeIndex")
        if outcome == "YES" or outcome_index == 0:
            yes_volume += usd_value

        ts = trade.get("timestamp")
        if ts is not None:
            ts_int = int(ts)
            # Handle milliseconds if timestamp is too large (> year 2100 in seconds)
            if ts_int > 4102444800:
                ts_int = ts_int // 1000
            hour = datetime.fromtimestamp(ts_int, tz=timezone.utc).hour
            hourly_distribution[hour] += 1

        # Track volume by event slug for category aggregation
        event_slug = trade.get("eventSlug")
        if event_slug:
            trade_by_event[event_slug] = trade_by_event.get(event_slug, 0.0) + usd_value

    avg_trade_size = total_volume / len(trades) if trades else 0.0
    yes_preference = yes_volume / total_volume if total_volume > 0 else 0.0

    # Debug: log hourly distribution
    logger.info(f"[STATS] hourly_distribution sum: {sum(hourly_distribution)}, non-zero hours: {[i for i, c in enumerate(hourly_distribution) if c > 0]}")

    # Fetch categories for events and aggregate
    categories: Dict[str, float] = {}
    if trade_by_event:
        event_slugs = list(trade_by_event.keys())
        slug_to_category = _fetch_event_categories(event_slugs)

        for slug, volume in trade_by_event.items():
            category = slug_to_category.get(slug, "Other")
            categories[category] = categories.get(category, 0.0) + volume

    return TraderStatsResponse(
        buy_count=buy_count,
        sell_count=sell_count,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        yes_preference=yes_preference,
        avg_trade_size=avg_trade_size,
        categories=categories,
        hourly_distribution=hourly_distribution,
    )


# PnL Subgraph endpoint for historical data
PNL_SUBGRAPH_URL = "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/0.0.14/gn"


class PnLDataPoint(BaseModel):
    timestamp: int
    pnl: float


class PnLHistoryResponse(BaseModel):
    data_points: List[PnLDataPoint]
    total_pnl: Optional[float]
    period: str


def _get_period_start_timestamp(period: str) -> Optional[int]:
    """Get start timestamp for period filter"""
    now = int(datetime.now(timezone.utc).timestamp())
    periods = {
        "1D": now - 86400,
        "1W": now - 604800,
        "1M": now - 2592000,
        "ALL": None,
    }
    return periods.get(period.upper())


@router.get("/{address}/pnl-history", response_model=PnLHistoryResponse)
def get_trader_pnl_history(
    address: str,
    period: str = Query(default="ALL", description="1D|1W|1M|ALL"),
):
    """
    Fetch PnL history from activity data.
    Since the PnL subgraph may not expose time series directly,
    we calculate cumulative PnL from trade activity.
    """
    normalized = _validate_address(address)
    period_start = _get_period_start_timestamp(period)

    try:
        # Fetch activity data which includes PnL changes
        params: Dict[str, object] = {
            "user": normalized,
            "limit": 1000,
            "type": "TRADE",
        }
        if period_start:
            params["start"] = period_start

        activity = _data_api_get("/activity", params)

        if not activity:
            return PnLHistoryResponse(data_points=[], total_pnl=None, period=period)

        # Build time series from activity
        # Group by day and calculate cumulative PnL
        daily_pnl: Dict[int, float] = {}
        for item in activity:
            ts = item.get("timestamp")
            if ts is None:
                continue

            # Round to day start
            day_ts = (int(ts) // 86400) * 86400

            # Calculate PnL from trade: (sell - buy) based on side
            side = item.get("side", "").upper()
            usdc_size = float(item.get("usdcSize") or 0)

            if side == "SELL":
                daily_pnl[day_ts] = daily_pnl.get(day_ts, 0) + usdc_size
            elif side == "BUY":
                daily_pnl[day_ts] = daily_pnl.get(day_ts, 0) - usdc_size

        # Sort and build cumulative series
        sorted_days = sorted(daily_pnl.keys())
        cumulative = 0.0
        data_points = []

        for day_ts in sorted_days:
            cumulative += daily_pnl[day_ts]
            data_points.append(PnLDataPoint(timestamp=day_ts, pnl=cumulative))

        # Get actual total PnL from leaderboard for accuracy
        total_pnl = _fetch_pnl_from_leaderboard(normalized)

        return PnLHistoryResponse(
            data_points=data_points,
            total_pnl=total_pnl,
            period=period,
        )

    except Exception as e:
        print(f"[WARN] PnL history fetch failed for {address}: {e}")
        return PnLHistoryResponse(data_points=[], total_pnl=None, period=period)
