import type { Metrics } from '../../types';
import { MetricCard } from './MetricCard';
import { formatVolume, formatPriceCents } from '../../utils/format';
import { Spinner } from '../common/Spinner';

interface MetricsPanelProps {
  metrics: Metrics | undefined;
  isLoading: boolean;
  period: string;
  onPeriodChange: (period: string) => void;
}

// Metric tooltips with formula and meaning
const TOOLTIPS = {
  buyPressure: {
    formula: 'Buy Volume / Total Volume × 100%',
    meaning: 'Market sentiment indicator. >55% = bullish, <45% = bearish. Shows whether buyers or sellers dominate.',
  },
  vwap: {
    formula: 'Σ(Price × Volume) / Σ(Volume)',
    meaning: 'Volume Weighted Average Price. Institutional benchmark for fair value. Price above VWAP = strong momentum.',
  },
  whaleSignal: {
    formula: 'Net direction of trades > $1000',
    meaning: 'Smart money indicator. Whales often have better information. Follow their direction for higher win rate.',
  },
  traders: {
    formula: 'Count of unique wallet addresses',
    meaning: 'Market breadth indicator. Rising traders + rising price = healthy trend with broad participation.',
  },
  netFlow: {
    formula: 'Buy Volume - Sell Volume',
    meaning: 'Capital flow direction. Positive = inflow (bullish), Negative = outflow (bearish). Precedes price moves.',
  },
  volume: {
    formula: 'Σ(Trade Size × Price)',
    meaning: 'Total trading activity. High volume confirms price moves, low volume suggests weak conviction.',
  },
};

export function MetricsPanel({ metrics, isLoading, period, onPeriodChange }: MetricsPanelProps) {
  const periods = ['1h', '4h', '24h'];

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="text-center text-slate-400 py-8">
        No metrics data available
      </div>
    );
  }

  const buyRatio = metrics.buy_sell_ratio;
  const whaleSignal = metrics.whale_signal;
  const traderStats = metrics.trader_stats;
  const netFlow = metrics.net_flow;
  const vwap = metrics.vwap;

  const buyPercentage = buyRatio.buy_percentage || 0;
  const signalTrend = whaleSignal.signal === 'bullish' ? 'up' : whaleSignal.signal === 'bearish' ? 'down' : 'neutral';

  return (
    <div className="space-y-4">
      {/* Period selector */}
      <div className="flex items-center gap-2">
        <span className="text-slate-400 text-sm">Period:</span>
        {periods.map((p) => (
          <button
            key={p}
            onClick={() => onPeriodChange(p)}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              period === p
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          title="Buy Pressure"
          value={`${buyPercentage.toFixed(0)}%`}
          subtitle={`${buyRatio.buy_count} buys`}
          trend={buyPercentage > 55 ? 'up' : buyPercentage < 45 ? 'down' : 'neutral'}
          tooltip={TOOLTIPS.buyPressure}
        />
        <MetricCard
          title="VWAP"
          value={formatPriceCents(vwap.vwap)}
          subtitle={`${vwap.trade_count} trades`}
          tooltip={TOOLTIPS.vwap}
        />
        <MetricCard
          title="Whale Signal"
          value={whaleSignal.signal.toUpperCase()}
          subtitle={`Strength: ${(whaleSignal.signal_strength * 100).toFixed(0)}%`}
          trend={signalTrend}
          tooltip={TOOLTIPS.whaleSignal}
        />
        <MetricCard
          title="Traders"
          value={traderStats.unique_traders}
          subtitle={`Avg: ${formatPriceCents(traderStats.avg_trade_size)}`}
          tooltip={TOOLTIPS.traders}
        />
        <MetricCard
          title="Net Flow"
          value={`$${formatVolume(Math.abs(netFlow.net_flow))}`}
          subtitle={netFlow.net_flow >= 0 ? 'Inflow' : 'Outflow'}
          trend={netFlow.net_flow > 0 ? 'up' : netFlow.net_flow < 0 ? 'down' : 'neutral'}
          tooltip={TOOLTIPS.netFlow}
        />
        <MetricCard
          title="Volume"
          value={`$${formatVolume(buyRatio.buy_volume + buyRatio.sell_volume)}`}
          subtitle={`${buyRatio.buy_count + buyRatio.sell_count} trades`}
          tooltip={TOOLTIPS.volume}
        />
      </div>
    </div>
  );
}
