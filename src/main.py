"""
Polymarket Sentiment Dashboard CLI
Phase 2: 支持后台调度和实时推送
"""

import click
from pathlib import Path

from .config import DATABASE_PATH, API_HOST, API_PORT, WHALE_THRESHOLD

# 默认回溯区块数 (从当前区块往前)
DEFAULT_BLOCK_LOOKBACK = 100


@click.group()
@click.version_option(version="0.2.0")
def cli():
    """Polymarket Sentiment Dashboard - 市场情绪仪表盘 (Phase 2)"""
    pass


@cli.command()
@click.option(
    "--from-block",
    type=int,
    help="起始区块号 (默认: 当前区块 - DEFAULT_BLOCK_LOOKBACK 或断点续传)",
)
@click.option("--to-block", type=int, help="结束区块号 (默认: 最新区块)")
@click.option("--db", default=DATABASE_PATH, help="数据库文件路径")
@click.option("--batch-size", default=500, type=int, help="每批处理的区块数")
@click.option("--reset", is_flag=True, help="重置数据库后重新同步")
def index(from_block: int, to_block: int, db: str, batch_size: int, reset: bool):
    """索引链上交易数据并检测鲸鱼交易"""
    from tqdm import tqdm
    from .config import get_web3
    from .core.db.schema import init_db, reset_db
    from .core.db.store import get_sync_state
    from .core.indexer import run_indexer
    from .core.whale_detector import WhaleDetector

    # 确保数据目录存在
    Path(db).parent.mkdir(parents=True, exist_ok=True)

    # 重置或初始化数据库
    if reset:
        click.echo(f"Resetting database: {db}")
        conn = reset_db(db)
    else:
        click.echo(f"Initializing database: {db}")
        conn = init_db(db)

    # 获取最新区块
    w3 = get_web3()
    latest_block = w3.eth.block_number

    # 设置目标区块
    if to_block is None:
        to_block = latest_block
        click.echo(f"Targeting latest block: {to_block}")

    # 自动断点续传或使用默认起始区块
    if from_block is None:
        if reset:
            # 重置后从 (当前区块 - DEFAULT_BLOCK_LOOKBACK) 开始
            from_block = max(1, latest_block - DEFAULT_BLOCK_LOOKBACK)
            click.echo(
                f"Starting from block: {from_block} (latest - {DEFAULT_BLOCK_LOOKBACK})"
            )
        else:
            last_synced = get_sync_state(conn, "trade_sync")
            if last_synced:
                from_block = last_synced + 1
                click.echo(f"Resuming from sync state: block {from_block}")
            else:
                # 首次同步从 (当前区块 - DEFAULT_BLOCK_LOOKBACK) 开始
                from_block = max(1, latest_block - DEFAULT_BLOCK_LOOKBACK)
                click.echo(
                    f"First sync, starting from block: {from_block} (latest - {DEFAULT_BLOCK_LOOKBACK})"
                )

    if from_block > to_block:
        click.echo(
            f"Already synced up to {from_block - 1}. Target {to_block} is behind."
        )
        conn.close()
        return

    click.echo(f"Indexing trades from block {from_block} to {to_block}...")

    # 1. 索引交易 (带 tqdm 进度条)
    total_blocks = to_block - from_block + 1

    # 使用 tqdm 显示进度
    with tqdm(total=total_blocks, unit="blocks", desc="Indexing") as bar:
        last_processed = from_block - 1

        def progress_callback(current, batch_end, total):
            nonlocal last_processed
            # current 是当前批次的起始区块
            # 已经完成的区块是 current - 1
            processed_so_far = current - 1
            delta = processed_so_far - last_processed

            if delta > 0:
                bar.update(delta)
                last_processed = processed_so_far

        result = run_indexer(
            conn, from_block, to_block, batch_size, progress_callback=progress_callback
        )

        # 确保进度条走完
        delta = to_block - last_processed
        if delta > 0:
            bar.update(delta)

    click.echo(f"\nIndexing complete:")
    click.echo(f"  - Total logs scanned: {result['total_logs']}")
    click.echo(f"  - Trades inserted: {result['inserted_trades']}")
    click.echo(f"  - Markets discovered: {result['discovered_markets']}")

    # 2. 检测鲸鱼交易 (K 线从 trades 实时聚合，无需单独处理)
    click.echo("\nDetecting whale trades...")
    detector = WhaleDetector(db)
    whale_count = detector.detect_from_trades()
    click.echo(f"  - Whale trades detected: {whale_count}")

    conn.close()
    click.echo("\nDone!")


@cli.command()
@click.option("--event-slug", help="发现特定事件下的市场")
@click.option("--active-only", is_flag=True, default=True, help="仅发现活跃市场")
@click.option("--all", "fetch_all", is_flag=True, help="全量发现所有市场 (耗时较长)")
@click.option("--limit", type=int, help="发现市场的数量限制")
@click.option("--db", default=DATABASE_PATH, help="数据库文件路径")
def discover(event_slug: str, active_only: bool, fetch_all: bool, limit: int, db: str):
    """从 Gamma API 发现并更新市场元数据 (含分类信息)"""
    import sqlite3
    from .core.discovery import discover_markets_by_event_slug, discover_all_markets
    from .core.db.schema import init_db, migrate_db

    migrate_db(db)
    conn = init_db(db)

    if event_slug:
        click.echo(f"Discovering markets for event: {event_slug}")
        result = discover_markets_by_event_slug(conn, event_slug)
    else:
        click.echo(
            f"Discovering all markets (active_only={active_only}, fetch_all={fetch_all})"
        )
        result = discover_all_markets(
            conn, active_only=active_only, limit=limit, fetch_all=fetch_all
        )

    click.echo(f"\nDiscovery complete:")
    click.echo(f"  - Markets found: {result['markets_found']}")
    click.echo(f"  - Markets saved/updated: {result['markets_saved']}")

    if result.get("warnings"):
        click.echo(f"\nWarnings ({len(result['warnings'])}):")
        for warning in result["warnings"][:5]:
            click.echo(f"  - {warning}")

    conn.close()
    click.echo("\nDone!")


@cli.command()
@click.option("--host", default=API_HOST, help="API 服务器地址")
@click.option("--port", default=API_PORT, type=int, help="API 服务器端口")
@click.option("--db", default=DATABASE_PATH, help="数据库文件路径")
@click.option("--reload", is_flag=True, help="启用热重载 (开发模式)")
@click.option("--sync-interval", default=10, type=int, help="后台同步间隔 (秒)")
@click.option("--no-scheduler", is_flag=True, help="禁用后台同步调度器")
@click.option(
    "--whale-threshold", default=WHALE_THRESHOLD, type=float, help="鲸鱼交易阈值 (USD)"
)
def serve(
    host: str,
    port: int,
    db: str,
    reload: bool,
    sync_interval: int,
    no_scheduler: bool,
    whale_threshold: float,
):
    """启动 API 服务器 (含后台同步和 WebSocket)"""
    import uvicorn
    import os

    # 设置环境变量供 API 使用
    os.environ["DATABASE_PATH"] = db
    os.environ["SYNC_INTERVAL"] = str(sync_interval)
    os.environ["ENABLE_SCHEDULER"] = "0" if no_scheduler else "1"
    os.environ["WHALE_THRESHOLD"] = str(whale_threshold)

    click.echo(f"Starting API server on {host}:{port}")
    click.echo(f"Using database: {db}")
    click.echo(f"API docs: http://{host}:{port}/docs")

    if no_scheduler:
        click.echo("Background scheduler: DISABLED")
    else:
        click.echo(f"Background scheduler: every {sync_interval}s")
        click.echo(f"Whale threshold: ${whale_threshold:,.0f}")

    click.echo(f"WebSocket endpoints:")
    click.echo(f"  - ws://{host}:{port}/api/ws/whales")
    click.echo(f"  - ws://{host}:{port}/api/ws/trades")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
@click.option("--db", default=DATABASE_PATH, help="数据库文件路径")
def stats(db: str):
    """显示数据库统计信息"""
    import sqlite3

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # 获取各表的记录数
    tables = ["markets", "trades", "klines", "whale_trades"]

    click.echo(f"Database: {db}\n")
    click.echo("Table Statistics:")
    click.echo("-" * 40)

    for table in tables:
        try:
            count = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            click.echo(f"  {table}: {count:,} records")
        except sqlite3.OperationalError:
            click.echo(f"  {table}: (table not found)")

    # 显示最近的同步状态
    click.echo("\nSync State:")
    click.echo("-" * 40)
    try:
        cursor.execute("SELECT key, last_block, updated_at FROM sync_state")
        for row in cursor.fetchall():
            click.echo(f"  {row[0]}: block {row[1]} ({row[2]})")
    except sqlite3.OperationalError:
        click.echo("  (no sync state)")

    conn.close()


if __name__ == "__main__":
    cli()
