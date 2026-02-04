import { useMemo } from 'react';
import { useTraderStats } from '../../hooks/useTrader';
import { Spinner } from '../common/Spinner';
import { formatUSD } from '../../utils/format';

interface TraderPatternsProps {
  address: string;
}

export function TraderPatterns({ address }: TraderPatternsProps) {
  const { data, isLoading } = useTraderStats(address);

  const topCategories = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.categories)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [data]);

  if (isLoading) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Trading Patterns</h2>
        <div className="text-center text-slate-400 py-6">No trading stats available</div>
      </div>
    );
  }

  const yesPercentage = (data.yes_preference * 100).toFixed(1);
  const buySellTotal = data.buy_volume + data.sell_volume;
  const buyPercent = buySellTotal > 0 ? (data.buy_volume / buySellTotal) * 100 : 0;

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Trading Patterns</h2>
        <p className="text-xs text-slate-500 mt-1">Behavior breakdown based on historical trades</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="trading-pattern-card bg-slate-950/60 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400 font-medium">Buy vs Sell Volume</div>
          <div className="flex items-center justify-between text-xs text-slate-200 mt-2">
            <span>Buy</span>
            <span>{formatUSD(data.buy_volume)}</span>
          </div>
          <div className="flex items-center justify-between text-xs text-slate-200 mt-1">
            <span>Sell</span>
            <span>{formatUSD(data.sell_volume)}</span>
          </div>
          <div className="mt-3 h-2 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-emerald-500" style={{ width: `${buyPercent}%` }} />
          </div>
        </div>
        <div className="trading-pattern-card bg-slate-950/60 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400 font-medium">YES Preference</div>
          <div className="text-2xl font-semibold text-white mt-2">{yesPercentage}%</div>
          <div className="text-xs text-slate-500 mt-1">Share of volume on YES</div>
        </div>
        <div className="trading-pattern-card bg-slate-950/60 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400 font-medium">Avg Trade Size</div>
          <div className="text-2xl font-semibold text-white mt-2">
            {formatUSD(data.avg_trade_size)}
          </div>
          <div className="text-xs text-slate-500 mt-1">Average USD per trade</div>
        </div>
        <div className="trading-pattern-card bg-slate-950/60 border border-slate-800 rounded-lg p-4">
          <div className="text-sm text-slate-400 font-medium mb-3">Top Categories</div>
          <div className="space-y-2">
            {topCategories.length === 0 ? (
              <div className="text-slate-500 text-xs">No category data</div>
            ) : (
              topCategories.map(([category, volume]) => (
                <div key={category} className="flex items-center justify-between text-xs">
                  <span className="text-slate-300">{category}</span>
                  <span className="text-slate-200 font-mono">{formatUSD(volume)}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
