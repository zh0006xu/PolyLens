import apiClient from './client';
import type { Metrics } from '../types';

interface ApiMetricsResponse {
  market_id: number;
  token_id: string | null;
  period: string;
  metrics: {
    buy_sell_ratio: number;
    buy_percentage: number;
    buy_volume: number;
    sell_volume: number;
    buy_count: number;
    sell_count: number;
    vwap: number;
    current_price: number;
    price_vs_vwap: number;
    total_volume: number;
    whale_signal: string;
    whale_buy_volume: number;
    whale_sell_volume: number;
    whale_ratio: number;
    unique_traders: number;
    total_trades: number;
    avg_trade_size: number;
    net_flow: number;
    flow_direction: string;
  };
}

export async function fetchMetrics(
  marketId: number,
  period: string = '24h',
  tokenId?: string
): Promise<Metrics> {
  const params: Record<string, string> = { period };
  if (tokenId) {
    params.token_id = tokenId;
  }
  const response = await apiClient.get<ApiMetricsResponse>(`/metrics/${marketId}`, { params });
  const data = response.data;
  const m = data.metrics;

  // Transform API response to match frontend types
  return {
    market_id: data.market_id,
    token_id: data.token_id,
    period: data.period,
    buy_sell_ratio: {
      buy_volume: m.buy_volume,
      sell_volume: m.sell_volume,
      buy_count: m.buy_count,
      sell_count: m.sell_count,
      ratio: m.buy_sell_ratio,
      buy_percentage: m.buy_percentage,
    },
    vwap: {
      vwap: m.vwap,
      total_volume: m.total_volume,
      trade_count: m.total_trades,
    },
    whale_signal: {
      whale_buy_volume: m.whale_buy_volume,
      whale_sell_volume: m.whale_sell_volume,
      whale_buy_count: 0,
      whale_sell_count: 0,
      signal: m.whale_signal as 'bullish' | 'bearish' | 'neutral',
      signal_strength: m.whale_ratio,
    },
    trader_stats: {
      unique_traders: m.unique_traders,
      unique_buyers: 0,
      unique_sellers: 0,
      avg_trade_size: m.avg_trade_size,
    },
    net_flow: {
      net_flow: m.net_flow,
      inflow: m.net_flow > 0 ? m.net_flow : 0,
      outflow: m.net_flow < 0 ? Math.abs(m.net_flow) : 0,
    },
  };
}
