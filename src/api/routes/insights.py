"""
Market Insights API Routes (Optimized for large datasets)
- 热门市场榜
- 异常交易量检测
- Smart Money 流向
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import get_db

router = APIRouter(prefix="/insights", tags=["insights"])


# ============== Response Models ==============

class HotMarket(BaseModel):
    id: int
    slug: str
    question: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = None
    volume_24h: float = 0.0
    trade_count_24h: int = 0
    unique_traders_24h: int = 0
    price_change_24h: Optional[float] = None
    current_price: Optional[float] = None


class HotMarketsResponse(BaseModel):
    markets: List[HotMarket]
    updated_at: str


class VolumeAnomaly(BaseModel):
    market_id: int
    slug: str
    question: Optional[str] = None
    image: Optional[str] = None
    volume_24h: float
    volume_avg_30d: float
    volume_ratio: float
    trade_count_24h: int
    anomaly_type: str


class VolumeAnomalyResponse(BaseModel):
    anomalies: List[VolumeAnomaly]
    threshold: float
    updated_at: str


class SmartMoneyFlow(BaseModel):
    market_id: int
    slug: str
    question: Optional[str] = None
    image: Optional[str] = None
    whale_buy_volume: float
    whale_sell_volume: float
    whale_net_flow: float
    whale_buy_count: int
    whale_sell_count: int
    flow_direction: str
    signal_strength: str


class SmartMoneyResponse(BaseModel):
    flows: List[SmartMoneyFlow]
    total_net_flow: float
    updated_at: str


# ============== Helper Functions ==============

def _get_cutoff_time(hours: int) -> str:
    """获取截止时间字符串"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')


# ============== API Endpoints ==============

@router.get("/hot-markets", response_model=HotMarketsResponse)
def get_hot_markets(
    limit: int = Query(default=10, le=50, description="返回数量"),
    category: Optional[str] = Query(default=None, description="分类过滤"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    获取热门市场榜 (使用预计算字段，高性能)
    """
    cursor = conn.cursor()
    import json

    # 使用 markets 表的预计算字段
    query = """
        SELECT
            m.id,
            m.slug,
            m.question,
            m.image,
            m.category,
            m.outcome_prices,
            COALESCE(m.volume_24h, 0) as volume_24h,
            COALESCE(m.trade_count, 0) as trade_count_24h,
            COALESCE(m.unique_traders_24h, 0) as unique_traders_24h
        FROM markets m
        WHERE m.status = 'active'
          AND COALESCE(m.volume_24h, 0) > 0
    """
    params = []

    if category:
        query += " AND m.category = ?"
        params.append(category)

    query += " ORDER BY m.volume_24h DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # 收集市场 ID 以批量获取 24h 价格变化
    market_ids = [row["id"] for row in rows]

    # 批量获取 24h 前的价格（高效单次查询）
    # 注意：数据库时间格式是 ISO 格式 (2026-01-31T03:18:16Z)
    cutoff_24h = _get_cutoff_time(24)
    cutoff_48h = _get_cutoff_time(48)

    price_24h_ago = {}
    if market_ids:
        placeholders = ",".join("?" * len(market_ids))
        cursor.execute(f"""
            WITH ranked AS (
                SELECT market_id, price,
                    ROW_NUMBER() OVER (PARTITION BY market_id ORDER BY timestamp DESC) as rn
                FROM trades
                WHERE market_id IN ({placeholders})
                  AND outcome = 'YES'
                  AND timestamp < ?
                  AND timestamp >= ?
            )
            SELECT market_id, price FROM ranked WHERE rn = 1
        """, market_ids + [cutoff_24h, cutoff_48h])
        for price_row in cursor.fetchall():
            price_24h_ago[price_row[0]] = price_row[1]

    markets = []
    for row in rows:
        market_id = row["id"]

        # 解析 outcome_prices 获取当前价格
        current_price = None
        outcome_prices = row["outcome_prices"]
        if outcome_prices:
            try:
                prices = json.loads(outcome_prices)
                if isinstance(prices, list) and len(prices) > 0:
                    current_price = float(prices[0])  # YES price
            except:
                pass

        # 计算 24h 价格变化
        price_change = None
        old_price = price_24h_ago.get(market_id)
        if current_price and old_price and old_price > 0:
            price_change = round((current_price - old_price) / old_price * 100, 1)

        # 使用预计算的 unique_traders_24h
        trade_count = row["trade_count_24h"] or 0
        unique_traders = row["unique_traders_24h"] or 0

        markets.append(HotMarket(
            id=market_id,
            slug=row["slug"],
            question=row["question"],
            image=row["image"],
            category=row["category"],
            volume_24h=round(row["volume_24h"], 2),
            trade_count_24h=trade_count,
            unique_traders_24h=unique_traders,
            price_change_24h=price_change,
            current_price=round(current_price, 4) if current_price else None,
        ))

    return HotMarketsResponse(
        markets=markets,
        updated_at=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/volume-anomalies", response_model=VolumeAnomalyResponse)
def get_volume_anomalies(
    threshold: float = Query(default=2.0, description="异常阈值倍数"),
    limit: int = Query(default=20, le=50, description="返回数量"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    检测交易量异常的市场

    使用 markets 表的预计算字段（volume_24h vs volume/30）
    """
    cursor = conn.cursor()

    # 使用 markets 表的预计算字段，避免扫描 trades 表
    query = """
        SELECT
            m.id as market_id,
            m.slug,
            m.question,
            m.image,
            COALESCE(m.volume_24h, 0) as volume_24h,
            COALESCE(m.trade_count, 0) as trade_count_24h,
            COALESCE(m.volume, 0) / 30.0 as volume_avg_daily
        FROM markets m
        WHERE m.status = 'active'
          AND COALESCE(m.volume_24h, 0) > 1000
        ORDER BY m.volume_24h DESC
        LIMIT 100
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    anomalies = []
    for row in rows:
        vol_24h = row["volume_24h"] or 0
        vol_avg = row["volume_avg_daily"] or 0

        # 计算比率
        if vol_avg > 0:
            ratio = vol_24h / vol_avg
        else:
            ratio = 10.0 if vol_24h > 5000 else 1.0

        # 只保留超过阈值的
        if ratio >= threshold:
            anomalies.append(VolumeAnomaly(
                market_id=row["market_id"],
                slug=row["slug"],
                question=row["question"],
                image=row["image"],
                volume_24h=round(vol_24h, 2),
                volume_avg_30d=round(vol_avg, 2),
                volume_ratio=round(ratio, 2),
                trade_count_24h=row["trade_count_24h"] or 0,
                anomaly_type="surge",
            ))

            if len(anomalies) >= limit:
                break

    return VolumeAnomalyResponse(
        anomalies=anomalies,
        threshold=threshold,
        updated_at=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/smart-money", response_model=SmartMoneyResponse)
def get_smart_money_flow(
    limit: int = Query(default=20, le=50, description="返回数量"),
    hours: int = Query(default=24, le=168, description="时间范围 (小时)"),
    min_whale_value: float = Query(default=1000, description="鲸鱼交易最小金额"),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    获取 Smart Money (鲸鱼) 资金流向

    使用 whale_trades 表（已预过滤的鲸鱼交易）提高性能
    """
    cursor = conn.cursor()
    cutoff = _get_cutoff_time(hours)

    # 使用 whale_trades 表（更快）
    query = """
        SELECT
            w.market_id,
            m.slug,
            m.question,
            m.image,
            SUM(CASE WHEN UPPER(w.side) = 'BUY' THEN w.usd_value ELSE 0 END) as buy_volume,
            SUM(CASE WHEN UPPER(w.side) = 'SELL' THEN w.usd_value ELSE 0 END) as sell_volume,
            SUM(CASE WHEN UPPER(w.side) = 'BUY' THEN 1 ELSE 0 END) as buy_count,
            SUM(CASE WHEN UPPER(w.side) = 'SELL' THEN 1 ELSE 0 END) as sell_count
        FROM whale_trades w
        JOIN markets m ON w.market_id = m.id
        WHERE w.timestamp >= ?
          AND w.usd_value >= ?
          AND m.status = 'active'
        GROUP BY w.market_id
        HAVING (buy_volume + sell_volume) > 0
        ORDER BY ABS(buy_volume - sell_volume) DESC
        LIMIT ?
    """

    cursor.execute(query, [cutoff, min_whale_value, limit])
    rows = cursor.fetchall()

    flows = []
    total_net = 0.0

    for row in rows:
        buy_vol = row["buy_volume"] or 0
        sell_vol = row["sell_volume"] or 0
        net_flow = buy_vol - sell_vol
        total_net += net_flow

        # 判断方向
        if net_flow > 0:
            direction = "inflow"
        elif net_flow < 0:
            direction = "outflow"
        else:
            direction = "neutral"

        # 判断信号强度
        total_vol = buy_vol + sell_vol
        if total_vol > 0:
            imbalance = abs(net_flow) / total_vol
            if imbalance >= 0.5:
                strength = "strong"
            elif imbalance >= 0.25:
                strength = "moderate"
            else:
                strength = "weak"
        else:
            strength = "weak"

        flows.append(SmartMoneyFlow(
            market_id=row["market_id"],
            slug=row["slug"],
            question=row["question"],
            image=row["image"],
            whale_buy_volume=round(buy_vol, 2),
            whale_sell_volume=round(sell_vol, 2),
            whale_net_flow=round(net_flow, 2),
            whale_buy_count=row["buy_count"] or 0,
            whale_sell_count=row["sell_count"] or 0,
            flow_direction=direction,
            signal_strength=strength,
        ))

    return SmartMoneyResponse(
        flows=flows,
        total_net_flow=round(total_net, 2),
        updated_at=datetime.utcnow().isoformat() + "Z",
    )
