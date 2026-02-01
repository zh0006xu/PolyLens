"""
K-lines API Routes
K 线数据实时从 trades 表聚合，不存储到数据库
"""

import sqlite3
from typing import List, Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from ..deps import get_db, get_db_path
from ...core.klines import KlineAggregator

router = APIRouter(prefix="/klines", tags=["klines"])


class KlineData(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int


class KlineResponse(BaseModel):
    market_id: int
    interval: str
    klines: List[KlineData]


@router.get("", response_model=KlineResponse)
def get_klines(
    market_id: int = Query(..., description="市场 ID"),
    interval: Literal["1m", "5m", "15m", "1h", "4h", "1d"] = Query(
        default="1h", description="K 线间隔"
    ),
    limit: int = Query(default=100, le=1000, description="返回数量"),
    token_id: Optional[str] = Query(default=None, description="指定 token_id (YES/NO)"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取 K 线数据（从 trades 实时聚合）"""
    cursor = conn.cursor()

    # 验证市场存在
    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # 如果没有指定 token_id，使用 YES token
    target_token = token_id or market["yes_token_id"]

    # 使用 KlineAggregator 从 trades 实时聚合
    aggregator = KlineAggregator(db_path)
    kline_data = aggregator.get_klines(
        market_id=market_id,
        interval=interval,
        limit=limit,
        token_id=target_token,
    )

    klines = [
        KlineData(
            timestamp=k["timestamp"],
            open=k["open"],
            high=k["high"],
            low=k["low"],
            close=k["close"],
            volume=k["volume"],
            trade_count=k["trade_count"],
        )
        for k in kline_data
    ]

    return KlineResponse(market_id=market_id, interval=interval, klines=klines)


@router.get("/price/{market_id}")
def get_latest_price(
    market_id: int,
    token_id: Optional[str] = Query(default=None, description="指定 token_id"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取市场最新价格"""
    cursor = conn.cursor()

    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    target_token = token_id or market["yes_token_id"]

    aggregator = KlineAggregator(db_path)
    return aggregator.get_latest_price(market_id, target_token)


@router.get("/range/{market_id}")
def get_price_range(
    market_id: int,
    token_id: Optional[str] = Query(default=None, description="指定 token_id"),
    hours: int = Query(default=24, description="时间范围（小时）"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取市场价格区间"""
    cursor = conn.cursor()

    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    target_token = token_id or market["yes_token_id"]

    aggregator = KlineAggregator(db_path)
    return aggregator.get_price_range(market_id, target_token, hours)
