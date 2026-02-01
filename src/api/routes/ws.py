"""
WebSocket 路由 - 实时数据推送端点
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..websocket.manager import ws_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/whales")
async def websocket_whales(websocket: WebSocket):
    """
    鲸鱼警报 WebSocket 端点

    连接后自动接收大额交易警报推送。
    支持心跳：发送 "ping" 返回 "pong"
    """
    await ws_manager.connect(websocket, "whales")
    try:
        while True:
            # 保持连接，接收客户端消息
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "status":
                await websocket.send_json(ws_manager.status)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "whales")


@router.websocket("/ws/trades")
async def websocket_trades(websocket: WebSocket):
    """
    实时交易 WebSocket 端点

    连接后自动接收新交易推送。
    支持心跳：发送 "ping" 返回 "pong"
    """
    await ws_manager.connect(websocket, "trades")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "status":
                await websocket.send_json(ws_manager.status)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, "trades")


@router.get("/ws/status")
async def websocket_status():
    """WebSocket 连接状态"""
    return ws_manager.status
