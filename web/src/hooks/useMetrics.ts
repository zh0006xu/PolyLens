import { useQuery } from '@tanstack/react-query';
import { fetchMetrics } from '../api/metrics';

export function useMetrics(marketId: number | undefined, period: string = '24h', tokenId?: string) {
  return useQuery({
    queryKey: ['metrics', marketId, period, tokenId],
    queryFn: () => fetchMetrics(marketId!, period, tokenId),
    enabled: !!marketId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}
