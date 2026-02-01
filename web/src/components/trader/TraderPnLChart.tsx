import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, LineSeries } from 'lightweight-charts';
import type { IChartApi, LineData, Time } from 'lightweight-charts';
import { useTraderPnLHistory } from '../../hooks/useTrader';
import { Spinner } from '../common/Spinner';

interface TraderPnLChartProps {
  address: string;
}

const PERIODS = ['1D', '1W', '1M', 'ALL'] as const;
type Period = (typeof PERIODS)[number];

function formatPnL(value: number): string {
  const isPositive = value >= 0;
  const absValue = Math.abs(value);
  const sign = isPositive ? '+' : '-';

  if (absValue >= 1_000_000) {
    return `${sign}$${(absValue / 1_000_000).toFixed(2)}M`;
  }
  if (absValue >= 1_000) {
    return `${sign}$${(absValue / 1_000).toFixed(2)}k`;
  }
  return `${sign}$${absValue.toFixed(2)}`;
}

export function TraderPnLChart({ address }: TraderPnLChartProps) {
  const [period, setPeriod] = useState<Period>('ALL');
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const { data, isLoading } = useTraderPnLHistory(address, period);

  useEffect(() => {
    if (!chartContainerRef.current || !data?.data_points?.length) return;

    const chartWidth = chartContainerRef.current.clientWidth;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      width: chartWidth,
      height: 200,
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#6366f1',
          width: 1,
          style: 2,
          labelBackgroundColor: '#6366f1',
        },
        horzLine: {
          color: '#6366f1',
          width: 1,
          style: 2,
          labelBackgroundColor: '#6366f1',
        },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#334155',
        visible: true,
      },
    });

    // Determine line color based on final PnL
    const finalPnL = data.data_points[data.data_points.length - 1]?.pnl ?? 0;
    const lineColor = finalPnL >= 0 ? '#10b981' : '#ef4444';

    const lineSeries = chart.addSeries(LineSeries, {
      color: lineColor,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      priceFormat: {
        type: 'custom',
        formatter: (price: number) => formatPnL(price),
      },
    });

    const lineData: LineData<Time>[] = data.data_points.map((point) => ({
      time: point.timestamp as Time,
      value: point.pnl,
    }));

    lineSeries.setData(lineData);
    chart.timeScale().fitContent();

    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

  const currentPnL = data?.total_pnl ?? data?.data_points?.[data.data_points.length - 1]?.pnl;
  const isPositive = (currentPnL ?? 0) >= 0;

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <span className={isPositive ? 'text-emerald-400' : 'text-red-400'}>
              {isPositive ? '\u25B2' : '\u25BC'}
            </span>
            Profit/Loss
          </div>
          <div className={`text-2xl font-bold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
            {currentPnL !== null && currentPnL !== undefined ? formatPnL(currentPnL) : '-'}
          </div>
          <div className="text-xs text-slate-500">{period === 'ALL' ? 'All-Time' : period}</div>
        </div>
        <div className="flex items-center gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                period === p
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-[200px]">
          <Spinner />
        </div>
      ) : data?.data_points?.length ? (
        <div ref={chartContainerRef} className="rounded-lg overflow-hidden" />
      ) : (
        <div className="flex justify-center items-center h-[200px] text-slate-400">
          No PnL history available
        </div>
      )}
    </div>
  );
}
