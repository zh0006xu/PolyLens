import { useQuery } from '@tanstack/react-query';
import { fetchWhales, fetchRecentWhales } from '../api/whales';

export function useWhales(marketId?: number, limit: number = 20, minUsd?: number) {
  return useQuery({
    queryKey: ['whales', marketId, limit, minUsd],
    queryFn: () => fetchWhales(marketId, limit, minUsd),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

export function useRecentWhales(limit: number = 10) {
  return useQuery({
    queryKey: ['whales', 'recent', limit],
    queryFn: () => fetchRecentWhales(limit),
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}
