"""
WebSocket 连接管理器 - 管理客户端连接和消息广播
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器 - 支持多频道订阅和消息广播"""

    def __init__(self):
        # 按频道分组的连接
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "whales": set(),  # 鲸鱼警报频道
            "trades": set(),  # 实时交易频道
        }
        self._lock = asyncio.Lock()
        self._message_count = 0

    async def connect(self, websocket: WebSocket, channel: str = "whales"):
        """
        接受连接并加入频道

        Args:
            websocket: WebSocket 连接
            channel: 频道名称 (whales, trades)
        """
        await websocket.accept()

        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)

        logger.info(
            f"Client connected to channel '{channel}', "
            f"total connections: {self.connection_count}"
        )

        # 发送欢迎消息
        await websocket.send_json(
            {
                "type": "connected",
                "channel": channel,
                "message": f"Connected to {channel} channel",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    async def disconnect(self, websocket: WebSocket, channel: str = "whales"):
        """断开连接"""
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)

        logger.info(
            f"Client disconnected from channel '{channel}', "
            f"total connections: {self.connection_count}"
        )

    async def broadcast(self, channel: str, message: dict):
        """
        向频道广播消息

        Args:
            channel: 频道名称
            message: 消息内容
        """
        if channel not in self.active_connections:
            return

        self._message_count += 1
        dead_connections = set()

        # 添加时间戳
        message["_broadcast_id"] = self._message_count
        message["_broadcast_time"] = datetime.utcnow().isoformat() + "Z"

        data = json.dumps(message, default=str)

        for connection in self.active_connections[channel].copy():
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                dead_connections.add(connection)

        # 清理断开的连接
        if dead_connections:
            async with self._lock:
                for conn in dead_connections:
                    self.active_connections[channel].discard(conn)

    async def broadcast_whale_alert(self, whale_data: dict):
        """
        广播鲸鱼警报

        Args:
            whale_data: 鲸鱼交易数据
        """
        await self.broadcast(
            "whales",
            {
                "type": "whale_alert",
                "data": {
                    "tx_hash": whale_data.get("tx_hash"),
                    "market_slug": whale_data.get("market_slug"),
                    "question": whale_data.get("question"),
                    "side": whale_data.get("side"),
                    "outcome": whale_data.get("outcome"),
                    "price": whale_data.get("price"),
                    "size": whale_data.get("size"),
                    "usd_value": whale_data.get("usd_value"),
                    "trader": whale_data.get("trader"),
                    "timestamp": whale_data.get("timestamp"),
                },
            },
        )

    async def broadcast_trade(self, trade_data: dict):
        """
        广播新交易

        Args:
            trade_data: 交易数据
        """
        await self.broadcast(
            "trades",
            {
                "type": "new_trade",
                "data": trade_data,
            },
        )

    @property
    def connection_count(self) -> Dict[str, int]:
        """获取各频道连接数"""
        return {ch: len(conns) for ch, conns in self.active_connections.items()}

    @property
    def total_connections(self) -> int:
        """获取总连接数"""
        return sum(len(conns) for conns in self.active_connections.values())

    @property
    def status(self) -> dict:
        """获取管理器状态"""
        return {
            "channels": list(self.active_connections.keys()),
            "connections": self.connection_count,
            "total_connections": self.total_connections,
            "messages_sent": self._message_count,
        }


# 全局单例
ws_manager = ConnectionManager()
