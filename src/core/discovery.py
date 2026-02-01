"""
Market Discovery Service
从 Gamma API 发现市场并存储到数据库
"""

import json
import sqlite3
import requests
from typing import Optional, Dict, Any, List

from ..config import GAMMA_API_BASE
from .ctf_utils import calculate_token_ids
from .db.store import upsert_event, upsert_market, set_sync_state


def fetch_event_from_gamma(event_slug: str) -> Optional[Dict[str, Any]]:
    """从 Gamma API 获取事件详情"""
    url = f"{GAMMA_API_BASE}/events?slug={event_slug}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        events = response.json()
        if events and len(events) > 0:
            return events[0]
    except Exception as e:
        print(f"Warning: Failed to fetch event from Gamma API: {e}")
    return None


def fetch_markets_from_gamma(
    event_slug: str = None,
    condition_id: str = None,
    active_only: bool = False,
    limit: int = None,
    fetch_all: bool = False,
) -> List[Dict[str, Any]]:
    """从 Gamma API 获取市场列表"""
    API_MAX_LIMIT = 500

    def build_url(offset: int = 0, page_limit: int = API_MAX_LIMIT) -> str:
        params = []
        if event_slug:
            params.append(f"slug={event_slug}")
        if condition_id:
            params.append(f"condition_ids={condition_id}")
        if active_only:
            params.append("closed=false")
        params.append(f"limit={page_limit}")
        if offset > 0:
            params.append(f"offset={offset}")
        return f"{GAMMA_API_BASE}/markets?{'&'.join(params)}"

    try:
        if fetch_all:
            all_markets = []
            offset = 0
            while True:
                url = build_url(offset=offset)
                print(f"  Fetching markets offset={offset}...")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                batch = response.json()
                if not batch:
                    break
                all_markets.extend(batch)
                if len(batch) < API_MAX_LIMIT:
                    break
                offset += API_MAX_LIMIT
                if limit and len(all_markets) >= limit:
                    return all_markets[:limit]
            return all_markets
        else:
            page_limit = min(limit, API_MAX_LIMIT) if limit else API_MAX_LIMIT
            url = build_url(page_limit=page_limit)
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Warning: Failed to fetch markets from Gamma API: {e}")
        return []


def parse_clob_token_ids(clob_token_ids: Any) -> tuple:
    """解析 clobTokenIds 字段"""
    if not clob_token_ids:
        return None, None

    try:
        if isinstance(clob_token_ids, str):
            ids = json.loads(clob_token_ids)
        else:
            ids = clob_token_ids

        if isinstance(ids, list) and len(ids) >= 2:
            return str(ids[0]), str(ids[1])
    except (json.JSONDecodeError, TypeError):
        pass

    return None, None


def extract_category(data: Dict[str, Any]) -> Optional[str]:
    """
    从 market 或 event 数据中提取分类
    优先级: category > tags[0].label (跳过 'All')
    """
    # 1. 优先使用 category 字段
    category = data.get("category")
    if category:
        return category

    # 2. 从 tags 中提取第一个有效标签
    tags = data.get("tags", [])
    for tag in tags:
        label = tag.get("label") if isinstance(tag, dict) else None
        if label and label.lower() != "all":
            return label

    return None


def verify_token_ids(
    condition_id: str,
    is_neg_risk: bool,
    gamma_yes_token: str,
    gamma_no_token: str,
) -> Dict[str, Any]:
    """验证 Token IDs 是否与本地计算结果一致"""
    result = {
        "verified": False,
        "calculated_yes": None,
        "calculated_no": None,
        "collateral_token": None,
        "warning": None,
    }

    try:
        calculated = calculate_token_ids(condition_id, is_neg_risk)
        result["calculated_yes"] = calculated["yesTokenId"]
        result["calculated_no"] = calculated["noTokenId"]
        result["collateral_token"] = calculated["collateralToken"]

        if gamma_yes_token and gamma_no_token:
            yes_match = gamma_yes_token == calculated["yesTokenId"]
            no_match = gamma_no_token == calculated["noTokenId"]

            if yes_match and no_match:
                result["verified"] = True
            else:
                result["warning"] = (
                    f"Token ID mismatch. "
                    f"Gamma YES: {gamma_yes_token[:20]}..., "
                    f"Calculated: {calculated['yesTokenId'][:20]}..."
                )
        else:
            result["warning"] = "No clobTokenIds from Gamma API to verify"

    except Exception as e:
        result["warning"] = f"Failed to calculate token IDs: {e}"

    return result


def process_market(
    conn: sqlite3.Connection,
    market: Dict[str, Any],
    event_id: int = None,
    verify_tokens: bool = True,
) -> Dict[str, Any]:
    """处理单个市场数据"""
    condition_id = market.get("conditionId")
    slug = market.get("slug")
    is_neg_risk = market.get("negRisk", False)

    result = {
        "slug": slug,
        "condition_id": condition_id,
        "saved": False,
        "market_id": None,
        "event_id": event_id,
        "warning": None,
    }

    if not condition_id:
        result["warning"] = f"Market {slug} has no conditionId, skipped"
        return result

    # 从 market 或其关联的 event 中提取分类
    # 优先级: market.category > market.tags > event.category > event.tags
    market_category = extract_category(market)

    if event_id is None:
        events = market.get("events", [])
        if events and len(events) > 0:
            event_data = events[0]
            # 如果 market 没有分类，尝试从 event 获取
            if not market_category:
                market_category = extract_category(event_data)
            event_id = upsert_event(
                conn,
                {
                    "slug": event_data.get("slug"),
                    "title": event_data.get("title"),
                    "description": event_data.get("description"),
                    "category": extract_category(event_data),
                    "startDate": event_data.get("startDate"),
                    "endDate": event_data.get("endDate"),
                    "image": event_data.get("image"),
                    "icon": event_data.get("icon"),
                    "active": event_data.get("active"),
                    "closed": event_data.get("closed"),
                    "archived": event_data.get("archived"),
                    "enableNegRisk": event_data.get("enableNegRisk"),
                },
            )
            result["event_id"] = event_id

    # 解析 Gamma API 的 token IDs
    gamma_yes, gamma_no = parse_clob_token_ids(market.get("clobTokenIds"))

    # 验证 Token IDs
    verification = None
    if verify_tokens:
        verification = verify_token_ids(condition_id, is_neg_risk, gamma_yes, gamma_no)
        if verification.get("warning"):
            result["warning"] = verification["warning"]

    # 确定最终使用的 token IDs
    if verification and verification.get("calculated_yes"):
        yes_token_id = verification["calculated_yes"]
        no_token_id = verification["calculated_no"]
        collateral_token = verification["collateral_token"]
    else:
        yes_token_id = gamma_yes
        no_token_id = gamma_no
        collateral_token = None

    # 存储到数据库
    try:
        market_id = upsert_market(
            conn,
            {
                "event_id": event_id,
                "slug": slug,
                "conditionId": condition_id,
                "questionID": market.get("questionID"),
                "resolvedBy": market.get("resolvedBy"),
                "collateralToken": collateral_token,
                "yesTokenId": yes_token_id,
                "no_token_id": no_token_id,
                "negRisk": is_neg_risk,
                "active": market.get("active"),
                "closed": market.get("closed"),
                "question": market.get("question"),
                "description": market.get("description"),
                "outcomes": market.get("outcomes"),
                "outcomePrices": market.get("outcomePrices"),
                "endDate": market.get("endDate"),
                # 前端展示字段
                "image": market.get("image"),
                "icon": market.get("icon"),
                "category": market_category,
                "volumeNum": market.get("volumeNum") or market.get("volume"),
                "volume24hr": market.get("volume24hr"),
                "liquidityNum": market.get("liquidityNum") or market.get("liquidity"),
                "bestBid": market.get("bestBid"),
                "bestAsk": market.get("bestAsk"),
                "sync_warning": result.get("warning"),
            },
        )
        result["saved"] = True
        result["market_id"] = market_id
        result["yes_token_id"] = yes_token_id
        result["no_token_id"] = no_token_id

    except Exception as e:
        result["warning"] = f"Failed to save market {slug}: {e}"

    return result


def discover_markets_by_event_slug(
    conn: sqlite3.Connection,
    event_slug: str,
    verify_tokens: bool = True,
) -> Dict[str, Any]:
    """通过事件 slug 发现并存储市场"""
    result = {
        "event_slug": event_slug,
        "event_id": None,
        "markets_found": 0,
        "markets_saved": 0,
        "markets": [],
        "warnings": [],
    }

    # 获取事件信息
    event_data = fetch_event_from_gamma(event_slug)
    event_category = None
    if event_data:
        event_category = extract_category(event_data)
        event_id = upsert_event(
            conn,
            {
                "slug": event_data.get("slug") or event_slug,
                "title": event_data.get("title"),
                "description": event_data.get("description"),
                "category": event_category,
                "startDate": event_data.get("startDate"),
                "endDate": event_data.get("endDate"),
                "active": event_data.get("active"),
                "closed": event_data.get("closed"),
                "archived": event_data.get("archived"),
                "enableNegRisk": event_data.get("enableNegRisk"),
            },
        )
        result["event_id"] = event_id
        print(f"Event saved: {event_slug} (id={event_id}, category={event_category})")

    # 获取市场列表
    markets = fetch_markets_from_gamma(event_slug=event_slug)
    result["markets_found"] = len(markets)

    if not markets:
        result["warnings"].append(f"No markets found for event: {event_slug}")
        return result

    print(f"Found {len(markets)} markets for event: {event_slug}")

    # 处理每个市场
    for market in markets:
        # If market doesn't have category, use the event's category
        if not extract_category(market) and event_category:
            market["category"] = event_category

        market_info = process_market(
            conn=conn,
            market=market,
            event_id=result.get("event_id"),
            verify_tokens=verify_tokens,
        )
        result["markets"].append(market_info)

        if market_info.get("saved"):
            result["markets_saved"] += 1

        if market_info.get("warning"):
            result["warnings"].append(market_info["warning"])

    return result


def discover_all_markets(
    conn: sqlite3.Connection,
    active_only: bool = True,
    limit: int = None,
    fetch_all: bool = False,
    verify_tokens: bool = True,
) -> Dict[str, Any]:
    """发现所有市场 (全量模式)"""
    result = {
        "markets_found": 0,
        "markets_saved": 0,
        "warnings": [],
    }

    markets = fetch_markets_from_gamma(
        active_only=active_only,
        limit=limit,
        fetch_all=fetch_all,
    )
    result["markets_found"] = len(markets)

    print(f"Found {len(markets)} markets from Gamma API")

    for market in markets:
        market_info = process_market(
            conn=conn,
            market=market,
            verify_tokens=verify_tokens,
        )
        if market_info.get("saved"):
            result["markets_saved"] += 1
        if market_info.get("warning"):
            result["warnings"].append(market_info["warning"])

    return result


def fetch_market_by_token_id_from_gamma(token_id: str) -> Optional[Dict[str, Any]]:
    """通过 token_id 从 Gamma API 查询市场"""
    url = f"{GAMMA_API_BASE}/markets?clob_token_ids={token_id}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        markets = response.json()
        if markets and len(markets) > 0:
            return markets[0]
    except Exception as e:
        print(f"Warning: Failed to fetch market by token_id from Gamma API: {e}")
    return None


def discover_market_by_token_id(
    conn: sqlite3.Connection,
    token_id: str,
    verify_tokens: bool = True,
) -> Optional[Dict[str, Any]]:
    """通过 token_id 发现并存储市场 (按需发现)"""
    gamma_market = fetch_market_by_token_id_from_gamma(token_id)
    if not gamma_market:
        return None

    # 如果市场没有 category，尝试从 events API 获取完整的 event 数据（包含 tags）
    if not extract_category(gamma_market):
        events = gamma_market.get("events", [])
        if events and events[0].get("slug"):
            event_slug = events[0]["slug"]
            full_event = fetch_event_from_gamma(event_slug)
            if full_event:
                category = extract_category(full_event)
                if category:
                    # 将 category 注入到市场数据中
                    gamma_market["category"] = category

    market_info = process_market(
        conn=conn,
        market=gamma_market,
        verify_tokens=verify_tokens,
    )

    if not market_info.get("saved"):
        return None

    return {
        "id": market_info["market_id"],
        "yes_token_id": market_info.get("yes_token_id"),
        "no_token_id": market_info.get("no_token_id"),
        "slug": market_info.get("slug"),
        "condition_id": market_info.get("condition_id"),
    }


def fetch_all_events_from_gamma(
    active_only: bool = False,
    limit: int = None,
) -> List[Dict[str, Any]]:
    """从 Gamma API 获取所有 events (用于批量更新 category)"""
    API_MAX_LIMIT = 500
    all_events = []
    offset = 0

    while True:
        params = [f"limit={API_MAX_LIMIT}"]
        if active_only:
            params.append("active=true")
        if offset > 0:
            params.append(f"offset={offset}")

        url = f"{GAMMA_API_BASE}/events?{'&'.join(params)}"

        try:
            print(f"  Fetching events offset={offset}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            batch = response.json()

            if not batch:
                break

            all_events.extend(batch)

            if len(batch) < API_MAX_LIMIT:
                break

            offset += API_MAX_LIMIT

            if limit and len(all_events) >= limit:
                return all_events[:limit]

        except Exception as e:
            print(f"Warning: Failed to fetch events from Gamma API: {e}")
            break

    return all_events


def update_categories_from_events(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    从 Gamma API 批量获取 events 的 category/tags，更新数据库中的 markets
    用于填充缺失的 category 数据
    """
    result = {
        "events_fetched": 0,
        "markets_updated": 0,
        "categories_found": {},
    }

    print("Fetching all events from Gamma API...")
    events = fetch_all_events_from_gamma()
    result["events_fetched"] = len(events)
    print(f"Fetched {len(events)} events")

    # 构建 event_slug -> category 映射
    event_categories = {}
    for event in events:
        event_slug = event.get("slug")
        category = extract_category(event)
        if event_slug and category:
            event_categories[event_slug] = category
            result["categories_found"][category] = result["categories_found"].get(category, 0) + 1

    print(f"Found {len(event_categories)} events with categories")
    print(f"Category distribution: {result['categories_found']}")

    # 更新 events 表
    cursor = conn.cursor()
    for event_slug, category in event_categories.items():
        cursor.execute(
            "UPDATE events SET category = ? WHERE slug = ? AND (category IS NULL OR category = '')",
            (category, event_slug),
        )

    # 通过 event_id 关联更新 markets 表
    cursor.execute("""
        UPDATE markets
        SET category = (
            SELECT e.category FROM events e WHERE e.id = markets.event_id
        )
        WHERE category IS NULL OR category = ''
    """)
    result["markets_updated"] = cursor.rowcount

    conn.commit()
    print(f"Updated {result['markets_updated']} markets with categories")

    return result


def refresh_market_metadata(conn: sqlite3.Connection, limit: int = None) -> Dict[str, Any]:
    """
    刷新数据库中市场的元数据 (从 Gamma API 获取最新数据)
    包括 category, volume, volume_24h, outcome_prices 等
    """
    result = {
        "markets_fetched": 0,
        "markets_updated": 0,
    }

    print("Fetching markets from Gamma API...")
    markets = fetch_markets_from_gamma(fetch_all=True, limit=limit)
    result["markets_fetched"] = len(markets)
    print(f"Fetched {len(markets)} markets")

    updated = 0
    for market in markets:
        condition_id = market.get("conditionId")
        if not condition_id:
            continue

        category = extract_category(market)
        # 也从 events 中获取
        if not category:
            events = market.get("events", [])
            if events:
                category = extract_category(events[0])

        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE markets SET
                category = COALESCE(?, category),
                volume = COALESCE(?, volume),
                volume_24h = COALESCE(?, volume_24h),
                outcome_prices = COALESCE(?, outcome_prices),
                liquidity = COALESCE(?, liquidity),
                image = COALESCE(?, image),
                updated_at = datetime('now')
            WHERE condition_id = ?
            """,
            (
                category,
                market.get("volumeNum") or market.get("volume"),
                market.get("volume24hr"),
                market.get("outcomePrices"),
                market.get("liquidityNum") or market.get("liquidity"),
                market.get("image"),
                condition_id,
            ),
        )
        if cursor.rowcount > 0:
            updated += 1

    conn.commit()
    result["markets_updated"] = updated
    print(f"Updated {updated} markets")

    return result