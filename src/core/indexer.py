"""
Trades Indexer - 交易索引器
扫描链上 OrderFilled 事件，解析并存储到数据库
"""

import sqlite3
import sys
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from web3 import Web3

from ..config import get_web3, CTF_EXCHANGE, NEG_RISK_CTF_EXCHANGE
from .db.store import (
    insert_trade,
    fetch_market_by_token_id,
    get_sync_state,
    set_sync_state,
)
from .discovery import discover_market_by_token_id


# Exchange 合约地址 (小写)
EXCHANGE_ADDRESSES = [
    CTF_EXCHANGE.lower(),
    NEG_RISK_CTF_EXCHANGE.lower(),
]

# OrderFilled 事件签名
# OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)
ORDER_FILLED_SIGNATURE = (
    "OrderFilled(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)"
)

DEFAULT_BATCH_SIZE = 1000
MAX_RETRIES = 3
RETRY_DELAY = 2


def get_order_filled_topic(w3: Web3) -> str:
    """获取 OrderFilled 事件的 topic"""
    topic_hash = w3.keccak(text=ORDER_FILLED_SIGNATURE).hex()
    if not topic_hash.startswith("0x"):
        topic_hash = "0x" + topic_hash
    return topic_hash


def fetch_logs_with_retry(
    w3: Web3,
    from_block: int,
    to_block: int,
    addresses: List[str],
    topics: List[str],
    max_retries: int = MAX_RETRIES,
) -> List[Dict]:
    """带重试的日志获取"""
    checksum_addresses = [Web3.to_checksum_address(addr) for addr in addresses]

    for attempt in range(max_retries):
        try:
            logs = w3.eth.get_logs(
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "address": checksum_addresses,
                    "topics": topics,
                }
            )
            return logs
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise


def get_block_timestamp(w3: Web3, block_number: int, cache: Dict[int, int]) -> int:
    """获取区块时间戳 (带缓存)"""
    if block_number not in cache:
        block = w3.eth.get_block(block_number)
        cache[block_number] = block["timestamp"]
    return cache[block_number]


def decode_order_filled_log(log: Dict, w3: Web3) -> Dict[str, Any]:
    """解码 OrderFilled 事件日志"""
    topics = [t.hex() if isinstance(t, bytes) else t for t in log["topics"]]
    data = log["data"].hex() if isinstance(log["data"], bytes) else log["data"]

    order_hash = topics[1]
    maker = "0x" + topics[2][-40:]
    taker = "0x" + topics[3][-40:]

    if data.startswith("0x"):
        data = data[2:]
    data_bytes = bytes.fromhex(data)
    maker_asset_id = int.from_bytes(data_bytes[0:32], "big")
    taker_asset_id = int.from_bytes(data_bytes[32:64], "big")
    maker_amount_filled = int.from_bytes(data_bytes[64:96], "big")
    taker_amount_filled = int.from_bytes(data_bytes[96:128], "big")
    fee = int.from_bytes(data_bytes[128:160], "big")

    return {
        "tx_hash": (
            log["transactionHash"].hex()
            if isinstance(log["transactionHash"], bytes)
            else log["transactionHash"]
        ),
        "log_index": log["logIndex"],
        "block_number": log["blockNumber"],
        "exchange": log["address"],
        "order_hash": order_hash,
        "maker": maker,
        "taker": taker,
        "maker_asset_id": str(maker_asset_id),
        "taker_asset_id": str(taker_asset_id),
        "maker_amount_filled": maker_amount_filled,
        "taker_amount_filled": taker_amount_filled,
        "fee": fee,
    }


def determine_trade_details(decoded: Dict[str, Any]) -> Tuple[str, str, float, float]:
    """确定交易方向、价格和数量"""
    maker_asset_id = int(decoded["maker_asset_id"])
    taker_asset_id = int(decoded["taker_asset_id"])
    maker_amount = decoded["maker_amount_filled"]
    taker_amount = decoded["taker_amount_filled"]

    if maker_asset_id == 0:
        token_id = str(taker_asset_id)
        side = "BUY"
        usdc_amount = maker_amount
        token_amount = taker_amount
    else:
        token_id = str(maker_asset_id)
        side = "SELL"
        usdc_amount = taker_amount
        token_amount = maker_amount

    if token_amount > 0:
        price = usdc_amount / token_amount
    else:
        price = 0.0

    size = token_amount / 1e6

    return token_id, side, price, size


def process_trade(
    conn: sqlite3.Connection,
    decoded: Dict[str, Any],
    timestamp: int,
    discovered_token_ids: set = None,
) -> Dict[str, Any]:
    """处理单笔交易并存入数据库"""
    result = {
        "tx_hash": decoded["tx_hash"],
        "log_index": decoded["log_index"],
        "saved": False,
        "market_id": None,
        "outcome": None,
        "warning": None,
        "market_discovered": False,
    }

    token_id, side, price, size = determine_trade_details(decoded)

    market = fetch_market_by_token_id(conn, token_id)

    if not market:
        if discovered_token_ids is not None and token_id in discovered_token_ids:
            result["warning"] = f"Unknown token_id: {token_id[:20]}..."
            return result

        market = discover_market_by_token_id(conn, token_id)

        if discovered_token_ids is not None:
            discovered_token_ids.add(token_id)

        if market:
            result["market_discovered"] = True

    if not market:
        result["warning"] = f"Unknown token_id: {token_id[:20]}..."
        return result

    if market.get("yes_token_id") == token_id:
        outcome = "YES"
    elif market.get("no_token_id") == token_id:
        outcome = "NO"
    else:
        outcome = "UNKNOWN"

    timestamp_str = (
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    trade_data = {
        "market_id": market["id"],
        "tx_hash": decoded["tx_hash"],
        "log_index": decoded["log_index"],
        "block_number": decoded["block_number"],
        "maker": decoded["maker"],
        "taker": decoded["taker"],
        "side": side,
        "outcome": outcome,
        "price": price,
        "size": size,
        "fee": decoded["fee"] / 1e6,
        "token_id": token_id,
        "timestamp": timestamp_str,
    }

    trade_id = insert_trade(conn, trade_data)

    if trade_id:
        result["saved"] = True
        result["trade_id"] = trade_id

    result["market_id"] = market["id"]
    result["outcome"] = outcome
    result["side"] = side
    result["price"] = price
    result["size"] = size

    return result


def run_indexer(
    conn: sqlite3.Connection,
    from_block: int,
    to_block: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
    w3: Web3 = None,
    progress_callback=None,
    tx_hash: str = None,
) -> Dict[str, Any]:
    """运行交易索引器"""
    if w3 is None:
        w3 = get_web3()

    if tx_hash:
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash
        tx_hash = tx_hash.lower()

    order_filled_topic = get_order_filled_topic(w3)

    result = {
        "from_block": from_block,
        "to_block": to_block,
        "total_logs": 0,
        "inserted_trades": 0,
        "skipped_trades": 0,
        "unknown_tokens": 0,
        "discovered_markets": 0,
        "warnings": [],
        "sample_trades": [],
    }

    discovered_token_ids = set()
    block_timestamp_cache = {}

    current_block = from_block

    while current_block <= to_block:
        batch_end = min(current_block + batch_size - 1, to_block)

        if not progress_callback and not tx_hash:
            sys.stdout.write(
                f"\r  Scanning blocks {current_block} - {batch_end} (of {to_block})..."
            )
            sys.stdout.flush()

        try:
            logs = fetch_logs_with_retry(
                w3=w3,
                from_block=current_block,
                to_block=batch_end,
                addresses=EXCHANGE_ADDRESSES,
                topics=[order_filled_topic],
            )
        except Exception as e:
            result["warnings"].append(
                f"Failed to fetch logs {current_block}-{batch_end}: {e}"
            )
            current_block = batch_end + 1
            continue

        result["total_logs"] += len(logs)

        # 1. Group logs by block number
        logs_by_block = defaultdict(list)
        for log in logs:
            logs_by_block[log['blockNumber']].append(log)

        # 2. Iterate through EACH block in the range sequentially
        # This ensures we update sync_state even for empty blocks, strictly preserving progress.
        for block_num in range(current_block, batch_end + 1):
            block_logs = logs_by_block.get(block_num, [])

            for log in block_logs:
                if tx_hash:
                    log_tx = (
                        log["transactionHash"].hex()
                        if isinstance(log["transactionHash"], bytes)
                        else log["transactionHash"]
                    )
                    if not log_tx.startswith("0x"):
                        log_tx = "0x" + log_tx
                    if log_tx.lower() != tx_hash:
                        continue

                try:
                    decoded = decode_order_filled_log(log, w3)
                    timestamp = get_block_timestamp(
                        w3, decoded["block_number"], block_timestamp_cache
                    )
                    # Note: insert_trade no longer commits, so this is pending
                    trade_result = process_trade(
                        conn, decoded, timestamp, discovered_token_ids
                    )

                    if trade_result.get("market_discovered"):
                        result["discovered_markets"] += 1

                    if trade_result.get("saved"):
                        result["inserted_trades"] += 1

                        if len(result["sample_trades"]) < 1:
                            token_id, _, _, _ = determine_trade_details(decoded)
                            ts_str = datetime.fromtimestamp(
                                timestamp, tz=timezone.utc
                            ).strftime("%Y-%m-%dT%H:%M:%S")

                            result["sample_trades"].append(
                                {
                                    "tx_hash": trade_result["tx_hash"],
                                    "log_index": trade_result["log_index"],
                                    "block_number": decoded["block_number"],
                                    "timestamp": ts_str,
                                    "side": trade_result.get("side"),
                                    "outcome": trade_result.get("outcome"),
                                    "price": str(round(trade_result.get("price", 0), 4)),
                                    "size": str(round(trade_result.get("size", 0), 2)),
                                    "token_id": token_id,
                                }
                            )
                    elif trade_result.get("warning"):
                        if "Unknown token_id" in trade_result["warning"]:
                            result["unknown_tokens"] += 1
                        else:
                            result["warnings"].append(trade_result["warning"])
                    else:
                        result["skipped_trades"] += 1

                except Exception as e:
                    result["warnings"].append(f"Failed to process log: {e}")

            # 3. Checkpoint after EACH block
            # This commits both the trades for this block AND the sync_state
            set_sync_state(conn, "trade_sync", block_num)
        
        if progress_callback:
            progress_callback(current_block, batch_end, to_block)

        current_block = batch_end + 1

    print()
    return result


def sync_trades(
    conn: sqlite3.Connection,
    to_block: int = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    w3: Web3 = None,
) -> Dict[str, Any]:
    """增量同步交易 (从上次同步位置继续)"""
    if w3 is None:
        w3 = get_web3()

    last_block = get_sync_state(conn, "trade_sync")

    if last_block is None:
        raise ValueError(
            "No previous sync state found. Please specify from_block using run_indexer()"
        )

    from_block = last_block + 1

    if to_block is None:
        to_block = w3.eth.block_number

    if from_block > to_block:
        return {
            "from_block": from_block,
            "to_block": to_block,
            "message": "Already synced to latest block",
            "inserted_trades": 0,
        }

    print(f"Syncing trades from block {from_block} to {to_block}...")

    return run_indexer(
        conn=conn,
        from_block=from_block,
        to_block=to_block,
        batch_size=batch_size,
        w3=w3,
    )