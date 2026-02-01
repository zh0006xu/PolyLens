#!/usr/bin/env python3
"""
更新数据库中市场的 category 信息
从 Gamma API 获取 events 的 category/tags 并更新关联的 markets
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import DATABASE_PATH
from src.core.discovery import (
    update_categories_from_events,
    refresh_market_metadata,
)
from src.core.db.schema import migrate_db


def main():
    parser = argparse.ArgumentParser(
        description="Update market categories from Polymarket API"
    )
    parser.add_argument(
        "--db",
        default=DATABASE_PATH,
        help=f"Database path (default: {DATABASE_PATH})",
    )
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="Refresh all market metadata (volume, prices, category)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of markets to update (for testing)",
    )
    args = parser.parse_args()

    # 确保数据库 schema 是最新的
    print(f"Migrating database schema: {args.db}")
    migrate_db(args.db)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    try:
        if args.refresh_all:
            print("\n=== Refreshing all market metadata ===")
            result = refresh_market_metadata(conn, limit=args.limit)
            print(f"\nRefresh complete:")
            print(f"  Markets fetched: {result['markets_fetched']}")
            print(f"  Markets updated: {result['markets_updated']}")
        else:
            print("\n=== Updating categories from events ===")
            result = update_categories_from_events(conn)
            print(f"\nUpdate complete:")
            print(f"  Events fetched: {result['events_fetched']}")
            print(f"  Markets updated: {result['markets_updated']}")
            print(f"  Categories found: {len(result['categories_found'])}")

            # 显示分类分布
            if result['categories_found']:
                print("\nTop categories:")
                sorted_cats = sorted(
                    result['categories_found'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                for cat, count in sorted_cats:
                    print(f"    {cat}: {count}")

        # 显示更新后的统计
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(category) as with_category,
                COUNT(*) - COUNT(category) as without_category
            FROM markets
        """)
        stats = cursor.fetchone()
        print(f"\nDatabase stats:")
        print(f"  Total markets: {stats['total']}")
        print(f"  With category: {stats['with_category']}")
        print(f"  Without category: {stats['without_category']}")

        # 显示分类分布
        cursor.execute("""
            SELECT category, COUNT(*) as cnt
            FROM markets
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY cnt DESC
            LIMIT 15
        """)
        rows = cursor.fetchall()
        if rows:
            print("\nCategory distribution in database:")
            for row in rows:
                print(f"    {row['category']}: {row['cnt']}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()