import { useQuery } from '@tanstack/react-query';
import { fetchKlines } from '../api/klines';
import type { KlineQueryParams } from '../types';

export function useKlines(params: KlineQueryParams) {
  return useQuery({
    queryKey: ['klines', params],
    queryFn: () => fetchKlines(params),
    enabled: !!params.market_id,
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}
