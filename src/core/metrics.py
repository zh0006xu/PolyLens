"""
市场指标计算模块

提供买卖压力比、VWAP、鲸鱼信号等核心指标计算
"""

import sqlite3
from typing import Dict, Optional, Literal
from datetime import datetime, timedelta


Period = Literal['1h', '4h', '24h', '7d', '30d']

PERIOD_SECONDS = {
    '1h': 3600,
    '4h': 14400,
    '24h': 86400,
    '7d': 604800,
    '30d': 2592000,
}


class MarketMetrics:
    """市场指标计算器"""

    def __init__(self, db_path: str, whale_threshold: float = 1000.0):
        """
        初始化指标计算器

        Args:
            db_path: 数据库路径
            whale_threshold: 鲸鱼交易阈值 (USD)
        """
        self.db_path = db_path
        self.whale_threshold = whale_threshold

    def _get_time_filter(self, period: Period) -> str:
        """获取时间过滤条件"""
        seconds = PERIOD_SECONDS.get(period, 86400)
        # 计算截止时间戳
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        cutoff_iso = cutoff.strftime('%Y-%m-%dT%H:%M:%SZ')
        return f"timestamp >= '{cutoff_iso}'"

    def calculate_buy_sell_ratio(
        self,
        market_id: int,
        token_id: Optional[str] = None,
        period: Period = '24h'
    ) -> Dict:
        """
        计算买卖压力比

        Args:
            market_id: 市场 ID
            token_id: Token ID (可选)
            period: 统计周期

        Returns:
            {
                'buy_volume': float,
                'sell_volume': float,
                'buy_count': int,
                'sell_count': int,
                'buy_sell_ratio': float,
                'buy_percentage': float
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        time_filter = self._get_time_filter(period)

        # 构建查询条件
        where_clauses = [f"market_id = ?", time_filter, "price > 0"]
        params = [market_id]

        if token_id:
            where_clauses.append("token_id = ?")
            params.append(token_id)

        where_sql = " AND ".join(where_clauses)

        # 分别统计买入和卖出
        cursor.execute(
            f"""
            SELECT
                side,
                SUM(price * size) as volume,
                COUNT(*) as count
            FROM trades
            WHERE {where_sql}
            GROUP BY side
            """,
            params
        )

        rows = cursor.fetchall()
        conn.close()

        buy_volume = 0.0
        sell_volume = 0.0
        buy_count = 0
        sell_count = 0

        for row in rows:
            side = row['side']
            if side and side.upper() == 'BUY':
                buy_volume = float(row['volume'] or 0)
                buy_count = int(row['count'] or 0)
            elif side and side.upper() == 'SELL':
                sell_volume = float(row['volume'] or 0)
                sell_count = int(row['count'] or 0)

        total_volume = buy_volume + sell_volume
        ratio = buy_volume / sell_volume if sell_volume > 0 else float('inf') if buy_volume > 0 else 1.0
        buy_pct = (buy_volume / total_volume * 100) if total_volume > 0 else 50.0

        return {
            'buy_volume': round(buy_volume, 2),
            'sell_volume': round(sell_volume, 2),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'buy_sell_ratio': round(ratio, 2) if ratio != float('inf') else None,
            'buy_percentage': round(buy_pct, 1),
        }

    def calculate_vwap(
        self,
        market_id: int,
        token_id: Optional[str] = None,
        period: Period = '24h'
    ) -> Dict:
        """
        计算成交量加权平均价 (VWAP)

        VWAP = Σ(price × size) / Σ(size)

        Args:
            market_id: 市场 ID
            token_id: Token ID (可选)
            period: 统计周期

        Returns:
            {
                'vwap': float,
                'current_price': float,
                'price_vs_vwap': float (百分比偏差),
                'total_volume': float,
                'total_size': float
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        time_filter = self._get_time_filter(period)

        # 构建查询条件
        where_clauses = [f"market_id = ?", time_filter, "price > 0", "size > 0"]
        params = [market_id]

        if token_id:
            where_clauses.append("token_id = ?")
            params.append(token_id)

        where_sql = " AND ".join(where_clauses)

        # 计算 VWAP
        cursor.execute(
            f"""
            SELECT
                SUM(price * size) as total_value,
                SUM(size) as total_size,
                SUM(price * size) as total_volume
            FROM trades
            WHERE {where_sql}
            """,
            params
        )

        row = cursor.fetchone()

        total_value = float(row['total_value'] or 0)
        total_size = float(row['total_size'] or 0)
        total_volume = float(row['total_volume'] or 0)

        vwap = total_value / total_size if total_size > 0 else None

        # 获取最新价格
        cursor.execute(
            f"""
            SELECT price
            FROM trades
            WHERE {where_sql}
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            params
        )

        price_row = cursor.fetchone()
        current_price = float(price_row['price']) if price_row else None

        conn.close()

        # 计算价格与 VWAP 的偏差
        price_vs_vwap = None
        if vwap and current_price:
            price_vs_vwap = round((current_price - vwap) / vwap * 100, 2)

        return {
            'vwap': round(vwap, 4) if vwap else None,
            'current_price': round(current_price, 4) if current_price else None,
            'price_vs_vwap': price_vs_vwap,
            'total_volume': round(total_volume, 2),
            'total_size': round(total_size, 2),
        }

    def calculate_whale_signal(
        self,
        market_id: int,
        token_id: Optional[str] = None,
        period: Period = '24h',
        threshold: Optional[float] = None
    ) -> Dict:
        """
        计算鲸鱼信号

        Args:
            market_id: 市场 ID
            token_id: Token ID (可选)
            period: 统计周期
            threshold: 鲸鱼阈值 (USD), 默认使用实例阈值

        Returns:
            {
                'signal': str ('bullish', 'bearish', 'neutral'),
                'whale_buy_volume': float,
                'whale_sell_volume': float,
                'whale_buy_count': int,
                'whale_sell_count': int,
                'whale_ratio': float
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        time_filter = self._get_time_filter(period)
        whale_thresh = threshold or self.whale_threshold

        # 构建查询条件
        where_clauses = [
            f"market_id = ?",
            time_filter,
            "price > 0",
            f"(price * size) >= {whale_thresh}"
        ]
        params = [market_id]

        if token_id:
            where_clauses.append("token_id = ?")
            params.append(token_id)

        where_sql = " AND ".join(where_clauses)

        # 统计鲸鱼买卖
        cursor.execute(
            f"""
            SELECT
                side,
                SUM(price * size) as volume,
                COUNT(*) as count
            FROM trades
            WHERE {where_sql}
            GROUP BY side
            """,
            params
        )

        rows = cursor.fetchall()
        conn.close()

        whale_buy_volume = 0.0
        whale_sell_volume = 0.0
        whale_buy_count = 0
        whale_sell_count = 0

        for row in rows:
            side = row['side']
            if side and side.upper() == 'BUY':
                whale_buy_volume = float(row['volume'] or 0)
                whale_buy_count = int(row['count'] or 0)
            elif side and side.upper() == 'SELL':
                whale_sell_volume = float(row['volume'] or 0)
                whale_sell_count = int(row['count'] or 0)

        # 计算信号
        total_whale = whale_buy_volume + whale_sell_volume
        if total_whale == 0:
            signal = 'neutral'
            whale_ratio = 1.0
        else:
            buy_pct = whale_buy_volume / total_whale
            if buy_pct > 0.6:
                signal = 'bullish'
            elif buy_pct < 0.4:
                signal = 'bearish'
            else:
                signal = 'neutral'
            whale_ratio = whale_buy_volume / whale_sell_volume if whale_sell_volume > 0 else float('inf')

        return {
            'signal': signal,
            'whale_buy_volume': round(whale_buy_volume, 2),
            'whale_sell_volume': round(whale_sell_volume, 2),
            'whale_buy_count': whale_buy_count,
            'whale_sell_count': whale_sell_count,
            'whale_ratio': round(whale_ratio, 2) if whale_ratio != float('inf') else None,
        }

    def calculate_trader_stats(
        self,
        market_id: int,
        token_id: Optional[str] = None,
        period: Period = '24h'
    ) -> Dict:
        """
        计算交易者统计

        Args:
            market_id: 市场 ID
            token_id: Token ID (可选)
            period: 统计周期

        Returns:
            {
                'unique_traders': int,
                'total_trades': int,
                'avg_trade_size': float
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        time_filter = self._get_time_filter(period)

        # 构建查询条件
        where_clauses = [f"market_id = ?", time_filter]
        params = [market_id]

        if token_id:
            where_clauses.append("token_id = ?")
            params.append(token_id)

        where_sql = " AND ".join(where_clauses)

        # 统计交易者
        cursor.execute(
            f"""
            SELECT
                COUNT(DISTINCT maker) as unique_makers,
                COUNT(DISTINCT taker) as unique_takers,
                COUNT(*) as total_trades,
                AVG(price * size) as avg_trade_size
            FROM trades
            WHERE {where_sql}
            """,
            params
        )

        row = cursor.fetchone()
        conn.close()

        # 合并 maker 和 taker 的去重数量 (简化处理)
        unique_makers = int(row['unique_makers'] or 0)
        unique_takers = int(row['unique_takers'] or 0)
        # 实际去重需要更复杂的查询,这里用近似值
        unique_traders = max(unique_makers, unique_takers)

        return {
            'unique_traders': unique_traders,
            'total_trades': int(row['total_trades'] or 0),
            'avg_trade_size': round(float(row['avg_trade_size'] or 0), 2),
        }

    def calculate_net_flow(
        self,
        market_id: int,
        token_id: Optional[str] = None,
        period: Period = '24h'
    ) -> Dict:
        """
        计算净资金流入

        Args:
            market_id: 市场 ID
            token_id: Token ID (可选)
            period: 统计周期

        Returns:
            {
                'net_flow': float,
                'flow_direction': str ('inflow', 'outflow', 'neutral')
            }
        """
        bs = self.calculate_buy_sell_ratio(market_id, token_id, period)

        net_flow = bs['buy_volume'] - bs['sell_volume']

        if net_flow > 0:
            direction = 'inflow'
        elif net_flow < 0:
            direction = 'outflow'
        else:
            direction = 'neutral'

        return {
            'net_flow': round(net_flow, 2),
            'flow_direction': direction,
        }

    def get_all_metrics(
        self,
        market_id: int,
        token_id: Optional[str] = None,
        period: Period = '24h'
    ) -> Dict:
        """
        获取市场的所有核心指标

        Args:
            market_id: 市场 ID
            token_id: Token ID (可选)
            period: 统计周期

        Returns:
            完整的指标字典
        """
        buy_sell = self.calculate_buy_sell_ratio(market_id, token_id, period)
        vwap_data = self.calculate_vwap(market_id, token_id, period)
        whale_signal = self.calculate_whale_signal(market_id, token_id, period)
        trader_stats = self.calculate_trader_stats(market_id, token_id, period)
        net_flow = self.calculate_net_flow(market_id, token_id, period)

        return {
            'market_id': market_id,
            'token_id': token_id,
            'period': period,
            'metrics': {
                # 买卖压力
                'buy_sell_ratio': buy_sell['buy_sell_ratio'],
                'buy_percentage': buy_sell['buy_percentage'],
                'buy_volume': buy_sell['buy_volume'],
                'sell_volume': buy_sell['sell_volume'],
                'buy_count': buy_sell['buy_count'],
                'sell_count': buy_sell['sell_count'],

                # VWAP
                'vwap': vwap_data['vwap'],
                'current_price': vwap_data['current_price'],
                'price_vs_vwap': vwap_data['price_vs_vwap'],
                'total_volume': vwap_data['total_volume'],

                # 鲸鱼信号
                'whale_signal': whale_signal['signal'],
                'whale_buy_volume': whale_signal['whale_buy_volume'],
                'whale_sell_volume': whale_signal['whale_sell_volume'],
                'whale_ratio': whale_signal['whale_ratio'],

                # 交易者统计
                'unique_traders': trader_stats['unique_traders'],
                'total_trades': trader_stats['total_trades'],
                'avg_trade_size': trader_stats['avg_trade_size'],

                # 资金流
                'net_flow': net_flow['net_flow'],
                'flow_direction': net_flow['flow_direction'],
            }
        }