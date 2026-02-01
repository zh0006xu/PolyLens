import apiClient from './client';
import type { Market, MarketListResponse, MarketQueryParams, PriceResponse } from '../types';

export async function fetchMarkets(params: MarketQueryParams = {}): Promise<MarketListResponse> {
  const response = await apiClient.get<MarketListResponse>('/markets', { params });
  return response.data;
}

export async function fetchMarket(marketId: number, tokenId?: string): Promise<Market> {
  const params = tokenId ? { token_id: tokenId } : {};
  const response = await apiClient.get<Market>(`/markets/${marketId}`, { params });
  return response.data;
}

export async function fetchMarketPrice(marketId: number): Promise<PriceResponse> {
  const response = await apiClient.get<PriceResponse>(`/markets/${marketId}/price`);
  return response.data;
}
