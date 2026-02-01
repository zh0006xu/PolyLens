import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import {
  fetchTraderSummary,
  fetchTraderTrades,
  fetchTraderPositions,
  fetchTraderStats,
  fetchTraderLeaderboard,
  fetchTraderValue,
  fetchTraderPnLHistory,
} from '../api/trader';
import type { TradeQueryParams } from '../types';

const isValidAddress = (address?: string) => /^0x[a-fA-F0-9]{40}$/.test(address || '');

export function useTraderSummary(address?: string) {
  return useQuery({
    queryKey: ['trader', address, 'summary'],
    queryFn: () => fetchTraderSummary(address as string),
    enabled: isValidAddress(address),
    staleTime: 60 * 1000,
  });
}

export function useTraderTrades(address: string | undefined, params: TradeQueryParams) {
  return useInfiniteQuery({
    queryKey: ['trader', address, 'trades', params],
    queryFn: ({ pageParam }) =>
      fetchTraderTrades(address as string, { ...params, offset: pageParam as number }),
    initialPageParam: params.offset || 0,
    getNextPageParam: (lastPage: { has_more: boolean; offset: number; limit: number }) =>
      lastPage.has_more ? lastPage.offset + lastPage.limit : undefined,
    enabled: isValidAddress(address),
  });
}

export function useTraderPositions(address?: string) {
  return useQuery({
    queryKey: ['trader', address, 'positions'],
    queryFn: () => fetchTraderPositions(address as string),
    enabled: isValidAddress(address),
  });
}

export function useTraderStats(address?: string) {
  return useQuery({
    queryKey: ['trader', address, 'stats'],
    queryFn: () => fetchTraderStats(address as string),
    enabled: isValidAddress(address),
    staleTime: 60 * 1000,
  });
}

export function useTraderLeaderboard(orderBy: string, limit = 25, offset = 0, timePeriod = 'DAY', category = 'OVERALL') {
  return useQuery({
    queryKey: ['trader', 'leaderboard', orderBy, timePeriod, category, limit, offset],
    queryFn: () => fetchTraderLeaderboard(orderBy, limit, offset, timePeriod, category),
    staleTime: 30 * 1000,
  });
}

export function useTraderValue(address?: string) {
  return useQuery({
    queryKey: ['trader', address, 'value'],
    queryFn: () => fetchTraderValue(address as string),
    enabled: isValidAddress(address),
    staleTime: 60 * 1000,
  });
}

export function useTraderPnLHistory(address?: string, period = 'ALL') {
  return useQuery({
    queryKey: ['trader', address, 'pnl-history', period],
    queryFn: () => fetchTraderPnLHistory(address as string, period),
    enabled: isValidAddress(address),
    staleTime: 60 * 1000,
  });
}
