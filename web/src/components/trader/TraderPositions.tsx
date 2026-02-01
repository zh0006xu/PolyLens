import { useState } from 'react';
import { useTraderPositions } from '../../hooks/useTrader';
import { Badge } from '../common/Badge';
import { Spinner } from '../common/Spinner';
import { formatUSD } from '../../utils/format';

interface TraderPositionsProps {
  address: string;
}

const PAGE_SIZE = 5;

export function TraderPositions({ address }: TraderPositionsProps) {
  const [displayCount, setDisplayCount] = useState(PAGE_SIZE);
  const { data, isLoading } = useTraderPositions(address);

  if (isLoading) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      </div>
    );
  }

  if (!data || data.positions.length === 0) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Active Positions</h2>
        <div className="text-center text-slate-400 py-6">No active positions</div>
      </div>
    );
  }

  const displayedPositions = data.positions.slice(0, displayCount);
  const hasMore = data.positions.length > displayCount;

  const handleLoadMore = () => {
    setDisplayCount((prev) => prev + PAGE_SIZE);
  };

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Active Positions</h2>
          <div className="text-xs text-slate-500 mt-1">
            {data.summary.total_positions} markets
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
              <th className="text-left py-3 px-4">Market</th>
              <th className="text-left py-3 px-4">Position</th>
              <th className="text-right py-3 px-4">Qty</th>
              <th className="text-right py-3 px-4">Avg Cost</th>
              <th className="text-right py-3 px-4">Current</th>
              <th className="text-right py-3 px-4">PnL</th>
            </tr>
          </thead>
          <tbody>
            {displayedPositions.map((pos) => (
              <tr
                key={`${pos.conditionId || pos.slug || 'pos'}-${pos.outcome || 'outcome'}`}
                className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                <td className="py-3 px-4 text-slate-200">
                  {pos.slug ? (
                    <a
                      href={`https://polymarket.com/market/${pos.slug}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:text-indigo-400 transition-colors"
                    >
                      {pos.title || pos.slug}
                    </a>
                  ) : (
                    pos.title || pos.slug || '-'
                  )}
                </td>
                <td className="py-3 px-4">
                  <Badge variant={
                    pos.outcomeIndex === 0 || pos.outcome?.toUpperCase() === 'YES'
                      ? 'info'
                      : 'default'
                  }>
                    {pos.outcome || '-'}
                  </Badge>
                </td>
                <td className="py-3 px-4 text-right text-slate-200 font-mono">
                  {(pos.size || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </td>
                <td className="py-3 px-4 text-right text-slate-200 font-mono">
                  {pos.avgPrice !== null && pos.avgPrice !== undefined ? `$${pos.avgPrice.toFixed(2)}` : '-'}
                </td>
                <td className="py-3 px-4 text-right text-white font-mono">
                  {pos.curPrice !== null && pos.curPrice !== undefined ? `$${pos.curPrice.toFixed(2)}` : '-'}
                </td>
                <td className={`py-3 px-4 text-right font-semibold ${
                  (pos.cashPnl ?? 0) > 0
                    ? 'text-emerald-400'
                    : (pos.cashPnl ?? 0) < 0
                      ? 'text-red-400'
                      : 'text-amber-400'
                }`}>
                  {pos.cashPnl !== null && pos.cashPnl !== undefined
                    ? `${pos.cashPnl >= 0 ? '+' : ''}${formatUSD(pos.cashPnl)}`
                    : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hasMore && (
        <div className="mt-4 text-center">
          <button
            onClick={handleLoadMore}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-sm transition-colors"
          >
            Load More ({data.positions.length - displayCount} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
