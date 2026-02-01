"""
Conditional Tokens Framework (CTF) 工具函数
用于计算 conditionId, collectionId, positionId (tokenId)
"""

from typing import Optional, Dict
from eth_abi import encode
from eth_utils import keccak

from ..config import USDC_E, WRAPPED_COLLATERAL


# ============================================================================
# alt-bn128 椭圆曲线参数
# ============================================================================

ALT_BN128_P = 21888242871839275222246405745257275088696311157297823662689037894645226208583
ALT_BN128_B = 3
ODD_TOGGLE = 1 << 254


# ============================================================================
# 椭圆曲线计算 (用于 NegRisk 市场)
# ============================================================================

def _mod_sqrt(a: int, p: int) -> Optional[int]:
    """计算模平方根 (Tonelli-Shanks 算法简化版)"""
    if a == 0:
        return 0
    if pow(a, (p - 1) // 2, p) != 1:
        return None
    return pow(a, (p + 1) // 4, p)


def calculate_collection_ids_ec(condition_id: str, outcome_slot_count: int = 2) -> list:
    """使用椭圆曲线计算 collection IDs"""
    collection_ids = []
    condition_bytes = bytes.fromhex(condition_id[2:] if condition_id.startswith("0x") else condition_id)

    for i in range(1, outcome_slot_count + 1):
        encoded = encode(["bytes32", "uint256"], [condition_bytes, i])
        init_hash = keccak(encoded)

        odd = init_hash[0] >= 0x80
        x = int.from_bytes(init_hash, "big") % ALT_BN128_P

        while True:
            x = (x + 1) % ALT_BN128_P
            yy = (pow(x, 3, ALT_BN128_P) + ALT_BN128_B) % ALT_BN128_P
            y = _mod_sqrt(yy, ALT_BN128_P)
            if y is not None and (y * y) % ALT_BN128_P == yy:
                break

        ec_hash = x
        if odd:
            ec_hash ^= ODD_TOGGLE

        collection_ids.append("0x" + ec_hash.to_bytes(32, "big").hex())

    return collection_ids


def calculate_position_ids_ec(condition_id: str, collateral_token: str, outcome_slot_count: int = 2) -> list:
    """使用椭圆曲线方式计算 position IDs"""
    collection_ids = calculate_collection_ids_ec(condition_id, outcome_slot_count)
    position_ids = []

    collateral_addr = bytes.fromhex(collateral_token[2:] if collateral_token.startswith("0x") else collateral_token)

    for collection_id in collection_ids:
        collection_bytes = bytes.fromhex(collection_id[2:])
        packed = collateral_addr + collection_bytes
        position_hash = keccak(packed)
        position_id = int.from_bytes(position_hash, "big")
        position_ids.append(str(position_id))

    return position_ids


# ============================================================================
# 统一接口
# ============================================================================

def calculate_token_ids(condition_id: str, is_neg_risk: bool = True) -> Dict[str, str]:
    """
    计算 YES/NO Token ID

    Args:
        condition_id: 条件 ID (bytes32 hex string)
        is_neg_risk: 是否为 NegRisk 市场

    Returns:
        dict with yesTokenId, noTokenId, collateralToken
    """
    collateral_token = WRAPPED_COLLATERAL if is_neg_risk else USDC_E
    position_ids = calculate_position_ids_ec(condition_id, collateral_token, 2)

    return {
        "yesTokenId": position_ids[0],
        "noTokenId": position_ids[1],
        "collateralToken": collateral_token
    }