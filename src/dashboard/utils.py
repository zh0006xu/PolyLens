
import requests
import streamlit as st

# API 配置
API_BASE = "http://localhost:8000/api"

def fetch_api(endpoint: str, params: dict = None):
    """调用 API"""
    try:
        url = f"{API_BASE}{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        return None

def format_usd(value: float) -> str:
    """格式化 USD 金额"""
    if value is None:
        return "N/A"
    if abs(value) >= 1000000:
        return f"${value/1000000:.2f}M"
    elif abs(value) >= 1000:
        return f"${value/1000:.2f}K"
    else:
        return f"${value:.2f}"
