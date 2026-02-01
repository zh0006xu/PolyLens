"""
K线聚合器 - 从 trades 表实时聚合 OHLCV 数据

注意: K 线数据不再存储到数据库，而是实时从 trades 表计算
"""

import sqlite3
from typing import List, Dict, Literal

Interval = Literal['1m', '5m', '15m', '1h', '4h', '1d']

INTERVAL_SECONDS = {
    '1m': 60,
    '5m': 300,
    '15m': 900,
    '1h': 3600,
    '4h': 14400,
    '1d': 86400,
}


class KlineAggregator:
    """K线数据聚合器 - 实时从 trades 表计算"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_klines(
        self,
        market_id: int,
        interval: Interval = '1h',
        limit: int = 100,
        token_id: str = None,
    ) -> List[Dict]:
        """
        从 trades 表实时聚合 K 线数据

        Args:
            market_id: 市场 ID
            interval: K 线间隔
            limit: 返回数量限制
            token_id: 可选，指定 token_id

        Returns:
            K 线数据列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        interval_sec = INTERVAL_SECONDS.get(interval, 3600)

        # 构建查询条件
        if token_id:
            where_clause = "WHERE market_id = ? AND token_id = ? AND price > 0"
            params = [market_id, token_id]
        else:
            where_clause = "WHERE market_id = ? AND price > 0"
            params = [market_id]

        # 从 trades 表实时聚合 OHLCV
        # timestamp 格式: ISO 8601 (2024-12-27T21:38:30Z)
        # 使用子查询获取每个周期的第一条和最后一条记录的价格作为 open/close
        query = f"""
        WITH trade_periods AS (
            SELECT
                *,
                (CAST(strftime('%s', replace(timestamp, 'Z', '+00:00')) AS INTEGER) / {interval_sec}) * {interval_sec} AS period
            FROM trades
            {where_clause}
        ),
        period_stats AS (
            SELECT
                period,
                MIN(price) AS low,
                MAX(price) AS high,
                SUM(price * size) AS volume,
                COUNT(*) AS trade_count,
                MIN(timestamp) AS first_ts,
                MAX(timestamp) AS last_ts
            FROM trade_periods
            GROUP BY period
        )
        SELECT
            ps.period AS timestamp,
            (SELECT price FROM trade_periods tp WHERE tp.period = ps.period AND tp.timestamp = ps.first_ts LIMIT 1) AS open,
            ps.high,
            ps.low,
            (SELECT price FROM trade_periods tp WHERE tp.period = ps.period AND tp.timestamp = ps.last_ts LIMIT 1) AS close,
            ps.volume,
            ps.trade_count
        FROM period_stats ps
        ORDER BY ps.period DESC
        LIMIT ?
        """

        cursor.execute(query, params + [limit])
        rows = cursor.fetchall()
        conn.close()

        # 转换为字典列表，按时间正序
        klines = [dict(row) for row in reversed(rows)]
        return klines

    def get_latest_price(self, market_id: int, token_id: str = None) -> Dict:
        """
        获取最新价格

        Args:
            market_id: 市场 ID
            token_id: 可选，指定 token_id

        Returns:
            {'price': float, 'timestamp': str}
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if token_id:
            cursor.execute(
                """
                SELECT price, timestamp
                FROM trades
                WHERE market_id = ? AND token_id = ? AND price > 0
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (market_id, token_id),
            )
        else:
            cursor.execute(
                """
                SELECT price, timestamp
                FROM trades
                WHERE market_id = ? AND price > 0
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (market_id,),
            )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {'price': row['price'], 'timestamp': row['timestamp']}
        return {'price': None, 'timestamp': None}

    def get_price_range(
        self,
        market_id: int,
        token_id: str = None,
        hours: int = 24,
    ) -> Dict:
        """
        获取指定时间范围内的价格区间

        Args:
            market_id: 市场 ID
            token_id: 可选，指定 token_id
            hours: 时间范围（小时）

        Returns:
            {'high': float, 'low': float, 'open': float, 'close': float, 'volume': float}
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 构建时间过滤
        time_filter = f"datetime(timestamp) >= datetime('now', '-{hours} hours')"

        if token_id:
            where_clause = f"WHERE market_id = ? AND token_id = ? AND price > 0 AND {time_filter}"
            params = [market_id, token_id]
        else:
            where_clause = f"WHERE market_id = ? AND price > 0 AND {time_filter}"
            params = [market_id]

        cursor.execute(
            f"""
            SELECT
                MIN(price) as low,
                MAX(price) as high,
                SUM(price * size) as volume,
                COUNT(*) as trade_count
            FROM trades
            {where_clause}
            """,
            params,
        )

        stats = cursor.fetchone()

        # 获取开盘价和收盘价
        cursor.execute(
            f"""
            SELECT price FROM trades
            {where_clause}
            ORDER BY timestamp ASC LIMIT 1
            """,
            params,
        )
        open_row = cursor.fetchone()

        cursor.execute(
            f"""
            SELECT price FROM trades
            {where_clause}
            ORDER BY timestamp DESC LIMIT 1
            """,
            params,
        )
        close_row = cursor.fetchone()

        conn.close()

        return {
            'high': stats['high'] if stats else None,
            'low': stats['low'] if stats else None,
            'open': open_row['price'] if open_row else None,
            'close': close_row['price'] if close_row else None,
            'volume': stats['volume'] if stats else 0,
            'trade_count': stats['trade_count'] if stats else 0,
        }