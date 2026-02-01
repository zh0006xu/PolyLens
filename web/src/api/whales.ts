import apiClient from './client';
import type { WhaleListResponse, WhaleTrade } from '../types';

interface ApiWhaleListResponse {
  whales: WhaleTrade[];
  total: number;
}

export async function fetchWhales(
  marketId?: number,
  limit: number = 20,
  minUsd?: number
): Promise<WhaleListResponse> {
  const params: Record<string, string | number> = { limit };
  if (marketId) {
    params.market_id = marketId;
  }
  if (minUsd !== undefined) {
    params.min_usd = minUsd;
  }
  const response = await apiClient.get<ApiWhaleListResponse>('/whales', { params });
  // API returns 'whales' but frontend expects 'trades'
  return {
    trades: response.data.whales,
    total: response.data.total,
  };
}

export async function fetchRecentWhales(limit: number = 10): Promise<WhaleTrade[]> {
  const response = await apiClient.get<WhaleTrade[]>('/whales/recent', { params: { limit } });
  return response.data;
}
