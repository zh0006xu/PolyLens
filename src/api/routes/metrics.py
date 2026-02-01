"""
市场指标 API Routes
"""

import sqlite3
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel

from ..deps import get_db, get_db_path
from ...core.metrics import MarketMetrics


router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricsData(BaseModel):
    """指标数据模型"""
    # 买卖压力
    buy_sell_ratio: Optional[float] = None
    buy_percentage: float = 50.0
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    buy_count: int = 0
    sell_count: int = 0

    # VWAP
    vwap: Optional[float] = None
    current_price: Optional[float] = None
    price_vs_vwap: Optional[float] = None
    total_volume: float = 0.0

    # 鲸鱼信号
    whale_signal: str = "neutral"
    whale_buy_volume: float = 0.0
    whale_sell_volume: float = 0.0
    whale_ratio: Optional[float] = None

    # 交易者统计
    unique_traders: int = 0
    total_trades: int = 0
    avg_trade_size: float = 0.0

    # 资金流
    net_flow: float = 0.0
    flow_direction: str = "neutral"


class MetricsResponse(BaseModel):
    """指标响应模型"""
    market_id: int
    token_id: Optional[str] = None
    period: str
    metrics: MetricsData


@router.get("/{market_id}", response_model=MetricsResponse)
def get_market_metrics(
    market_id: int,
    token_id: Optional[str] = Query(default=None, description="Token ID (可选,默认 YES)"),
    period: Literal["1h", "4h", "24h", "7d", "30d"] = Query(
        default="24h", description="统计周期"
    ),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    获取市场的核心指标

    返回买卖压力比、VWAP、鲸鱼信号等指标数据
    """
    cursor = conn.cursor()

    # 验证市场存在
    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # 如果没有指定 token_id，使用 YES token
    target_token = token_id or market["yes_token_id"]

    # 计算指标
    calculator = MarketMetrics(db_path)
    result = calculator.get_all_metrics(market_id, target_token, period)

    return MetricsResponse(
        market_id=market_id,
        token_id=target_token,
        period=period,
        metrics=MetricsData(**result["metrics"])
    )


@router.get("/{market_id}/buy-sell-ratio")
def get_buy_sell_ratio(
    market_id: int,
    token_id: Optional[str] = Query(default=None),
    period: Literal["1h", "4h", "24h", "7d", "30d"] = Query(default="24h"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取买卖压力比"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    target_token = token_id or market["yes_token_id"]
    calculator = MarketMetrics(db_path)
    return calculator.calculate_buy_sell_ratio(market_id, target_token, period)


@router.get("/{market_id}/vwap")
def get_vwap(
    market_id: int,
    token_id: Optional[str] = Query(default=None),
    period: Literal["1h", "4h", "24h", "7d", "30d"] = Query(default="24h"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取 VWAP (成交量加权平均价)"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    target_token = token_id or market["yes_token_id"]
    calculator = MarketMetrics(db_path)
    return calculator.calculate_vwap(market_id, target_token, period)


@router.get("/{market_id}/whale-signal")
def get_whale_signal(
    market_id: int,
    token_id: Optional[str] = Query(default=None),
    period: Literal["1h", "4h", "24h", "7d", "30d"] = Query(default="24h"),
    threshold: float = Query(default=1000.0, description="鲸鱼阈值 (USD)"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取鲸鱼信号"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    target_token = token_id or market["yes_token_id"]
    calculator = MarketMetrics(db_path, whale_threshold=threshold)
    return calculator.calculate_whale_signal(market_id, target_token, period)


@router.get("/{market_id}/traders")
def get_trader_stats(
    market_id: int,
    token_id: Optional[str] = Query(default=None),
    period: Literal["1h", "4h", "24h", "7d", "30d"] = Query(default="24h"),
    db_path: str = Depends(get_db_path),
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取交易者统计"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, yes_token_id FROM markets WHERE id = ?", (market_id,))
    market = cursor.fetchone()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    target_token = token_id or market["yes_token_id"]
    calculator = MarketMetrics(db_path)
    return calculator.calculate_trader_stats(market_id, target_token, period)
