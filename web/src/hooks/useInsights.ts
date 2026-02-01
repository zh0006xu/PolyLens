import { useQuery } from '@tanstack/react-query';
import {
  fetchHotMarkets,
  fetchVolumeAnomalies,
  fetchSmartMoney,
} from '../api/insights';

const REFETCH_INTERVAL = 10 * 1000; // 10 seconds

export function useHotMarkets(limit = 10, category?: string) {
  return useQuery({
    queryKey: ['insights', 'hot-markets', limit, category],
    queryFn: () => fetchHotMarkets(limit, category),
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useVolumeAnomalies(threshold = 2.0, limit = 20) {
  return useQuery({
    queryKey: ['insights', 'volume-anomalies', threshold, limit],
    queryFn: () => fetchVolumeAnomalies(threshold, limit),
    refetchInterval: REFETCH_INTERVAL,
  });
}

export function useSmartMoney(limit = 20, hours = 24, minWhaleValue = 1000) {
  return useQuery({
    queryKey: ['insights', 'smart-money', limit, hours, minWhaleValue],
    queryFn: () => fetchSmartMoney(limit, hours, minWhaleValue),
    refetchInterval: REFETCH_INTERVAL,
  });
}
