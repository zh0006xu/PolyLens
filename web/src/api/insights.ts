import { apiClient } from './client';

// Types
export interface HotMarket {
  id: number;
  slug: string;
  question: string | null;
  image: string | null;
  category: string | null;
  volume_24h: number;
  trade_count_24h: number;
  unique_traders_24h: number;
  price_change_24h: number | null;
  current_price: number | null;
}

export interface HotMarketsResponse {
  markets: HotMarket[];
  updated_at: string;
}

export interface VolumeAnomaly {
  market_id: number;
  slug: string;
  question: string | null;
  image: string | null;
  volume_24h: number;
  volume_avg_30d: number;
  volume_ratio: number;
  trade_count_24h: number;
  anomaly_type: string;
}

export interface VolumeAnomalyResponse {
  anomalies: VolumeAnomaly[];
  threshold: number;
  updated_at: string;
}

export interface SmartMoneyFlow {
  market_id: number;
  slug: string;
  question: string | null;
  image: string | null;
  whale_buy_volume: number;
  whale_sell_volume: number;
  whale_net_flow: number;
  whale_buy_count: number;
  whale_sell_count: number;
  flow_direction: 'inflow' | 'outflow' | 'neutral';
  signal_strength: 'strong' | 'moderate' | 'weak';
}

export interface SmartMoneyResponse {
  flows: SmartMoneyFlow[];
  total_net_flow: number;
  updated_at: string;
}

// API Functions
export async function fetchHotMarkets(limit = 10, category?: string): Promise<HotMarketsResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (category) params.append('category', category);
  const response = await apiClient.get<HotMarketsResponse>(`/insights/hot-markets?${params}`);
  return response.data;
}

export async function fetchVolumeAnomalies(threshold = 2.0, limit = 20): Promise<VolumeAnomalyResponse> {
  const params = new URLSearchParams({
    threshold: String(threshold),
    limit: String(limit),
  });
  const response = await apiClient.get<VolumeAnomalyResponse>(`/insights/volume-anomalies?${params}`);
  return response.data;
}

export async function fetchSmartMoney(limit = 20, hours = 24, minWhaleValue = 1000): Promise<SmartMoneyResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    hours: String(hours),
    min_whale_value: String(minWhaleValue),
  });
  const response = await apiClient.get<SmartMoneyResponse>(`/insights/smart-money?${params}`);
  return response.data;
}
