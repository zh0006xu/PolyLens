"""
Streamlit 前端应用 - Polymarket 市场情绪仪表盘
支持自动刷新、实时指标展示和可视化
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import json

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

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


def format_ratio(ratio: float) -> str:
    """格式化比率"""
    if ratio is None:
        return "N/A"
    return f"{ratio:.2f}"


def get_signal_color(signal: str) -> str:
    """获取信号颜色"""
    colors = {
        'bullish': '#00C853',  # 绿色
        'bearish': '#FF1744',  # 红色
        'neutral': '#9E9E9E',  # 灰色
    }
    return colors.get(signal, '#9E9E9E')


def get_signal_emoji(signal: str) -> str:
    """获取信号 emoji"""
    emojis = {
        'bullish': '🟢',
        'bearish': '🔴',
        'neutral': '⚪',
    }
    return emojis.get(signal, '⚪')


def render_metric_card(title: str, value: str, subtitle: str = None, delta: str = None, delta_color: str = None):
    """渲染指标卡片"""
    st.metric(label=title, value=value, delta=delta)
    if subtitle:
        st.caption(subtitle)


def main():
    st.set_page_config(
        page_title="Polymarket 情绪仪表盘",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 Polymarket 市场情绪仪表盘")
    st.markdown("*实时追踪预测市场数据、鲸鱼交易和市场趋势*")

    # 检查 API 连接
    stats = fetch_api("/stats")
    if not stats:
        st.error("无法连接到 API 服务器。请确保 API 服务已启动: `python -m src.main serve`")
        st.stop()

    # 自动刷新设置（在侧边栏底部显示）
    auto_refresh = False
    refresh_interval = 30

    # 获取调度器状态
    scheduler_status = fetch_api("/scheduler/status")
    if scheduler_status and scheduler_status.get("enabled"):
        sync_count = scheduler_status.get("sync_count", 0)
        is_syncing = scheduler_status.get("is_syncing", False)
        status_text = "🔄 同步中..." if is_syncing else "✅ 后台同步已启用"
        st.caption(f"{status_text} | 已同步 {sync_count} 次 | 间隔 {scheduler_status.get('interval_seconds', 30)}秒")

    # 顶部统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("市场数量", f"{stats.get('markets_count', 0):,}")
    with col2:
        st.metric("交易记录", f"{stats.get('trades_count', 0):,}")
    with col3:
        st.metric("K线数据", f"{stats.get('klines_count', 0):,}")
    with col4:
        st.metric("鲸鱼交易", f"{stats.get('whale_trades_count', 0):,}")

    st.divider()

    # 侧边栏 - 市场选择和设置
    with st.sidebar:
        st.header("🔍 市场选择")

        # 获取市场列表
        markets_data = fetch_api("/markets", {"limit": 50})

        if markets_data and markets_data.get("markets"):
            markets = markets_data["markets"]
            market_options = {
                f"{m['question'][:50]}..." if m['question'] and len(m['question']) > 50
                else (m['question'] or m['slug']): m['id']
                for m in markets
            }

            if market_options:
                options_list = list(market_options.keys())
                
                # 尝试保持之前的选择
                current_index = 0
                # 如果 session_state 中有记录，且该记录仍在新的选项列表中，则恢复该选择
                if "selected_market_name" in st.session_state:
                    if st.session_state.selected_market_name in options_list:
                        current_index = options_list.index(st.session_state.selected_market_name)

                selected_name = st.selectbox(
                    "选择市场",
                    options_list,
                    index=current_index,
                    key="market_selector" 
                )
                
                # 更新 session_state
                st.session_state.selected_market_name = selected_name
                
                selected_market_id = market_options[selected_name]

                # 显示市场状态
                selected_market_obj = next((m for m in markets if m['id'] == selected_market_id), None)
                if selected_market_obj:
                    status = selected_market_obj.get("status", "active")
                    st.divider()
                    if status == "closed" or status == "finalized":
                        st.error(f"🔴 已结束 ({status})")
                        
                        # 解析赢家
                        try:
                            prices_str = selected_market_obj.get("outcome_prices")
                            outcomes_str = selected_market_obj.get("outcomes")
                            
                            if prices_str and outcomes_str:
                                prices = json.loads(prices_str) if isinstance(prices_str, str) else prices_str
                                outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
                                
                                if isinstance(prices, list) and isinstance(outcomes, list) and len(prices) == len(outcomes):
                                    winner_idx = -1
                                    for i, p in enumerate(prices):
                                        if float(p) >= 0.99:
                                            winner_idx = i
                                            break
                                    
                                    if winner_idx >= 0:
                                        st.success(f"🏆 赢家: {outcomes[winner_idx]}")
                        except Exception:
                            pass
                    else:
                        st.success(f"🟢 交易中 ({status})")

            else:
                st.warning("暂无市场数据")
                selected_market_id = None
        else:
            st.warning("暂无市场数据，请先索引数据")
            selected_market_id = None

        st.divider()

        # 指标周期选择
        st.header("📊 指标设置")
        metrics_period = st.selectbox(
            "统计周期",
            ["1h", "4h", "24h", "7d", "30d"],
            index=2,  # 默认 24h
            format_func=lambda x: {
                "1h": "1 小时",
                "4h": "4 小时",
                "24h": "24 小时",
                "7d": "7 天",
                "30d": "30 天",
            }.get(x, x)
        )

        st.divider()

        # K 线间隔选择
        st.header("📈 K 线设置")
        interval = st.selectbox(
            "时间间隔",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=2,  # 默认 15m
        )

        kline_limit = st.slider("显示数量", 20, 200, 100)

        st.divider()

        # 鲸鱼阈值设置
        st.header("🐋 鲸鱼设置")
        whale_threshold = st.number_input(
            "最小金额 (USD)",
            min_value=100,
            max_value=100000,
            value=1000,
            step=100,
        )

        st.divider()

        # 自动刷新设置
        st.header("🔄 自动刷新")
        auto_refresh = st.checkbox("启用自动刷新", value=False, key="auto_refresh_toggle")
        refresh_interval = st.selectbox(
            "刷新间隔",
            [15, 30, 60, 120],
            index=1,
            format_func=lambda x: f"{x} 秒",
            disabled=not auto_refresh,
            key="refresh_interval_select",
        )

        if auto_refresh and HAS_AUTOREFRESH:
            st_autorefresh(interval=refresh_interval * 1000, limit=None, key="data_refresh")
        elif auto_refresh and not HAS_AUTOREFRESH:
            st.warning("请安装: `pip install streamlit-autorefresh`")

    # 主内容区域
    if selected_market_id:
        # 获取市场详情
        base_market_info = fetch_api(f"/markets/{selected_market_id}")

        if base_market_info:
            st.subheader(f"📌 {base_market_info.get('question', base_market_info.get('slug'))}")

            # 解析 Outcomes
            outcomes_json = base_market_info.get("outcomes")
            outcome_names = ["YES", "NO"]
            try:
                if outcomes_json:
                    if isinstance(outcomes_json, str):
                        outcome_names = json.loads(outcomes_json)
                    elif isinstance(outcomes_json, list):
                        outcome_names = outcomes_json
            except Exception:
                pass

            # Outcome 选择器
            selected_outcome_idx = st.radio(
                "选择结果:",
                range(len(outcome_names)),
                index=0,
                horizontal=True,
                format_func=lambda i: outcome_names[i],
                key="outcome_selector_main"
            )
            selected_outcome_name = outcome_names[selected_outcome_idx]

            # 确定 Token ID
            if selected_outcome_idx == 0:
                selected_token_id = base_market_info.get("yes_token_id")
            else:
                selected_token_id = base_market_info.get("no_token_id")

            # ============================================================
            # 核心指标卡片区域 (P0 可视化)
            # ============================================================
            st.divider()
            st.subheader(f"📊 {selected_outcome_name} 市场指标 ({metrics_period})")

            # 获取指标数据
            metrics_data = fetch_api(f"/metrics/{selected_market_id}", {
                "token_id": selected_token_id,
                "period": metrics_period,
            })

            if metrics_data and metrics_data.get("metrics"):
                m = metrics_data["metrics"]

                # 第一行: 核心指标
                col1, col2, col3 = st.columns(3)

                with col1:
                    # 24h 交易量
                    volume = m.get('total_volume', 0)
                    st.metric(
                        "交易量",
                        format_usd(volume),
                        delta=f"{m.get('total_trades', 0)} 笔交易",
                        help="计算方式：所选周期内所有交易的成交金额总和。\n\n用户价值：反映市场的活跃程度和流动性。交易量激增通常伴随着重要新闻或价格突破。"
                    )

                with col2:
                    # 买卖压力比
                    buy_pct = m.get('buy_percentage', 50)
                    ratio = m.get('buy_sell_ratio')
                    ratio_str = format_ratio(ratio) if ratio else "N/A"

                    # 判断多空
                    if buy_pct > 55:
                        pressure_label = "▲ 多方主导"
                        pressure_color = "normal"
                    elif buy_pct < 45:
                        pressure_label = "▼ 空方主导"
                        pressure_color = "inverse"
                    else:
                        pressure_label = "◆ 势均力敌"
                        pressure_color = "off"

                    st.metric(
                        "买入占比",
                        f"{buy_pct:.1f}%",
                        delta=pressure_label,
                        delta_color=pressure_color,
                        help="计算方式：买入金额 / 总交易金额 * 100%。\n\n用户价值：衡量市场情绪的多空倾向。高于 55% 通常被视为看涨信号，低于 45% 视为看跌。"
                    )
                    st.caption(f"买卖比: {ratio_str}")

                    # 进度条展示买卖比
                    st.progress(min(buy_pct / 100, 1.0))

                with col3:
                    # 鲸鱼信号
                    signal = m.get('whale_signal', 'neutral')
                    whale_buy = m.get('whale_buy_volume', 0)
                    whale_sell = m.get('whale_sell_volume', 0)

                    signal_emoji = get_signal_emoji(signal)
                    signal_label = {
                        'bullish': 'Bullish',
                        'bearish': 'Bearish',
                        'neutral': 'Neutral'
                    }.get(signal, 'Neutral')

                    st.metric(
                        "鲸鱼信号",
                        f"{signal_emoji} {signal_label}",
                        delta=f"买 {format_usd(whale_buy)} / 卖 {format_usd(whale_sell)}",
                        help="计算方式：基于大额交易（鲸鱼）的净买入方向判断。\n\n用户价值：Smart Money（聪明钱）的动向。鲸鱼通常拥有更灵通的信息，跟随鲸鱼操作胜率更高。"
                    )

                # 第二行: 价格指标
                col4, col5, col6 = st.columns(3)

                with col4:
                    # VWAP
                    vwap = m.get('vwap')
                    current = m.get('current_price')
                    vs_vwap = m.get('price_vs_vwap')

                    if vwap:
                        st.metric(
                            "VWAP (量价均价)",
                            f"${vwap:.4f}",
                            delta=f"当前: ${current:.4f}" if current else None,
                            help="计算方式：成交量加权平均价格 (Volume Weighted Average Price)。\n\n用户价值：机构交易者公认的'公平价格'。当现价高于 VWAP 时，市场处于强势趋势。"
                        )
                        if vs_vwap:
                            if vs_vwap > 0:
                                st.caption(f"高于 VWAP {vs_vwap:.2f}%")
                            else:
                                st.caption(f"低于 VWAP {abs(vs_vwap):.2f}%")
                    else:
                        st.metric("VWAP (量价均价)", "N/A")

                with col5:
                    # 交易者数量
                    traders = m.get('unique_traders', 0)
                    avg_size = m.get('avg_trade_size', 0)
                    st.metric(
                        "活跃交易者",
                        f"{traders}",
                        delta=f"平均单笔 {format_usd(avg_size)}",
                        help="计算方式：周期内参与交易的独立钱包地址数量。\n\n用户价值：衡量市场的广度。价格上涨伴随活跃人数增加，说明趋势健康可靠。"
                    )

                with col6:
                    # 净资金流
                    net_flow = m.get('net_flow', 0)
                    direction = m.get('flow_direction', 'neutral')

                    if direction == 'inflow':
                        flow_emoji = "📈"
                        flow_label = "净流入"
                    elif direction == 'outflow':
                        flow_emoji = "📉"
                        flow_label = "净流出"
                    else:
                        flow_emoji = "➡️"
                        flow_label = "平衡"

                    st.metric(
                        "资金流向",
                        f"{flow_emoji} {format_usd(abs(net_flow))}",
                        delta=flow_label,
                        help="计算方式：买入总金额 - 卖出总金额。\n\n用户价值：直观展示资金是在流入还是逃离该市场。持续净流入往往是价格上涨的前兆。"
                    )

            else:
                st.info("暂无指标数据")

            # ============================================================
            # K 线图 (带 VWAP 和成交量)
            # ============================================================
            st.divider()
            st.subheader(f"📈 {selected_outcome_name} 价格走势")

            klines_data = fetch_api("/klines", {
                "market_id": selected_market_id,
                "interval": interval,
                "limit": kline_limit,
                "token_id": selected_token_id
            })

            if klines_data and klines_data.get("klines"):
                klines = klines_data["klines"]
                df = pd.DataFrame(klines)
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

                # 创建带子图的图表 (K 线 + 成交量)
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    row_heights=[0.7, 0.3],
                    subplot_titles=(f'{selected_outcome_name} 价格', '成交量')
                )

                # K 线图
                fig.add_trace(
                    go.Candlestick(
                        x=df['datetime'],
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="价格",
                    ),
                    row=1, col=1
                )

                # 添加 VWAP 参考线 (如果有)
                if metrics_data and metrics_data.get("metrics"):
                    vwap = metrics_data["metrics"].get('vwap')
                    if vwap:
                        fig.add_hline(
                            y=vwap,
                            line_dash="dash",
                            line_color="orange",
                            annotation_text=f"VWAP: {vwap:.4f}",
                            annotation_position="right",
                            row=1, col=1
                        )

                # 成交量柱状图
                colors = ['#26A69A' if df['close'].iloc[i] >= df['open'].iloc[i] else '#EF5350'
                          for i in range(len(df))]

                fig.add_trace(
                    go.Bar(
                        x=df['datetime'],
                        y=df['volume'],
                        marker_color=colors,
                        name="成交量",
                        showlegend=False,
                    ),
                    row=2, col=1
                )

                fig.update_layout(
                    height=500,
                    margin=dict(l=20, r=20, t=40, b=20),
                    xaxis_rangeslider_visible=False,
                    showlegend=False,
                )

                fig.update_xaxes(title_text="时间", row=2, col=1)
                fig.update_yaxes(title_text="价格", row=1, col=1)
                fig.update_yaxes(title_text="成交量", row=2, col=1)

                st.plotly_chart(fig, use_container_width=True)

                # 显示 K 线统计信息
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                with m_col1:
                    st.metric("区间最高", f"{df['high'].max():.4f}", help="当前可见 K 线范围内的最高价格")
                with m_col2:
                    st.metric("区间最低", f"{df['low'].min():.4f}", help="当前可见 K 线范围内的最低价格")
                with m_col3:
                    st.metric("区间成交量", format_usd(df['volume'].sum()), help="当前可见 K 线范围内的总成交量")
                with m_col4:
                    latest_close = df['close'].iloc[-1]
                    st.metric("最新收盘", f"{latest_close:.4f}", help="最新一根 K 线的收盘价")
            else:
                st.info(f"暂无 {selected_outcome_name} 的 K 线数据")

    # ============================================================
    # 鲸鱼交易区域 (当前市场)
    # ============================================================
    st.divider()
    st.subheader("🐋 当前市场鲸鱼交易")
    st.caption("显示该市场的大额交易。查看全市场数据请访问左侧 'Global Whales' 页面。")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 鲸鱼交易列表 (按市场过滤)
        whales_data = fetch_api("/whales", {
            "limit": 20,
            "min_usd": whale_threshold,
            "market_id": selected_market_id,  # Filter by market
        })

        if whales_data and whales_data.get("whales"):
            whales = whales_data["whales"]
            whale_df = pd.DataFrame(whales)

            # 将 YES/NO 映射为实际的选项名称
            if "outcome" in whale_df.columns:
                def map_outcome(val):
                    if val == "YES":
                        return outcome_names[0] if len(outcome_names) > 0 else "YES"
                    elif val == "NO":
                        return outcome_names[1] if len(outcome_names) > 1 else "NO"
                    return val
                
                whale_df["outcome"] = whale_df["outcome"].apply(map_outcome)

            # 选择显示的列 (移除 market_slug 因为都是同一个市场)
            display_cols = ["side", "outcome", "usd_value", "price", "size", "timestamp"]
            available_cols = [c for c in display_cols if c in whale_df.columns]

            if available_cols:
                display_df = whale_df[available_cols].copy()

                # 格式化
                if "usd_value" in display_df.columns:
                    display_df["usd_value"] = display_df["usd_value"].apply(
                        lambda x: format_usd(x) if x else "N/A"
                    )
                if "price" in display_df.columns:
                    display_df["price"] = display_df["price"].apply(
                        lambda x: f"{x:.4f}" if x else "N/A"
                    )

                # 重命名列
                display_df = display_df.rename(columns={
                    "side": "方向",
                    "outcome": "结果",
                    "usd_value": "金额",
                    "price": "价格",
                    "size": "数量",
                    "timestamp": "时间",
                })

                st.dataframe(display_df, use_container_width=True, height=400)
            else:
                st.dataframe(whale_df, use_container_width=True, height=400)
        else:
            st.info("该市场暂无鲸鱼交易数据")

    with col2:
        # 鲸鱼统计 (按市场过滤)
        whale_stats = fetch_api("/whales/stats", params={
            "min_usd": whale_threshold,
            "market_id": selected_market_id, # Filter by market
        })

        if whale_stats:
            st.metric("该市场鲸鱼交易数", f"{whale_stats.get('total_count', 0):,}", help="当前市场检测到的鲸鱼交易总笔数")
            st.metric("总交易额", format_usd(whale_stats.get('total_volume', 0)), help="当前市场鲸鱼交易总金额")
            st.metric("平均金额", format_usd(whale_stats.get('avg_value', 0)), help="当前市场平均单笔鲸鱼金额")
            st.metric("最大单笔", format_usd(whale_stats.get('max_value', 0)), help="当前市场最大一笔交易")

    # 页脚
    st.divider()
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(
        f"""
        <div style="text-align: center; color: gray; font-size: 12px;">
        Polymarket Sentiment Dashboard | 数据来源: Polygon 链上交易<br>
        最后更新: {update_time} | {'自动刷新已启用' if auto_refresh else '手动刷新'}
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()