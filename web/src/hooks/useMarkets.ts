import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { fetchMarkets, fetchMarket, fetchMarketPrice } from '../api/markets';
import type { MarketQueryParams } from '../types';

// Cache settings: data stays fresh for 30 seconds, cached for 5 minutes
const STALE_TIME = 30 * 1000; // 30 seconds
const GC_TIME = 5 * 60 * 1000; // 5 minutes

export function useMarkets(params: MarketQueryParams = {}) {
  return useQuery({
    queryKey: ['markets', params],
    queryFn: () => fetchMarkets(params),
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  });
}

export function useInfiniteMarkets(params: Omit<MarketQueryParams, 'offset'> = {}) {
  const limit = params.limit || 20;

  return useInfiniteQuery({
    queryKey: ['markets', 'infinite', params],
    queryFn: ({ pageParam = 0 }) => fetchMarkets({ ...params, offset: pageParam, limit }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const totalFetched = allPages.reduce((sum, page) => sum + page.markets.length, 0);
      return lastPage.has_more ? totalFetched : undefined;
    },
    staleTime: STALE_TIME,
    gcTime: GC_TIME,
  });
}

export function useMarket(marketId: number | undefined, tokenId?: string) {
  return useQuery({
    queryKey: ['market', marketId, tokenId],
    queryFn: () => fetchMarket(marketId!, tokenId),
    enabled: !!marketId,
  });
}

export function useMarketPrice(marketId: number | undefined) {
  return useQuery({
    queryKey: ['marketPrice', marketId],
    queryFn: () => fetchMarketPrice(marketId!),
    enabled: !!marketId,
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}
