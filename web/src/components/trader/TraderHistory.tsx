import { useMemo, useState } from 'react';
import { useTraderTrades } from '../../hooks/useTrader';
import { Badge } from '../common/Badge';
import { Spinner } from '../common/Spinner';
import { formatUSD, formatRelativeTime, truncateTxHash } from '../../utils/format';
import type { TraderTradeListResponse } from '../../types';

interface TraderHistoryProps {
  address: string;
}

const toStartIso = (value: string) => (value ? `${value}T00:00:00Z` : undefined);
const toEndIso = (value: string) => (value ? `${value}T23:59:59Z` : undefined);

export function TraderHistory({ address }: TraderHistoryProps) {
  const [side, setSide] = useState('');
  const [minUsd, setMinUsd] = useState('');
  const [maxUsd, setMaxUsd] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const params = useMemo(() => ({
    limit: 5,
    side: side || undefined,
    min_usd: minUsd ? Number(minUsd) : undefined,
    max_usd: maxUsd ? Number(maxUsd) : undefined,
    start_time: toStartIso(startDate),
    end_time: toEndIso(endDate),
  }), [side, minUsd, maxUsd, startDate, endDate]);

  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useTraderTrades(address, params);

  const trades = data?.pages.flatMap((page: TraderTradeListResponse) => page.trades) || [];
  const total = trades.length;

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Trade History</h2>
          <div className="text-xs text-slate-500 mt-1">Loaded {total} trades</div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={side}
            onChange={(e) => setSide(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Sides</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
          <input
            type="number"
            value={minUsd}
            onChange={(e) => setMinUsd(e.target.value)}
            placeholder="Min USD"
            className="w-24 bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="number"
            value={maxUsd}
            onChange={(e) => setMaxUsd(e.target.value)}
            placeholder="Max USD"
            className="w-24 bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
          />
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Spinner />
        </div>
      ) : trades.length === 0 ? (
        <div className="text-center text-slate-400 py-8">No trades found</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
                <th className="text-left py-3 px-4">Time</th>
                <th className="text-left py-3 px-4">Market</th>
                <th className="text-left py-3 px-4">Side</th>
                <th className="text-left py-3 px-4">Position</th>
                <th className="text-right py-3 px-4">Price</th>
                <th className="text-right py-3 px-4">Size</th>
                <th className="text-right py-3 px-4">Value</th>
                <th className="text-left py-3 px-4">Tx</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, idx) => (
                <tr
                  key={`${trade.transactionHash || 'trade'}-${trade.timestamp || idx}`}
                  className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                >
                  <td className="py-3 px-4 text-slate-400">
                    {trade.timestamp ? formatRelativeTime(trade.timestamp) : '-'}
                  </td>
                  <td className="py-3 px-4 text-slate-200">
                    {trade.slug ? (
                      <a
                        href={`https://polymarket.com/market/${trade.slug}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-indigo-400 transition-colors"
                      >
                        {trade.title || trade.slug}
                      </a>
                    ) : (
                      trade.title || trade.slug || '-'
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                      {trade.side || '-'}
                    </Badge>
                  </td>
                  <td className="py-3 px-4">
                    <Badge variant={
                      trade.outcomeIndex === 0 || trade.outcome?.toUpperCase() === 'YES'
                        ? 'info'
                        : 'default'
                    }>
                      {trade.outcome || '-'}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-right text-white font-mono">
                    {trade.price !== null && trade.price !== undefined ? `$${trade.price.toFixed(2)}` : '-'}
                  </td>
                  <td className="py-3 px-4 text-right text-slate-300 font-mono">
                    {trade.size !== null && trade.size !== undefined
                      ? trade.size.toLocaleString(undefined, { maximumFractionDigits: 0 })
                      : '-'}
                  </td>
                  <td className="py-3 px-4 text-right text-white font-bold">
                    {trade.usdValue !== null && trade.usdValue !== undefined
                      ? formatUSD(trade.usdValue)
                      : trade.price && trade.size
                      ? formatUSD(trade.price * trade.size)
                      : '-'}
                  </td>
                  <td className="py-3 px-4">
                    {trade.transactionHash ? (
                      <a
                        href={`https://polygonscan.com/tx/${trade.transactionHash}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-400 hover:text-indigo-400 font-mono"
                      >
                        {truncateTxHash(trade.transactionHash)}
                      </a>
                    ) : (
                      '-'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {hasNextPage && (
        <div className="mt-4 text-center">
          <button
            onClick={() => fetchNextPage()}
            disabled={isFetchingNextPage}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-sm transition-colors disabled:opacity-60"
          >
            {isFetchingNextPage ? 'Loading...' : 'Load More'}
          </button>
        </div>
      )}
    </div>
  );
}
