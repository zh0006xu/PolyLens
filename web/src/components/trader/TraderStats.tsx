import type { TraderSummary } from '../../types';

interface TraderStatsProps {
  summary: TraderSummary;
}

function formatCompactNumber(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}k`;
  }
  return `$${value.toFixed(0)}`;
}

function formatPnL(value: number): { text: string; isPositive: boolean } {
  const isPositive = value >= 0;
  const absValue = Math.abs(value);
  const sign = isPositive ? '+' : '-';

  // Format with commas and 2 decimal places for precision
  const formatted = absValue.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return {
    text: `${sign}$${formatted}`,
    isPositive,
  };
}

export function TraderStats({ summary }: TraderStatsProps) {
  const pnlInfo = summary.pnl !== null ? formatPnL(summary.pnl) : null;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {/* Positions Value */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-xs text-slate-400 mb-1">Positions Value</div>
        <div className="text-2xl font-bold text-white">
          {summary.positions_value !== null
            ? formatCompactNumber(summary.positions_value)
            : '-'}
        </div>
      </div>

      {/* Profit/Loss */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-xs text-slate-400 mb-1">Profit/Loss</div>
        <div className={`text-2xl font-bold ${pnlInfo?.isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
          {pnlInfo ? pnlInfo.text : '-'}
        </div>
        <div className="text-xs text-slate-500 mt-1">All-Time</div>
      </div>

      {/* Win Rate */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-xs text-slate-400 mb-1">Win Rate</div>
        <div className={`text-2xl font-bold ${
          summary.win_rate !== null
            ? summary.win_rate >= 50
              ? 'text-emerald-400'
              : 'text-amber-400'
            : 'text-white'
        }`}>
          {summary.win_rate !== null ? `${summary.win_rate}%` : '-'}
        </div>
        <div className="text-xs text-slate-500 mt-1">Closed positions</div>
      </div>

      {/* Biggest Win */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-xs text-slate-400 mb-1">Biggest Win</div>
        <div className="text-2xl font-bold text-emerald-400">
          {summary.biggest_win !== null && summary.biggest_win > 0
            ? formatCompactNumber(summary.biggest_win)
            : '-'}
        </div>
      </div>

      {/* Predictions (Total Markets Traded) */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
        <div className="text-xs text-slate-400 mb-1">Markets</div>
        <div className="text-2xl font-bold text-white">
          {summary.predictions !== null ? summary.predictions.toLocaleString() : '-'}
        </div>
        <div className="text-xs text-slate-500 mt-1">Total traded</div>
      </div>
    </div>
  );
}
