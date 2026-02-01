import apiClient from './client';
import type { KlineResponse, KlineQueryParams } from '../types';

interface ApiKline {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trade_count: number;
}

interface ApiKlineResponse {
  market_id: number;
  interval: string;
  klines: ApiKline[];
}

export async function fetchKlines(params: KlineQueryParams): Promise<KlineResponse> {
  const response = await apiClient.get<ApiKlineResponse>('/klines', { params });

  // Transform API response to match frontend types (timestamp -> time)
  const klines = response.data.klines.map((k) => ({
    time: k.timestamp,
    open: k.open,
    high: k.high,
    low: k.low,
    close: k.close,
    volume: k.volume,
  }));

  return {
    klines,
    vwap: null, // API doesn't return vwap yet
  };
}
