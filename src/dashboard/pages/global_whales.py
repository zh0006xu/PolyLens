
import streamlit as st
import pandas as pd
import requests

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

st.set_page_config(
    page_title="全球鲸鱼监控 - Polymarket",
    page_icon="🐋",
    layout="wide",
)

st.title("🐋 全球鲸鱼监控")
st.markdown("*实时追踪全市场大额交易*")

# 侧边栏设置
with st.sidebar:
    st.header("设置")
    whale_threshold = st.number_input(
        "最小金额 (USD)",
        min_value=100,
        max_value=100000,
        value=1000,
        step=100,
    )
    
    limit = st.slider("显示数量", 20, 200, 50)

    if st.button("刷新数据"):
        st.rerun()

# 核心统计
st.subheader("全市场鲸鱼统计")
col1, col2, col3, col4 = st.columns(4)

stats = fetch_api("/whales/stats", {"min_usd": whale_threshold})

if stats:
    col1.metric("总鲸鱼交易数", f"{stats.get('total_count', 0):,}")
    col2.metric("总交易额", format_usd(stats.get('total_volume', 0)))
    col3.metric("平均单笔", format_usd(stats.get('avg_value', 0)))
    col4.metric("最大单笔", format_usd(stats.get('max_value', 0)))
else:
    st.warning("无法获取统计数据")

st.divider()

# 交易列表
st.subheader("实时鲸鱼交易")

whales_data = fetch_api("/whales", {
    "limit": limit,
    "min_usd": whale_threshold,
})

if whales_data and whales_data.get("whales"):
    whales = whales_data["whales"]
    df = pd.DataFrame(whales)

    # 选择显示的列
    display_cols = ["market_slug", "side", "outcome", "usd_value", "price", "size", "timestamp"]
    
    # 简单的列重命名映射
    column_config = {
        "market_slug": "市场",
        "side": "方向",
        "outcome": "结果",
        "usd_value": st.column_config.NumberColumn("金额 (USD)", format="$%.2f"),
        "price": st.column_config.NumberColumn("价格", format="%.4f"),
        "size": "数量",
        "timestamp": "时间",
    }

    st.dataframe(
        df[display_cols],
        use_container_width=True,
        column_config=column_config,
        height=600
    )
else:
    st.info("暂无数据")
