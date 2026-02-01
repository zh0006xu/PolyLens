import { useQuery } from '@tanstack/react-query';
import { fetchMarketHolders } from '../api/holders';

export function useMarketHolders(marketId?: number, limit: number = 10) {
  return useQuery({
    queryKey: ['holders', marketId, limit],
    queryFn: () => fetchMarketHolders(marketId!, limit),
    enabled: !!marketId,
    refetchInterval: 60000,
  });
}
