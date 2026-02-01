"""
数据库 Schema 定义
使用 SQLite 存储市场、交易和鲸鱼数据
"""

import sqlite3
from pathlib import Path


def init_db(db_path: str) -> sqlite3.Connection:
    """
    初始化数据库，创建表结构

    Args:
        db_path: 数据库文件路径

    Returns:
        sqlite3.Connection 实例
    """
    # 确保目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row  # 返回字典形式的行

    # 启用 WAL 模式以支持并发读写，提升性能
    # WAL 允许读取和写入同时进行，解决同步时网页响应慢的问题
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    cursor = conn.cursor()

    # =========================================================================
    # events 表 - 事件信息
    # =========================================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug VARCHAR NOT NULL UNIQUE,
            title VARCHAR,
            description TEXT,
            category VARCHAR,
            start_date VARCHAR,
            end_date VARCHAR,
            image VARCHAR,
            icon VARCHAR,
            status VARCHAR DEFAULT 'active',
            enable_neg_risk BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # =========================================================================
    # markets 表 - 市场信息 (扩展字段支持前端卡片展示)
    # =========================================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS markets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            slug VARCHAR NOT NULL,
            condition_id VARCHAR NOT NULL UNIQUE,
            question_id VARCHAR,
            oracle VARCHAR,
            collateral_token VARCHAR,
            yes_token_id VARCHAR,
            no_token_id VARCHAR,
            enable_neg_risk BOOLEAN DEFAULT 0,
            status VARCHAR DEFAULT 'active',
            question VARCHAR,
            description TEXT,
            outcomes VARCHAR,
            outcome_prices VARCHAR,
            end_date VARCHAR,

            -- 前端展示字段 (从 Gamma API 获取)
            image VARCHAR,
            icon VARCHAR,
            category VARCHAR,
            volume REAL DEFAULT 0,
            volume_24h REAL DEFAULT 0,
            liquidity REAL DEFAULT 0,
            best_bid REAL,
            best_ask REAL,
            trade_count INTEGER DEFAULT 0,

            sync_warning VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """
    )

    # 市场表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_slug ON markets(slug)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_yes_token ON markets(yes_token_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_no_token ON markets(no_token_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_event_id ON markets(event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_category ON markets(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_volume ON markets(volume DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_status ON markets(status)")

    # =========================================================================
    # trades 表 - 交易记录
    # =========================================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id INTEGER,
            tx_hash VARCHAR NOT NULL,
            log_index INTEGER NOT NULL,
            block_number INTEGER,
            maker VARCHAR,
            taker VARCHAR,
            side VARCHAR,
            outcome VARCHAR,
            price DECIMAL(18, 8),
            size DECIMAL(18, 8),
            fee DECIMAL(18, 8),
            token_id VARCHAR,
            timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (market_id) REFERENCES markets(id),
            UNIQUE (tx_hash, log_index)
        )
    """
    )

    # 交易表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_market_id ON trades(market_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_block ON trades(block_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_token_id ON trades(token_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_maker ON trades(maker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_taker ON trades(taker)")

    # =========================================================================
    # whale_trades 表 - 鲸鱼交易
    # =========================================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS whale_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_hash VARCHAR NOT NULL,
            log_index INTEGER NOT NULL,
            market_id INTEGER,
            trader VARCHAR,
            side VARCHAR,
            outcome VARCHAR,
            price REAL,
            size REAL,
            usd_value REAL,
            block_number INTEGER,
            timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (market_id) REFERENCES markets(id),
            UNIQUE(tx_hash, log_index)
        )
    """
    )

    # 鲸鱼表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whales_usd ON whale_trades(usd_value DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whales_market ON whale_trades(market_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whales_timestamp ON whale_trades(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whales_trader ON whale_trades(trader)")

    # =========================================================================
    # market_metrics 表 - 市场指标快照
    # =========================================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS market_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_id INTEGER NOT NULL,
            token_id VARCHAR,
            timestamp INTEGER NOT NULL,
            interval VARCHAR NOT NULL,

            -- 成交量指标
            buy_volume REAL DEFAULT 0,
            sell_volume REAL DEFAULT 0,
            buy_count INTEGER DEFAULT 0,
            sell_count INTEGER DEFAULT 0,

            -- 价格指标
            vwap REAL,
            price_high REAL,
            price_low REAL,
            price_open REAL,
            price_close REAL,

            -- 交易者指标
            unique_traders INTEGER DEFAULT 0,

            -- 鲸鱼指标
            whale_buy_volume REAL DEFAULT 0,
            whale_sell_volume REAL DEFAULT 0,
            whale_buy_count INTEGER DEFAULT 0,
            whale_sell_count INTEGER DEFAULT 0,

            -- 衍生指标
            buy_sell_ratio REAL,
            net_flow REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (market_id) REFERENCES markets(id),
            UNIQUE(market_id, token_id, interval, timestamp)
        )
    """
    )

    # 市场指标表索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_market ON market_metrics(market_id, interval)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON market_metrics(timestamp)")

    # =========================================================================
    # sync_state 表 - 同步状态
    # =========================================================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            key VARCHAR PRIMARY KEY,
            last_block INTEGER,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.commit()
    return conn


def migrate_db(db_path: str) -> None:
    """
    数据库迁移 - 添加新列到已有表

    Args:
        db_path: 数据库文件路径
    """
    conn = sqlite3.connect(db_path, timeout=30)
    cursor = conn.cursor()

    # 检查并添加 events 表的新列
    cursor.execute("PRAGMA table_info(events)")
    existing_events_columns = {row[1] for row in cursor.fetchall()}
    if "category" not in existing_events_columns:
        cursor.execute("ALTER TABLE events ADD COLUMN category VARCHAR")
        print("Added column: events.category")

    # 检查并添加 markets 表的新列
    new_columns = [
        ("image", "VARCHAR"),
        ("icon", "VARCHAR"),
        ("category", "VARCHAR"),
        ("volume", "REAL DEFAULT 0"),
        ("volume_24h", "REAL DEFAULT 0"),
        ("liquidity", "REAL DEFAULT 0"),
        ("best_bid", "REAL"),
        ("best_ask", "REAL"),
        ("trade_count", "INTEGER DEFAULT 0"),
    ]

    # 获取现有列
    cursor.execute("PRAGMA table_info(markets)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE markets ADD COLUMN {col_name} {col_type}")
                print(f"Added column: markets.{col_name}")
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not add column {col_name}: {e}")

    # 创建新索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_category ON markets(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_volume ON markets(volume DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_markets_status ON markets(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_maker ON trades(maker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_taker ON trades(taker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_whales_trader ON whale_trades(trader)")
    except sqlite3.OperationalError:
        pass

    # 删除 klines 表 (如果存在)
    try:
        cursor.execute("DROP TABLE IF EXISTS klines")
        print("Dropped table: klines (K-lines are now computed on-the-fly from trades)")
    except sqlite3.OperationalError:
        pass

    # 更新 trade_count 字段 (从 trades 表聚合)
    try:
        cursor.execute("""
            UPDATE markets
            SET trade_count = (
                SELECT COUNT(*) FROM trades WHERE trades.market_id = markets.id
            )
            WHERE EXISTS (SELECT 1 FROM trades WHERE trades.market_id = markets.id)
        """)
        updated = cursor.rowcount
        if updated > 0:
            print(f"Updated trade_count for {updated} markets")
    except sqlite3.OperationalError as e:
        print(f"Warning: Could not update trade_count: {e}")

    conn.commit()
    conn.close()


def reset_db(db_path: str) -> sqlite3.Connection:
    """
    重置数据库 (删除后重新创建)

    Args:
        db_path: 数据库文件路径

    Returns:
        sqlite3.Connection 实例
    """
    path = Path(db_path)
    if path.exists():
        try:
            path.unlink()
            print(f"Deleted existing database: {db_path}")
        except PermissionError:
            print(f"Warning: Cannot delete {db_path}. Truncating tables instead.")
            conn = sqlite3.connect(db_path, timeout=30)
            cursor = conn.cursor()
            for table in ['trades', 'markets', 'events', 'whale_trades', 'market_metrics', 'sync_state']:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
            conn.close()

    return init_db(db_path)
