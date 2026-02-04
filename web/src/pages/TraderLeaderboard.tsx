import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useTraderLeaderboard } from '../hooks/useTrader';
import { fetchTraderLeaderboard } from '../api/trader';
import { TraderSearch, TraderLevelBadge } from '../components/trader';
import { formatUSD, truncateAddress } from '../utils/format';

// Skeleton row component for loading state
function SkeletonRow() {
  return (
    <tr className="border-b border-slate-800/50">
      <td className="py-3 px-4">
        <div className="h-4 w-8 bg-slate-700 rounded animate-pulse" />
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-700 animate-pulse" />
          <div className="space-y-2">
            <div className="h-4 w-32 bg-slate-700 rounded animate-pulse" />
            <div className="h-3 w-20 bg-slate-800 rounded animate-pulse" />
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-right">
        <div className="h-4 w-24 bg-slate-700 rounded animate-pulse ml-auto" />
      </td>
      <td className="py-3 px-4 text-right">
        <div className="h-4 w-20 bg-slate-700 rounded animate-pulse ml-auto" />
      </td>
    </tr>
  );
}

type SortField = 'vol' | 'pnl';
type TimePeriod = 'DAY' | 'WEEK' | 'MONTH' | 'ALL';

const timePeriodOptions: { value: TimePeriod; label: string }[] = [
  { value: 'DAY', label: '24h' },
  { value: 'WEEK', label: '7d' },
  { value: 'MONTH', label: '30d' },
  { value: 'ALL', label: 'All Time' },
];

export function TraderLeaderboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [sortField, setSortField] = useState<SortField>('pnl');
  const [timePeriod, setTimePeriod] = useState<TimePeriod>(() => {
    const period = searchParams.get('period');
    const normalized = period ? period.toUpperCase() : null;
    const isValid = timePeriodOptions.some((option) => option.value === normalized);
    return (isValid ? normalized : 'DAY') as TimePeriod;
  });
  const queryClient = useQueryClient();
  const { data, isLoading } = useTraderLeaderboard(sortField === 'vol' ? 'VOL' : 'PNL', 25, 0, timePeriod, 'OVERALL');

  const handleSort = (field: SortField) => {
    if (sortField !== field) {
      setSortField(field);
    }
  };

  // Prefetch data on hover
  const handleTimePeriodHover = (period: TimePeriod) => {
    const orderBy = sortField === 'vol' ? 'VOL' : 'PNL';
    queryClient.prefetchQuery({
      queryKey: ['trader', 'leaderboard', orderBy, period, 'OVERALL', 25, 0],
      queryFn: () => fetchTraderLeaderboard(orderBy, 25, 0, period, 'OVERALL'),
      staleTime: 30 * 1000,
    });
  };

  const handleTimePeriodChange = (nextPeriod: TimePeriod) => {
    setTimePeriod(nextPeriod);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('period', nextPeriod);
    setSearchParams(nextParams, { replace: true });
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return (
        <svg className="w-3 h-3 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      );
    }
    return (
      <svg className="w-3 h-3 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    );
  };

  const SortableHeader = ({ field, children, align = 'left' }: { field: SortField; children: React.ReactNode; align?: 'left' | 'right' }) => (
    <th
      className={`text-${align} py-3 px-4 cursor-pointer hover:text-slate-200 transition-colors`}
      onClick={() => handleSort(field)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : ''}`}>
        {children}
        <SortIcon field={field} />
      </div>
    </th>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Trader Leaderboard</h1>
        <p className="text-slate-400 text-sm mt-1">Polymarket official ranking</p>
      </div>

      {/* Search bar and time period selector row */}
      <div className="flex items-center justify-between gap-4">
        {/* Search bar - left aligned */}
        <div className="flex-1 max-w-md">
          <TraderSearch />
        </div>
        {/* Time period selector - right aligned */}
        <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-1">
          {timePeriodOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => handleTimePeriodChange(option.value)}
              onMouseEnter={() => handleTimePeriodHover(option.value)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                timePeriod === option.value
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        {isLoading ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
                  <th className="text-left py-3 px-4 w-16">Rank</th>
                  <th className="text-left py-3 px-4">Trader</th>
                  <th className="text-right py-3 px-4">Volume</th>
                  <th className="text-right py-3 px-4">PnL</th>
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: 10 }).map((_, i) => (
                  <SkeletonRow key={i} />
                ))}
              </tbody>
            </table>
          </div>
        ) : !data || data.traders.length === 0 ? (
          <div className="text-center text-slate-400 py-8">No traders found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
                  <th className="text-left py-3 px-4 w-16">Rank</th>
                  <th className="text-left py-3 px-4">Trader</th>
                  <SortableHeader field="vol" align="right">
                    Volume {timePeriod === 'ALL' ? '' : `(${timePeriodOptions.find(o => o.value === timePeriod)?.label})`}
                  </SortableHeader>
                  <SortableHeader field="pnl" align="right">
                    PnL {timePeriod === 'ALL' ? '' : `(${timePeriodOptions.find(o => o.value === timePeriod)?.label})`}
                  </SortableHeader>
                </tr>
              </thead>
              <tbody>
                {data.traders.map((trader, index) => (
                  <tr
                    key={`${trader.proxyWallet || 'trader'}-${index}`}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="py-3 px-4 text-slate-400">#{trader.rank || index + 1}</td>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        {trader.profileImage ? (
                          <img
                            src={trader.profileImage}
                            alt={trader.userName || trader.proxyWallet || 'Trader'}
                            className="w-8 h-8 rounded-full object-cover border border-slate-700"
                          />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-slate-400">
                            {trader.userName ? trader.userName.slice(0, 2).toUpperCase() : '0x'}
                          </div>
                        )}
                        <div>
                          <div className="flex items-center gap-1.5">
                            {trader.proxyWallet ? (
                              <Link
                                to={`/trader/${trader.proxyWallet}`}
                                className="text-indigo-400 hover:text-indigo-300 font-medium"
                              >
                                {trader.userName || truncateAddress(trader.proxyWallet)}
                              </Link>
                            ) : (
                              <span className="text-slate-300">
                                {trader.userName || 'Unknown'}
                              </span>
                            )}
                            {trader.verifiedBadge && (
                              <span className="text-emerald-400 text-xs" title="Verified">✓</span>
                            )}
                            <TraderLevelBadge level={trader.whale_level} size="sm" />
                          </div>
                          {trader.xUsername && (
                            <div className="text-xs text-slate-500">@{trader.xUsername}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right text-white font-semibold">
                      {formatUSD(trader.vol || 0)}
                    </td>
                    <td className={`py-3 px-4 text-right font-semibold ${(trader.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {formatUSD(trader.pnl || 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
