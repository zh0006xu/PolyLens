"""
配置管理 - 从 .env 文件加载环境变量
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3

# 加载 .env 文件 (从项目根目录)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


# ============================================================================
# RPC 配置
# ============================================================================

RPC_URL = os.getenv("RPC_URL", "https://rpc.ankr.com/polygon")


def get_web3() -> Web3:
    """获取 Web3 实例 (配置 POA 中间件用于 Polygon)"""
    from web3.middleware import ExtraDataToPOAMiddleware

    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={'timeout': 30}))
    # Polygon 是 POA 链，需要注入中间件处理 extraData 字段
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


# ============================================================================
# API 配置
# ============================================================================

GAMMA_API_BASE = os.getenv("GAMMA_API_BASE", "https://gamma-api.polymarket.com")


# ============================================================================
# 数据库配置
# ============================================================================

# 解析为绝对路径，避免因工作目录不同导致读写到不同文件
_db_path = os.getenv("DATABASE_PATH", "./data/dashboard.db")
if not os.path.isabs(_db_path):
    _db_path = str((Path(__file__).parent.parent / _db_path.lstrip("./")).resolve())
DATABASE_PATH = _db_path


# ============================================================================
# API 服务器配置
# ============================================================================

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))


# ============================================================================
# 鲸鱼检测配置
# ============================================================================

WHALE_THRESHOLD = float(os.getenv("WHALE_THRESHOLD", "1000"))


# ============================================================================
# 合约地址 (Polygon Mainnet)
# ============================================================================

# Conditional Tokens Framework
CONDITIONAL_TOKENS_ADDRESS = os.getenv(
    "CONDITIONAL_TOKENS_ADDRESS",
    "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
)

# 抵押品代币
USDC_E = os.getenv("USDC_E", "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174")
WRAPPED_COLLATERAL = os.getenv("WRAPPED_COLLATERAL", "0x3A3BD7bb9528E159577F7C2e685CC81A765002E2")

# NegRisk 合约
NEG_RISK_ADAPTER = os.getenv("NEG_RISK_ADAPTER", "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296")
NEG_RISK_CTF_EXCHANGE = os.getenv("NEG_RISK_CTF_EXCHANGE", "0xC5d563A36AE78145C45a50134d48A7D5220f80A4")

# CTF Exchange
CTF_EXCHANGE = os.getenv("CTF_EXCHANGE", "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E")