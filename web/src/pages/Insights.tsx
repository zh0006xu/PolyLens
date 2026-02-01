import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useHotMarkets, useVolumeAnomalies, useSmartMoney } from '../hooks/useInsights';
import { Spinner } from '../components/common';
import { formatUSD } from '../utils/format';

// ============== Helper Components ==============

// 问号提示组件
function InfoTooltip({ text }: { text: string }) {
  return (
    <div className="group relative inline-flex ml-1">
      <span className="w-4 h-4 rounded-full bg-slate-700 text-slate-400 text-xs flex items-center justify-center cursor-help hover:bg-slate-600">
        ?
      </span>
      <div className="hidden group-hover:block absolute right-0 top-full mt-1 z-20 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 w-64 shadow-lg">
        {text}
      </div>
    </div>
  );
}

// 指标说明
const METRIC_EXPLANATIONS = {
  sentiment: "Overall Sentiment = 鲸鱼买入金额 / (买入 + 卖出金额) × 100%。≥60% 为 Bullish，≤40% 为 Bearish。",
  netFlow: "Smart Money Net Flow = 24h 内鲸鱼（≥$1000）买入总额 - 卖出总额。正数表示资金净流入。",
  anomalies: "Volume Anomalies = 24h 交易量 ≥ 30日均值 × 2 的市场数量。表示有异常活跃的市场。",
  totalVolume: "Top 10 Volume = 当前热门 Top 10 市场的 24h 总交易量之和。",
  volumeRatio: "Volume Ratio = 24h 交易量 / 30日日均交易量。越高说明今日活跃度越异常。",
  signalStrength: "Signal Strength: Strong (净流向占比≥50%), Moderate (≥25%), Weak (<25%)。",
  price: "YES Price = YES token 的当前价格（0-1）。价格越高表示市场认为该事件越可能发生。",
  priceChange: "24h Change = (当前价格 - 24h前价格) / 24h前价格 × 100%。",
};

function SentimentBadge({ value, type }: { value: number; type: 'percent' | 'flow' }) {
  let color = 'text-slate-400';
  let bg = 'bg-slate-800';
  let label = 'Neutral';

  if (type === 'percent') {
    if (value >= 60) {
      color = 'text-emerald-400';
      bg = 'bg-emerald-500/20';
      label = 'Bullish';
    } else if (value <= 40) {
      color = 'text-red-400';
      bg = 'bg-red-500/20';
      label = 'Bearish';
    }
  } else {
    if (value > 0) {
      color = 'text-emerald-400';
      bg = 'bg-emerald-500/20';
      label = 'Inflow';
    } else if (value < 0) {
      color = 'text-red-400';
      bg = 'bg-red-500/20';
      label = 'Outflow';
    }
  }

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${color} ${bg}`}>
      {label}
    </span>
  );
}

function PriceChange({ value }: { value: number | null }) {
  if (value === null) return <span className="text-slate-500">-</span>;
  const isPositive = value >= 0;
  return (
    <span className={isPositive ? 'text-emerald-400' : 'text-red-400'}>
      {isPositive ? '+' : ''}{value.toFixed(1)}%
    </span>
  );
}

function FlowArrow({ direction }: { direction: string }) {
  if (direction === 'inflow') {
    return <span className="text-emerald-400 text-lg">↑</span>;
  }
  if (direction === 'outflow') {
    return <span className="text-red-400 text-lg">↓</span>;
  }
  return <span className="text-slate-400 text-lg">→</span>;
}

function SignalStrength({ strength }: { strength: string }) {
  const dots = strength === 'strong' ? 3 : strength === 'moderate' ? 2 : 1;
  const color = strength === 'strong' ? 'bg-emerald-400' : strength === 'moderate' ? 'bg-amber-400' : 'bg-slate-500';

  return (
    <div className="flex gap-0.5">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i <= dots ? color : 'bg-slate-700'}`}
        />
      ))}
    </div>
  );
}

// ============== Main Page Component ==============

export function Insights() {
  const [timeRange] = useState(24);

  const { data: hotData, isLoading: hotLoading } = useHotMarkets(10);
  const { data: anomalyData, isLoading: anomalyLoading } = useVolumeAnomalies(2.0, 10);
  const { data: smartData, isLoading: smartLoading } = useSmartMoney(15, timeRange, 1000);

  // Calculate overall sentiment based on whale volume (not just count)
  const totalBuyVolume = smartData?.flows.reduce((sum, f) => sum + (f.whale_buy_volume || 0), 0) || 0;
  const totalSellVolume = smartData?.flows.reduce((sum, f) => sum + (f.whale_sell_volume || 0), 0) || 0;
  const totalWhaleVolume = totalBuyVolume + totalSellVolume;
  const bullishPercent = totalWhaleVolume > 0 ? Math.round((totalBuyVolume / totalWhaleVolume) * 100) : 50;

  // Calculate total 24h volume from hot markets
  const totalHotMarketVolume = hotData?.markets.reduce((sum, m) => sum + (m.volume_24h || 0), 0) || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Market Insights</h1>
        <p className="text-slate-400 text-sm mt-1">Real-time market sentiment and smart money tracking</p>
      </div>

      {/* ============== Sentiment Dashboard ============== */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-xl border border-slate-700 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Market Sentiment Dashboard</h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Overall Sentiment */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="flex items-center text-xs text-slate-400 mb-1">
              Overall Sentiment
              <InfoTooltip text={METRIC_EXPLANATIONS.sentiment} />
            </div>
            {smartLoading ? (
              <div className="text-slate-500">Loading...</div>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <span className={`text-2xl font-bold ${bullishPercent >= 50 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {bullishPercent}%
                  </span>
                  <SentimentBadge value={bullishPercent} type="percent" />
                </div>
                <div className="text-xs text-slate-500 mt-1">Whale buy ratio</div>
              </>
            )}
          </div>

          {/* Net Flow */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="flex items-center text-xs text-slate-400 mb-1">
              Smart Money Net Flow
              <InfoTooltip text={METRIC_EXPLANATIONS.netFlow} />
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${(smartData?.total_net_flow || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {formatUSD(Math.abs(smartData?.total_net_flow || 0))}
              </span>
              <SentimentBadge value={smartData?.total_net_flow || 0} type="flow" />
            </div>
            <div className="text-xs text-slate-500 mt-1">24h whale activity</div>
          </div>

          {/* Volume Anomalies */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="flex items-center text-xs text-slate-400 mb-1">
              Volume Anomalies
              <InfoTooltip text={METRIC_EXPLANATIONS.anomalies} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-amber-400">
                {anomalyData?.anomalies.length || 0}
              </span>
              <span className="text-xs text-slate-400">markets</span>
            </div>
            <div className="text-xs text-slate-500 mt-1">Unusual activity detected</div>
          </div>

          {/* Total Volume */}
          <div className="bg-slate-800/50 rounded-lg p-4">
            <div className="flex items-center text-xs text-slate-400 mb-1">
              Top 10 Volume
              <InfoTooltip text={METRIC_EXPLANATIONS.totalVolume} />
            </div>
            {hotLoading ? (
              <div className="text-slate-500">Loading...</div>
            ) : (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-indigo-400">
                    {formatUSD(totalHotMarketVolume)}
                  </span>
                </div>
                <div className="text-xs text-slate-500 mt-1">Hot markets 24h vol</div>
              </>
            )}
          </div>
        </div>

        {/* Sentiment Bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>Bearish</span>
            <span>Bullish</span>
          </div>
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-red-500 via-amber-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${bullishPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* ============== Hot Markets ============== */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Hot Markets</h2>
          <span className="text-xs text-slate-500">24h activity ranking</span>
        </div>

        {hotLoading ? (
          <div className="flex justify-center py-8"><Spinner /></div>
        ) : !hotData?.markets.length ? (
          <div className="text-center text-slate-400 py-8">No data available</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
                  <th className="text-left py-3 px-2">#</th>
                  <th className="text-left py-3 px-2">Market</th>
                  <th className="text-right py-3 px-2">
                    <div className="flex items-center justify-end">
                      YES Price
                      <InfoTooltip text={METRIC_EXPLANATIONS.price} />
                    </div>
                  </th>
                  <th className="text-right py-3 px-2">
                    <div className="flex items-center justify-end">
                      24h Change
                      <InfoTooltip text={METRIC_EXPLANATIONS.priceChange} />
                    </div>
                  </th>
                  <th className="text-right py-3 px-2">Volume</th>
                  <th className="text-right py-3 px-2">Traders</th>
                </tr>
              </thead>
              <tbody>
                {hotData.markets.map((market, idx) => (
                  <tr key={market.id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-3 px-2 text-slate-500">{idx + 1}</td>
                    <td className="py-3 px-2">
                      <Link
                        to={`/market/${market.id}`}
                        className="text-indigo-400 hover:text-indigo-300 line-clamp-1"
                      >
                        {market.question || market.slug}
                      </Link>
                      {market.category && (
                        <div className="text-xs text-slate-500">{market.category}</div>
                      )}
                    </td>
                    <td className="py-3 px-2 text-right text-white">
                      {market.current_price ? `${(market.current_price * 100).toFixed(0)}¢` : '-'}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <PriceChange value={market.price_change_24h} />
                    </td>
                    <td className="py-3 px-2 text-right text-white">{formatUSD(market.volume_24h)}</td>
                    <td className="py-3 px-2 text-right text-slate-300">{market.unique_traders_24h}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ============== Two Column Layout ============== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Volume Anomalies */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <h2 className="text-lg font-semibold text-white">Volume Anomalies</h2>
              <InfoTooltip text={METRIC_EXPLANATIONS.volumeRatio} />
            </div>
            <span className="text-xs text-amber-400">2x+ avg volume</span>
          </div>

          {anomalyLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : !anomalyData?.anomalies.length ? (
            <div className="text-center text-slate-400 py-8">No anomalies detected</div>
          ) : (
            <div className="space-y-3">
              {anomalyData.anomalies.slice(0, 8).map((item) => (
                <div
                  key={item.market_id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/market/${item.market_id}`}
                      className="text-sm text-indigo-400 hover:text-indigo-300 line-clamp-1"
                    >
                      {item.question || item.slug}
                    </Link>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {item.trade_count_24h} trades
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className="text-amber-400 font-semibold">
                      {item.volume_ratio.toFixed(1)}x
                    </div>
                    <div className="text-xs text-slate-500">
                      {formatUSD(item.volume_24h)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Smart Money Flow */}
        <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <h2 className="text-lg font-semibold text-white">Smart Money Flow</h2>
              <InfoTooltip text={METRIC_EXPLANATIONS.signalStrength} />
            </div>
            <span className="text-xs text-slate-500">Whale trades $1k+</span>
          </div>

          {smartLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : !smartData?.flows.length ? (
            <div className="text-center text-slate-400 py-8">No whale activity</div>
          ) : (
            <div className="space-y-3">
              {smartData.flows.slice(0, 8).map((flow) => (
                <div
                  key={flow.market_id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <FlowArrow direction={flow.flow_direction} />
                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/market/${flow.market_id}`}
                        className="text-sm text-indigo-400 hover:text-indigo-300 line-clamp-1"
                      >
                        {flow.question || flow.slug}
                      </Link>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-emerald-400">
                          {flow.whale_buy_count} buys
                        </span>
                        <span className="text-xs text-red-400">
                          {flow.whale_sell_count} sells
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className={`font-semibold ${flow.whale_net_flow >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {flow.whale_net_flow >= 0 ? '+' : ''}{formatUSD(flow.whale_net_flow)}
                    </div>
                    <div className="flex items-center justify-end gap-1 mt-0.5">
                      <span className="text-xs text-slate-500">{flow.signal_strength}</span>
                      <SignalStrength strength={flow.signal_strength} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="text-center text-xs text-slate-500">
        Data refreshes every 10 seconds • Last updated: {smartData?.updated_at ? new Date(smartData.updated_at).toLocaleTimeString() : '-'}
      </div>
    </div>
  );
}
