import apiClient from './client';
import type {
  TraderSummary,
  TraderTradeListResponse,
  TraderPositionsResponse,
  TraderProfileStats,
  TraderLeaderboardResponse,
  TraderValueResponse,
  TradeQueryParams,
  PnLHistoryResponse,
} from '../types';

export async function fetchTraderSummary(address: string) {
  const response = await apiClient.get<TraderSummary>(`/traders/${address}`);
  return response.data;
}

export async function fetchTraderTrades(address: string, params: TradeQueryParams) {
  const response = await apiClient.get<TraderTradeListResponse>(`/traders/${address}/trades`, {
    params,
  });
  return response.data;
}

export async function fetchTraderPositions(address: string) {
  const response = await apiClient.get<TraderPositionsResponse>(`/traders/${address}/positions`);
  return response.data;
}

export async function fetchTraderStats(address: string) {
  const response = await apiClient.get<TraderProfileStats>(`/traders/${address}/stats`);
  return response.data;
}

export async function fetchTraderLeaderboard(orderBy: string, limit = 25, offset = 0, timePeriod = 'DAY', category = 'OVERALL') {
  const response = await apiClient.get<TraderLeaderboardResponse>('/traders/top', {
    params: { orderBy, limit, offset, timePeriod, category, includeLevels: true },
  });
  return response.data;
}

export async function fetchTraderValue(address: string) {
  const response = await apiClient.get<TraderValueResponse>(`/traders/${address}/value`);
  return response.data;
}

export async function searchTraders(query: string, limit = 20) {
  const response = await apiClient.get<{ results: string[] }>('/traders/search', {
    params: { q: query, limit },
  });
  return response.data;
}

export async function fetchTraderPnLHistory(address: string, period = 'ALL') {
  const response = await apiClient.get<PnLHistoryResponse>(`/traders/${address}/pnl-history`, {
    params: { period },
  });
  return response.data;
}
