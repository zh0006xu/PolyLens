"""
Dashboard module - K线聚合、鲸鱼检测等
"""

from .aggregator import KlineAggregator
from .whale_detector import WhaleDetector

__all__ = ["KlineAggregator", "WhaleDetector"]