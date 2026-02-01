"""
API 依赖注入
"""

import sqlite3
from functools import lru_cache
from typing import Generator

from ..config import DATABASE_PATH


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """获取数据库连接 (依赖注入)"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@lru_cache()
def get_db_path() -> str:
    """获取数据库路径"""
    return DATABASE_PATH