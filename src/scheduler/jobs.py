"""
后台调度任务 - 定时同步链上数据
"""

import sqlite3
import logging
import asyncio
from typing import Callable, Optional, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..config import DATABASE_PATH
from ..core.indexer import sync_trades
from ..dashboard.whale_detector import WhaleDetector

logger = logging.getLogger(__name__)


class SyncScheduler:
    """同步调度器 - 定时从链上同步最新交易数据"""

    def __init__(
        self,
        db_path: str = DATABASE_PATH,
        interval_seconds: int = 30,
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

    async def sync_job(self):
        """
        同步任务：索引新交易 -> 检测鲸鱼 -> 推送通知

        K 线数据从 trades 实时聚合，无需额外处理
        """
        if self.is_syncing:
            logger.warning("Previous sync still running, skipping...")
            return

        self.is_syncing = True
        self.sync_count += 1

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # 1. 同步最新交易
            logger.info(f"[Sync #{self.sync_count}] Starting sync...")
            result = sync_trades(conn, batch_size=500)

            inserted = result.get("inserted_trades", 0)
            logger.info(f"[Sync #{self.sync_count}] Synced {inserted} new trades")

            # 2. 检测新鲸鱼并推送通知
            if inserted > 0:
                detector = WhaleDetector(self.db_path, threshold_usd=self.whale_threshold)
                new_whales = detector.detect_new_whales()

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

            conn.close()

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
