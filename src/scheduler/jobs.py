"""
后台调度任务 - 定时同步链上数据
"""

import sqlite3
import logging
import asyncio
import httpx
from typing import Callable, Optional, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import DATABASE_PATH
from ..core.indexer import sync_trades
from ..core.whale_detector import WhaleDetector

logger = logging.getLogger(__name__)


def _get_market_status(data: dict) -> str:
    """从 Gamma API 数据推断市场状态"""
    if data.get("archived"):
        return "archived"
    if data.get("closed"):
        return "closed"
    if data.get("active") is False:
        return "closed"
    return "active"


def _refresh_prices_from_polymarket(conn: sqlite3.Connection, limit: int = 50, max_workers: int = 10) -> int:
    """
    从 Polymarket Gamma API 刷新活跃市场的 outcome_prices、status 和 event_slug
    使用并行请求加速（约 2 秒刷新 50 个市场）

    Args:
        limit: 刷新市场数量
        max_workers: 并发请求数（默认 10，太高可能触发 API rate limit）
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cursor = conn.cursor()

    # 获取最活跃的市场（按交易量排序）
    cursor.execute("""
        SELECT id, slug, event_id FROM markets
        WHERE status = 'active' AND slug IS NOT NULL
        ORDER BY volume DESC
        LIMIT ?
    """, (limit,))

    markets = cursor.fetchall()
    if not markets:
        return 0

    def fetch_market_data(market_id, slug, event_id):
        try:
            resp = httpx.get(
                f"https://gamma-api.polymarket.com/markets",
                params={"slug": slug},
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    market_data = data[0]
                    # Extract event slug from embedded events
                    event_slug = None
                    events = market_data.get("events", [])
                    if events and len(events) > 0:
                        event_slug = events[0].get("slug")
                    return market_id, {
                        "outcome_prices": market_data.get("outcomePrices"),
                        "status": _get_market_status(market_data),
                        "event_id": event_id,
                        "event_slug": event_slug,
                    }
        except Exception:
            pass
        return market_id, None

    # 并行请求
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_market_data, m[0], m[1], m[2]) for m in markets]
        results = [f.result() for f in as_completed(futures)]

    # 批量更新数据库
    updated = 0
    event_updates = {}
    for market_id, market_data in results:
        if market_data:
            cursor.execute(
                "UPDATE markets SET outcome_prices = ?, status = ? WHERE id = ?",
                (market_data["outcome_prices"], market_data["status"], market_id)
            )
            updated += 1
            # Collect event slug updates
            if market_data.get("event_id") and market_data.get("event_slug"):
                event_updates[market_data["event_id"]] = market_data["event_slug"]

    # Update event slugs
    for event_id, event_slug in event_updates.items():
        cursor.execute(
            "UPDATE events SET slug = ? WHERE id = ?",
            (event_slug, event_id)
        )

    conn.commit()
    return updated


def _update_unique_traders(conn: sqlite3.Connection, limit: int = 50) -> int:
    """
    更新活跃市场的 unique_traders_24h（24小时内的独立交易者数量）

    只计算 top N 热门市场以保证性能（使用覆盖索引优化）
    """
    cursor = conn.cursor()

    # 获取需要更新的热门市场
    cursor.execute("""
        SELECT id FROM markets
        WHERE status = 'active'
        ORDER BY volume_24h DESC
        LIMIT ?
    """, (limit,))
    market_ids = [row[0] for row in cursor.fetchall()]

    if not market_ids:
        return 0

    # 批量计算 unique traders（使用覆盖索引 idx_trades_timestamp_market_taker）
    placeholders = ",".join("?" * len(market_ids))
    cursor.execute(f"""
        SELECT market_id, COUNT(DISTINCT taker) as unique_traders
        FROM trades
        WHERE market_id IN ({placeholders})
          AND timestamp >= datetime('now', '-24 hours')
        GROUP BY market_id
    """, market_ids)

    # 批量更新
    updated = 0
    for row in cursor.fetchall():
        cursor.execute(
            "UPDATE markets SET unique_traders_24h = ? WHERE id = ?",
            (row[1], row[0])
        )
        updated += 1

    conn.commit()
    return updated


class SyncScheduler:
    """同步调度器 - 定时从链上同步最新交易数据"""

    def __init__(
        self,
        db_path: str = DATABASE_PATH,
        interval_seconds: int = 10,
        whale_threshold: float = 1000.0,
    ):
        """
        初始化调度器

        Args:
            db_path: 数据库路径
            interval_seconds: 同步间隔（秒）
            whale_threshold: 鲸鱼交易阈值（USD）
        """
        self.db_path = db_path
        self.interval = interval_seconds
        self.whale_threshold = whale_threshold
        self.scheduler = AsyncIOScheduler()
        self.is_syncing = False
        self.last_sync_result: Optional[dict] = None
        self.sync_count = 0

        # 鲸鱼通知回调（由外部注入）
        self.whale_notifier: Optional[Callable[[dict], Any]] = None

    def _sync_trades_sync(self) -> dict:
        """
        同步执行交易索引（在线程池中运行）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            result = sync_trades(conn, batch_size=500)
            return result
        finally:
            conn.close()

    async def sync_job(self):
        """
        同步任务：索引新交易 -> 检测鲸鱼 -> 推送通知

        K 线数据从 trades 实时聚合，无需额外处理
        使用 asyncio.to_thread 避免阻塞事件循环
        """
        if self.is_syncing:
            logger.warning("Previous sync still running, skipping...")
            return

        self.is_syncing = True
        self.sync_count += 1

        try:
            # 1. 同步最新交易 (在线程池中执行，不阻塞事件循环)
            logger.info(f"[Sync #{self.sync_count}] Starting sync...")
            result = await asyncio.to_thread(self._sync_trades_sync)

            inserted = result.get("inserted_trades", 0)
            logger.info(f"[Sync #{self.sync_count}] Synced {inserted} new trades")

            # 2. 每次同步都刷新市场价格 (从 Polymarket API，约 2 秒)
            def refresh_prices():
                with sqlite3.connect(self.db_path) as conn:
                    return _refresh_prices_from_polymarket(conn, limit=50)

            price_updated = await asyncio.to_thread(refresh_prices)
            if price_updated > 0:
                logger.info(f"[Sync #{self.sync_count}] Refreshed {price_updated} markets (prices & status)")

            # 2.5 更新热门市场的 unique_traders_24h (约 3 秒)
            def update_traders():
                with sqlite3.connect(self.db_path) as conn:
                    return _update_unique_traders(conn, limit=50)

            traders_updated = await asyncio.to_thread(update_traders)
            if traders_updated > 0:
                logger.info(f"[Sync #{self.sync_count}] Updated unique_traders for {traders_updated} markets")

            # 3. 检测新鲸鱼并推送通知 (在线程池中执行)
            if inserted > 0:
                def detect_whales():
                    detector = WhaleDetector(self.db_path, threshold_usd=self.whale_threshold)
                    return detector.detect_new_whales()

                new_whales = await asyncio.to_thread(detect_whales)

                if new_whales:
                    logger.info(
                        f"[Sync #{self.sync_count}] Detected {len(new_whales)} new whale trades"
                    )

                    # 逐个推送鲸鱼警报
                    if self.whale_notifier:
                        for whale in new_whales:
                            try:
                                if asyncio.iscoroutinefunction(self.whale_notifier):
                                    await self.whale_notifier(whale)
                                else:
                                    self.whale_notifier(whale)
                            except Exception as e:
                                logger.error(f"Failed to notify whale: {e}")

            self.last_sync_result = {
                "sync_count": self.sync_count,
                "inserted_trades": inserted,
                "discovered_markets": result.get("discovered_markets", 0),
                "from_block": result.get("from_block"),
                "to_block": result.get("to_block"),
            }

        except Exception as e:
            logger.error(f"[Sync #{self.sync_count}] Sync job failed: {e}")
            self.last_sync_result = {
                "sync_count": self.sync_count,
                "error": str(e),
            }
        finally:
            self.is_syncing = False

    def start(self):
        """启动调度器"""
        self.scheduler.add_job(
            self.sync_job,
            trigger=IntervalTrigger(seconds=self.interval),
            id="sync_trades",
            name="Sync blockchain trades",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            f"Scheduler started: syncing every {self.interval}s, "
            f"whale threshold ${self.whale_threshold}"
        )

    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    async def trigger_sync(self) -> dict:
        """手动触发一次同步"""
        await self.sync_job()
        return self.last_sync_result or {}

    @property
    def status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self.scheduler.running,
            "is_syncing": self.is_syncing,
            "interval_seconds": self.interval,
            "sync_count": self.sync_count,
            "last_result": self.last_sync_result,
            "whale_threshold": self.whale_threshold,
        }
