"""
Categories API Routes
"""

import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryResponse(BaseModel):
    slug: str
    name: str
    count: int


class CategoryListResponse(BaseModel):
    categories: List[CategoryResponse]


@router.get("", response_model=CategoryListResponse)
def get_categories(
    conn: sqlite3.Connection = Depends(get_db),
):
    """获取分类列表及每个分类的市场数量"""
    cursor = conn.cursor()

    # Get categories with market counts, excluding NULL categories
    query = """
        SELECT
            category,
            COUNT(*) as count
        FROM markets
        WHERE category IS NOT NULL AND category != ''
        GROUP BY category
        ORDER BY count DESC
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    categories = []
    for row in rows:
        slug = row["category"]
        # Convert slug to display name (e.g., "sports" -> "Sports", "crypto" -> "Crypto")
        name = slug.replace("-", " ").replace("_", " ").title() if slug else "Other"
        categories.append(
            CategoryResponse(
                slug=slug,
                name=name,
                count=row["count"],
            )
        )

    return CategoryListResponse(categories=categories)
