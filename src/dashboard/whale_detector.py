"""
鲸鱼检测器 - 检测并存储大额交易
"""

import sqlite3
from typing import List, Dict

from ..config import WHALE_THRESHOLD


class WhaleDetector:
    """大额交易检测器"""

    def __init__(self, db_path: str, threshold_usd: float = None):
        self.db_path = db_path
        self.threshold = threshold_usd or WHALE_THRESHOLD

    def detect_from_trades(self) -> int:
        """
        扫描 trades 表，将大单写入 whale_trades 表

        Returns:
            检测到的鲸鱼交易数量
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 检测大单 (price * size > threshold)
        # 注意: price 是每个 token 的价格 (0-1), size 是 token 数量
        # USD 价值 = price * size
        cursor.execute(
            """
            INSERT OR IGNORE INTO whale_trades
            (tx_hash, log_index, market_id, trader, side, outcome, price, size, usd_value, block_number, timestamp)
            SELECT
                tx_hash,
                log_index,
                market_id,
                maker as trader,
                side,
                outcome,
                price,
                size,
                (price * size) as usd_value,
                block_number,
                timestamp
            FROM trades
            WHERE (price * size) > ?
            """,
            (self.threshold,),
        )

        inserted = cursor.rowcount
        conn.commit()
        conn.close()

        return inserted

    def detect_new_whales(self) -> List[Dict]:
        """
        增量检测新的鲸鱼交易并返回详情（用于 WebSocket 推送）

        使用 sync_state 表记录上次检测位置，只处理新交易。

        Returns:
            新检测到的鲸鱼交易列表（含市场信息）
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取上次检测位置
        cursor.execute(
            "SELECT last_block FROM sync_state WHERE key = 'whale_sync'"
        )
        row = cursor.fetchone()
        since_trade_id = row["last_block"] if row else 0

        # 查询新的大单（包含市场信息）
        cursor.execute(
            """
            SELECT
                t.id,
                t.tx_hash,
                t.log_index,
                t.market_id,
                t.maker as trader,
                t.side,
                t.outcome,
                t.price,
                t.size,
                (t.price * t.size) as usd_value,
                t.block_number,
                t.timestamp,
                m.slug as market_slug,
                m.question
            FROM trades t
            LEFT JOIN markets m ON t.market_id = m.id
            WHERE t.id > ? AND (t.price * t.size) > ?
            ORDER BY t.id ASC
            """,
            (since_trade_id, self.threshold),
        )

        new_whales = [dict(row) for row in cursor.fetchall()]

        # 插入到 whale_trades 表
        for whale in new_whales:
            cursor.execute(
                """
                INSERT OR IGNORE INTO whale_trades
                (tx_hash, log_index, market_id, trader, side, outcome, price, size, usd_value, block_number, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    whale["tx_hash"],
                    whale["log_index"],
                    whale["market_id"],
                    whale["trader"],
                    whale["side"],
                    whale["outcome"],
                    whale["price"],
                    whale["size"],
                    whale["usd_value"],
                    whale["block_number"],
                    whale["timestamp"],
                ),
            )

        # 更新同步状态
        if new_whales:
            max_id = max(w["id"] for w in new_whales)
            cursor.execute(
                """
                INSERT OR REPLACE INTO sync_state (key, last_block, updated_at)
                VALUES ('whale_sync', ?, datetime('now'))
                """,
                (max_id,),
            )

        conn.commit()
        conn.close()

        return new_whales

    def get_whales(
        self,
        limit: int = 50,
        min_usd: float = None,
        market_id: int = None,
    ) -> List[Dict]:
        """
        获取鲸鱼交易列表

        Args:
            limit: 返回数量限制
            min_usd: 最小 USD 价值
            market_id: 可选，指定市场

        Returns:
            鲸鱼交易列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        min_val = min_usd or self.threshold

        if market_id:
            cursor.execute(
                """
                SELECT w.*, m.question, m.slug as market_slug
                FROM whale_trades w
                LEFT JOIN markets m ON w.market_id = m.id
                WHERE w.usd_value >= ? AND w.market_id = ?
                ORDER BY w.usd_value DESC
                LIMIT ?
                """,
                (min_val, market_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT w.*, m.question, m.slug as market_slug
                FROM whale_trades w
                LEFT JOIN markets m ON w.market_id = m.id
                WHERE w.usd_value >= ?
                ORDER BY w.usd_value DESC
                LIMIT ?
                """,
                (min_val, limit),
            )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_recent_whales(self, limit: int = 20) -> List[Dict]:
        """
        获取最近的鲸鱼交易

        Args:
            limit: 返回数量限制

        Returns:
            最近的鲸鱼交易列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT w.*, m.question, m.slug as market_slug
            FROM whale_trades w
            LEFT JOIN markets m ON w.market_id = m.id
            ORDER BY w.timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_stats(self, min_usd: float = None, market_id: int = None) -> Dict:
        """
        获取鲸鱼交易统计

        Args:
            min_usd: 最小 USD 价值过滤
            market_id: 可选，指定市场 ID

        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT
                COUNT(*) as total_count,
                SUM(usd_value) as total_volume,
                AVG(usd_value) as avg_value,
                MAX(usd_value) as max_value,
                MIN(usd_value) as min_value
            FROM whale_trades
        """
        params = []
        conditions = []

        if min_usd is not None:
            conditions.append("usd_value >= ?")
            params.append(min_usd)
        
        if market_id is not None:
            conditions.append("market_id = ?")
            params.append(market_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        cursor.execute(query, params)

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "total_count": row[0] or 0,
                "total_volume": row[1] or 0,
                "avg_value": row[2] or 0,
                "max_value": row[3] or 0,
                "min_value": row[4] or 0,
            }

        return {
            "total_count": 0,
            "total_volume": 0,
            "avg_value": 0,
            "max_value": 0,
            "min_value": 0,
        }