import apiClient from './client';
import type { MarketHoldersResponse } from '../types';

export async function fetchMarketHolders(
  marketId: number,
  limit: number = 10
): Promise<MarketHoldersResponse> {
  const response = await apiClient.get<MarketHoldersResponse>(`/markets/${marketId}/holders`, {
    params: { limit, includeLevels: true },
  });
  return response.data;
}
