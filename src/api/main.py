"""
FastAPI 主入口 - 包含后台调度器和 WebSocket 支持
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import (
    markets_router,
    klines_router,
    whales_router,
    ws_router,
    metrics_router,
    categories_router,
    traders_router,
)
from .websocket.manager import ws_manager
from ..scheduler.jobs import SyncScheduler
from ..config import DATABASE_PATH

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler: SyncScheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理 - 启动/停止后台调度器"""
    global scheduler

    # 从环境变量读取配置
    db_path = os.environ.get("DATABASE_PATH", DATABASE_PATH)
    sync_interval = int(os.environ.get("SYNC_INTERVAL", "30"))
    enable_scheduler = os.environ.get("ENABLE_SCHEDULER", "1") == "1"
    whale_threshold = float(os.environ.get("WHALE_THRESHOLD", "1000"))

    # 启动调度器
    if enable_scheduler:
        scheduler = SyncScheduler(
            db_path=db_path,
            interval_seconds=sync_interval,
            whale_threshold=whale_threshold,
        )

        # 注入 WebSocket 通知回调
        scheduler.whale_notifier = ws_manager.broadcast_whale_alert

        scheduler.start()
        logger.info(f"Background scheduler enabled: interval={sync_interval}s")
    else:
        logger.info("Background scheduler disabled")

    yield

    # 停止调度器
    if scheduler:
        scheduler.stop()


app = FastAPI(
    title="Polymarket Sentiment Dashboard API",
    description="市场情绪仪表盘 API - 提供市场数据、K线、鲸鱼交易、WebSocket 实时推送",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(markets_router, prefix="/api")
app.include_router(klines_router, prefix="/api")
app.include_router(whales_router, prefix="/api")
app.include_router(ws_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(traders_router, prefix="/api")


@app.get("/")
def root():
    """API 根路径"""
    return {
        "name": "Polymarket Sentiment Dashboard API",
        "version": "0.3.0",
        "docs": "/docs",
        "endpoints": {
            "markets": "/api/markets",
            "categories": "/api/categories",
            "klines": "/api/klines",
            "whales": "/api/whales",
            "metrics": "/api/metrics/{market_id}",
            "traders": "/api/traders/{address}",
            "websocket_whales": "ws://host/api/ws/whales",
            "websocket_trades": "ws://host/api/ws/trades",
            "websocket_status": "/api/ws/status",
            "scheduler_status": "/api/scheduler/status",
        },
    }


@app.get("/health")
def health():
    """健康检查"""
    return {
        "status": "ok",
        "scheduler": scheduler.status if scheduler else None,
        "websocket": ws_manager.status,
    }


@app.get("/api/stats")
def get_stats():
    """获取整体统计信息"""
    import sqlite3
    from ..config import DATABASE_PATH

    db_path = os.environ.get("DATABASE_PATH", DATABASE_PATH)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}

    # 各表记录数 (K 线不再存储，实时从 trades 计算)
    for table in ["events", "markets", "trades", "whale_trades"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats[f"{table}_count"] = 0

    # 同步状态
    try:
        cursor.execute("SELECT key, last_block FROM sync_state")
        stats["sync_state"] = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        stats["sync_state"] = {}

    conn.close()

    return stats


@app.get("/api/scheduler/status")
async def scheduler_status():
    """获取调度器状态"""
    if scheduler is None:
        return {
            "enabled": False,
            "message": "Scheduler not initialized (use --no-scheduler to disable)",
        }
    return {
        "enabled": True,
        **scheduler.status,
    }


@app.post("/api/scheduler/trigger")
async def scheduler_trigger():
    """手动触发一次同步"""
    if scheduler is None:
        return {"error": "Scheduler not enabled"}

    result = await scheduler.trigger_sync()
    return {
        "message": "Sync triggered",
        "result": result,
    }
