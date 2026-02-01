"""
Whale Trades API Routes
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..deps import get_db, get_db_path
from ...dashboard.whale_detector import WhaleDetector

router = APIRouter(prefix="/whales", tags=["whales"])


class WhaleTradeResponse(BaseModel):
    id: int
    tx_hash: str
    log_index: int
    market_id: Optional[int] = None
    market_slug: Optional[str] = None
    question: Optional[str] = None
    trader: Optional[str] = None
    side: Optional[str] = None
    outcome: Optional[str] = None
    price: Optional[float] = None
    size: Optional[float] = None
    usd_value: Optional[float] = None
    block_number: Optional[int] = None
    timestamp: Optional[str] = None


class WhaleListResponse(BaseModel):
    whales: List[WhaleTradeResponse]
    total: int


class WhaleStatsResponse(BaseModel):
    total_count: int
    total_volume: float
    avg_value: float
    max_value: float
    min_value: float


@router.get("", response_model=WhaleListResponse)
def get_whales(
    limit: int = Query(default=50, le=200, description="返回数量"),
    min_usd: Optional[float] = Query(default=None, description="最小 USD 价值"),
    market_id: Optional[int] = Query(default=None, description="市场 ID"),
    db_path: str = Depends(get_db_path),
):
    """获取鲸鱼交易列表（按 USD 价值排序）"""
    detector = WhaleDetector(db_path)
    rows = detector.get_whales(limit=limit, min_usd=min_usd, market_id=market_id)

    whales = [
        WhaleTradeResponse(
            id=row["id"],
            tx_hash=row["tx_hash"],
            log_index=row["log_index"],
            market_id=row.get("market_id"),
            market_slug=row.get("market_slug"),
            question=row.get("question"),
            trader=row.get("trader"),
            side=row.get("side"),
            outcome=row.get("outcome"),
            price=row.get("price"),
            size=row.get("size"),
            usd_value=row.get("usd_value"),
            block_number=row.get("block_number"),
            timestamp=row.get("timestamp"),
        )
        for row in rows
    ]

    # 获取总数（应用相同过滤条件）
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    min_val = min_usd or detector.threshold
    if market_id:
        cursor.execute(
            "SELECT COUNT(*) FROM whale_trades WHERE usd_value >= ? AND market_id = ?",
            (min_val, market_id),
        )
    else:
        cursor.execute("SELECT COUNT(*) FROM whale_trades WHERE usd_value >= ?", (min_val,))
    total = cursor.fetchone()[0]
    conn.close()

    return WhaleListResponse(whales=whales, total=total)


@router.get("/recent", response_model=WhaleListResponse)
def get_recent_whales(
    limit: int = Query(default=20, le=100, description="返回数量"),
    db_path: str = Depends(get_db_path),
):
    """获取最近的鲸鱼交易（按时间排序）"""
    detector = WhaleDetector(db_path)
    rows = detector.get_recent_whales(limit=limit)

    whales = [
        WhaleTradeResponse(
            id=row["id"],
            tx_hash=row["tx_hash"],
            log_index=row["log_index"],
            market_id=row.get("market_id"),
            market_slug=row.get("market_slug"),
            question=row.get("question"),
            trader=row.get("trader"),
            side=row.get("side"),
            outcome=row.get("outcome"),
            price=row.get("price"),
            size=row.get("size"),
            usd_value=row.get("usd_value"),
            block_number=row.get("block_number"),
            timestamp=row.get("timestamp"),
        )
        for row in rows
    ]

    return WhaleListResponse(whales=whales, total=len(whales))


@router.get("/stats", response_model=WhaleStatsResponse)
def get_whale_stats(
    min_usd: Optional[float] = Query(default=None, description="最小 USD 价值"),
    market_id: Optional[int] = Query(default=None, description="市场 ID"),
    db_path: str = Depends(get_db_path),
):
    """获取鲸鱼交易统计"""
    detector = WhaleDetector(db_path)
    stats = detector.get_stats(min_usd=min_usd, market_id=market_id)

    return WhaleStatsResponse(
        total_count=stats["total_count"],
        total_volume=stats["total_volume"],
        avg_value=stats["avg_value"],
        max_value=stats["max_value"],
        min_value=stats["min_value"],
    )


@router.post("/detect")
def detect_whales(
    threshold: Optional[float] = Query(default=None, description="检测阈值 (USD)"),
    db_path: str = Depends(get_db_path),
):
    """触发鲸鱼检测"""
    detector = WhaleDetector(db_path, threshold_usd=threshold)
    count = detector.detect_from_trades()

    return {"message": f"Detected {count} whale trades", "count": count}
