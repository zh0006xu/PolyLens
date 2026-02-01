import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CandlestickSeries, LineSeries, createTextWatermark } from 'lightweight-charts';
import type {
  IChartApi,
  CandlestickData,
  Time,
  MouseEventParams,
  CustomData,
  ICustomSeriesPaneRenderer,
  ICustomSeriesPaneView,
  PaneRendererCustomData,
  CustomSeriesOptions,
  PriceToCoordinateConverter,
  CustomSeriesWhitespaceData,
} from 'lightweight-charts';
import type { CanvasRenderingTarget2D } from 'fancy-canvas';
import type { Kline } from '../../types';
import { Spinner } from '../common/Spinner';

interface KlineChartProps {
  klines: Kline[];
  vwap?: number | null;
  isLoading?: boolean;
  height?: number;
}

interface HoveredData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change: number;
  changePercent: number;
}

interface VolumeBarData extends CustomData<Time> {
  value: number;
  color?: string;
}

const BAR_SPACING_SPECIAL_CASE_FROM = 2.5;
const BAR_SPACING_SPECIAL_CASE_TO = 4;
const BAR_SPACING_SPECIAL_CASE_COEFF = 3;

const optimalCandlestickWidth = (barSpacing: number, pixelRatio: number) => {
  if (barSpacing >= BAR_SPACING_SPECIAL_CASE_FROM && barSpacing <= BAR_SPACING_SPECIAL_CASE_TO) {
    return Math.floor(BAR_SPACING_SPECIAL_CASE_COEFF * pixelRatio);
  }
  const barSpacingReducingCoeff = 0.2;
  const coeff =
    1 -
    (barSpacingReducingCoeff *
      Math.atan(Math.max(BAR_SPACING_SPECIAL_CASE_TO, barSpacing) - BAR_SPACING_SPECIAL_CASE_TO)) /
      (Math.PI * 0.5);
  const res = Math.floor(barSpacing * coeff * pixelRatio);
  const scaledBarSpacing = Math.floor(barSpacing * pixelRatio);
  const optimal = Math.min(res, scaledBarSpacing);
  return Math.max(Math.floor(pixelRatio), optimal);
};

class VolumeHistogramRenderer implements ICustomSeriesPaneRenderer {
  private data: PaneRendererCustomData<Time, VolumeBarData> | null = null;
  private options: CustomSeriesOptions | null = null;

  update(data: PaneRendererCustomData<Time, VolumeBarData>, options: CustomSeriesOptions) {
    this.data = data;
    this.options = options;
  }

  draw(
    target: CanvasRenderingTarget2D,
    priceConverter: PriceToCoordinateConverter,
    _isHovered: boolean,
  ) {
    if (!this.data || !this.data.visibleRange) return;

    const { bars, visibleRange, barSpacing, conflationFactor } = this.data;
    target.useBitmapCoordinateSpace(({ context, horizontalPixelRatio, verticalPixelRatio, bitmapSize }) => {
      const effectiveSpacing = barSpacing * conflationFactor;
      const barWidth = optimalCandlestickWidth(effectiveSpacing, horizontalPixelRatio);
      const halfWidth = Math.floor(barWidth / 2);

      const basePrice = 0;
      const baseCoordinate = priceConverter(basePrice);
      const baseY =
        baseCoordinate === null
          ? bitmapSize.height - 1
          : Math.round(baseCoordinate * verticalPixelRatio);

      for (let i = visibleRange.from; i < visibleRange.to; i++) {
        const bar = bars[i];
        const value = bar.originalData.value;
        const yCoordinate = priceConverter(value);
        if (yCoordinate === null) continue;

        const x = Math.round(bar.x * horizontalPixelRatio);
        const left = x - halfWidth;
        const right = left + barWidth - 1;
        const top = Math.min(Math.round(yCoordinate * verticalPixelRatio), baseY);
        const bottom = Math.max(Math.round(yCoordinate * verticalPixelRatio), baseY);

        context.fillStyle = bar.originalData.color || bar.barColor || this.options?.color || '#6366f1';
        context.fillRect(left, top, right - left + 1, bottom - top);
      }
    });
  }
}

class VolumeHistogramSeries implements ICustomSeriesPaneView<Time, VolumeBarData, CustomSeriesOptions> {
  private rendererInstance = new VolumeHistogramRenderer();

  renderer() {
    return this.rendererInstance;
  }

  update(data: PaneRendererCustomData<Time, VolumeBarData>, seriesOptions: CustomSeriesOptions) {
    this.rendererInstance.update(data, seriesOptions);
  }

  priceValueBuilder(plotRow: VolumeBarData) {
    // Include zero so the volume scale always has a baseline to draw from.
    return [0, plotRow.value];
  }

  isWhitespace(data: VolumeBarData | CustomSeriesWhitespaceData<Time>): data is CustomSeriesWhitespaceData<Time> {
    return (data as VolumeBarData).value === undefined;
  }

  defaultOptions(): CustomSeriesOptions {
    return {
      color: '#6366f1',
      lastValueVisible: false,
      priceLineVisible: false,
      title: '',
      visible: true,
      priceScaleId: 'right',
      autoscaleInfoProvider: undefined,
    } as CustomSeriesOptions;
  }
}

export function KlineChart({ klines, vwap, isLoading, height = 400 }: KlineChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const [hoveredData, setHoveredData] = useState<HoveredData | null>(null);
  const [maVisibility, setMaVisibility] = useState<Record<number, boolean>>({
    5: true,
    7: true,
    10: true,
  });

  const computeMA = (period: number, accessor: (k: Kline) => number) => {
    const data: { time: Time; value: number }[] = [];
    if (klines.length < period) return data;
    let sum = 0;
    for (let i = 0; i < klines.length; i += 1) {
      sum += accessor(klines[i]);
      if (i >= period) {
        sum -= accessor(klines[i - period]);
      }
      if (i >= period - 1) {
        data.push({
          time: klines[i].time as Time,
          value: sum / period,
        });
      }
    }
    return data;
  };

  const maConfigs = [
    { period: 5, color: '#ec4899' },
    { period: 7, color: '#60a5fa' },
    { period: 10, color: '#f59e0b' },
  ];

  // Create chart for price and volume
  useEffect(() => {
    if (!chartContainerRef.current || klines.length === 0) return;

    // Create kline lookup map
    const klineMap = new Map<number, Kline>();
    klines.forEach((k) => klineMap.set(k.time, k));

    const chartWidth = chartContainerRef.current.clientWidth;

    const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
    const computeBarSpacing = (width: number, count: number) => {
      if (count <= 1) return 120;
      const spacing = Math.floor(width / (count + 2));
      return clamp(spacing, 6, 120);
    };

    // Common timeScale options for consistent bar spacing
    const commonTimeScaleOptions = {
      borderColor: '#334155',
      barSpacing: computeBarSpacing(chartWidth, klines.length),
      minBarSpacing: 3,
      rightOffset: 0,
      fixLeftEdge: true,
      fixRightEdge: true,
    };

    // Common rightPriceScale options for alignment - use larger minimumWidth
    const commonPriceScaleOptions = {
      borderColor: '#334155',
      visible: true,
      autoScale: true,
      scaleMargins: {
        top: 0.1,
        bottom: 0.1,
      },
      minimumWidth: 80,
    };

    // ============ Single Chart (price + volume) ============
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#9ca3af',
        panes: {
          enableResize: false,
          separatorColor: 'transparent',
          separatorHoverColor: 'transparent',
        },
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      width: chartWidth,
      height,
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
          labelVisible: false,
        },
      },
      timeScale: {
        ...commonTimeScaleOptions,
        visible: true,
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: Time) => {
          const date = new Date((time as number) * 1000);
          const month = String(date.getMonth() + 1).padStart(2, '0');
          const day = String(date.getDate()).padStart(2, '0');
          const hours = String(date.getHours()).padStart(2, '0');
          const minutes = String(date.getMinutes()).padStart(2, '0');
          return `${month}/${day} ${hours}:${minutes}`;
        },
      },
      rightPriceScale: commonPriceScaleOptions,
    });

    const [pricePane] = chart.panes();
    const spacerPane = chart.addPane(true);
    const volumePane = chart.addPane(true);
    pricePane.setStretchFactor(3);
    spacerPane.setStretchFactor(0.25);
    volumePane.setStretchFactor(1);

    // Add candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderUpColor: '#10b981',
      borderDownColor: '#ef4444',
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: {
        type: 'price',
        precision: 4,
        minMove: 0.0001,
      },
    }, 0);

    // Add VWAP line
    const vwapLine = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 2,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      priceFormat: {
        type: 'price',
        precision: 4,
        minMove: 0.0001,
      },
      title: 'VWAP',
    }, 0);

    // Add MA lines
    const maDataByPeriod = new Map<number, Map<number, number>>();
    const maSeries = maConfigs.map((ma) => {
      const series = chart.addSeries(LineSeries, {
        color: ma.color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        priceFormat: {
          type: 'price',
          precision: 4,
          minMove: 0.0001,
        },
        title: '',
      }, 0);
      const maData = computeMA(ma.period, (k) => k.close);
      series.setData(maData);
      const lookup = new Map<number, number>();
      maData.forEach((point) => {
        lookup.set(point.time as number, point.value);
      });
      maDataByPeriod.set(ma.period, lookup);
      series.applyOptions({ visible: maVisibility[ma.period] ?? false });
      return series;
    });

    const maPriceLines = maSeries.map((series, index) => {
      const ma = maConfigs[index];
      return series.createPriceLine({
        price: 0,
        color: ma.color,
        lineVisible: false,
        axisLabelVisible: false,
        axisLabelColor: ma.color,
        axisLabelTextColor: '#0b1220',
        title: '',
      });
    });

    // Set price data
    const candleData: CandlestickData<Time>[] = klines.map((k) => ({
      time: k.time as Time,
      open: k.open,
      high: k.high,
      low: k.low,
      close: k.close,
    }));
    candleSeries.setData(candleData);
    chart.priceScale('right', 0).applyOptions({
      ...commonPriceScaleOptions,
      autoScale: true,
    });

    // Set VWAP data
    if (vwap !== null && vwap !== undefined) {
      const vwapData = klines.map((k) => ({
        time: k.time as Time,
        value: vwap,
      }));
      vwapLine.setData(vwapData);
    }

    // Add volume series (custom renderer to match candlestick width)
    const volumeSeries = chart.addCustomSeries(new VolumeHistogramSeries(), {
      color: '#6366f1',
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: {
        type: 'volume',
      },
    }, 2);

    // Set volume data
    const volumeData: VolumeBarData[] = klines.map((k) => ({
      time: k.time as Time,
      value: k.volume,
      color: k.close >= k.open ? '#10b981' : '#ef4444',
    }));
    volumeSeries.setData(volumeData);

    const volumeMaSeries = maConfigs.map((ma) => {
      const series = chart.addSeries(LineSeries, {
        color: ma.color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        title: '',
      }, 2);
      series.setData(computeMA(ma.period, (k) => k.volume));
      series.applyOptions({ visible: maVisibility[ma.period] ?? false });
      return series;
    });

    chart.priceScale('right', 2).applyOptions({
      ...commonPriceScaleOptions,
      autoScale: true,
    });

    createTextWatermark(volumePane, {
      visible: true,
      horzAlign: 'left',
      vertAlign: 'top',
      lines: [
        {
          text: 'Volume',
          color: '#64748b',
          fontSize: 12,
          fontFamily: 'inherit',
          fontStyle: '',
        },
      ],
    });

    const syncPriceScaleWidths = () => {
      const priceWidth = chart.priceScale('right', 0).width();
      const volumeWidth = chart.priceScale('right', 2).width();
      const targetWidth = Math.max(priceWidth, volumeWidth, commonPriceScaleOptions.minimumWidth);
      chart.priceScale('right', 0).applyOptions({ minimumWidth: targetWidth });
      chart.priceScale('right', 2).applyOptions({ minimumWidth: targetWidth });
    };

    chart.timeScale().fitContent();
    chart.timeScale().applyOptions(commonTimeScaleOptions);
    requestAnimationFrame(syncPriceScaleWidths);

    // Subscribe to crosshair move
    const handleCrosshairMove = (param: MouseEventParams) => {
      if (!param.time || !param.point) {
        setHoveredData(null);
        maPriceLines.forEach((line) => {
          line.applyOptions({ axisLabelVisible: false });
        });
        return;
      }

      const time = param.time as number;
      const kline = klineMap.get(time);

      if (kline) {
        const change = kline.close - kline.open;
        const changePercent = (change / kline.open) * 100;
        setHoveredData({
          time: kline.time,
          open: kline.open,
          high: kline.high,
          low: kline.low,
          close: kline.close,
          volume: kline.volume,
          change,
          changePercent,
        });
      }

      maPriceLines.forEach((line, index) => {
        const ma = maConfigs[index];
        const lookup = maDataByPeriod.get(ma.period);
        const value = lookup?.get(time);
        const visible = Boolean(value) && (maVisibility[ma.period] ?? false);
        if (visible && value !== undefined) {
          line.applyOptions({
            price: value,
            axisLabelVisible: true,
            axisLabelColor: ma.color,
            axisLabelTextColor: '#0b1220',
          });
        } else {
          line.applyOptions({ axisLabelVisible: false });
        }
      });
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);
    chartRef.current = chart;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        const width = chartContainerRef.current.clientWidth;
        const barSpacing = computeBarSpacing(width, klines.length);
        chartRef.current.applyOptions({ width });
        chartRef.current.timeScale().fitContent();
        chartRef.current.timeScale().applyOptions({ ...commonTimeScaleOptions, barSpacing });
        requestAnimationFrame(syncPriceScaleWidths);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      maSeries.forEach((series) => chart.removeSeries(series));
      maPriceLines.forEach((line, index) => {
        maSeries[index]?.removePriceLine(line);
      });
      volumeMaSeries.forEach((series) => chart.removeSeries(series));
      chart.remove();
      chartRef.current = null;
    };
  }, [height, klines, vwap, maVisibility]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center" style={{ height }}>
        <Spinner />
      </div>
    );
  }

  if (klines.length === 0) {
    return (
      <div className="flex justify-center items-center text-slate-400" style={{ height }}>
        No chart data available
      </div>
    );
  }

  // Format time for display
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };

  // Get the last kline for default display
  const lastKline = klines[klines.length - 1];
  const lastChange = lastKline.close - lastKline.open;
  const lastChangePercent = (lastChange / lastKline.open) * 100;

  // Use hovered data or last kline
  const displayData = hoveredData || {
    time: lastKline.time,
    open: lastKline.open,
    high: lastKline.high,
    low: lastKline.low,
    close: lastKline.close,
    volume: lastKline.volume,
    change: lastChange,
    changePercent: lastChangePercent,
  };

  const isHovering = hoveredData !== null;

  return (
    <div>
      {/* Stats row - updates on hover */}
      <div className="flex items-center gap-4 mb-4 text-sm flex-wrap">
        <div className="text-slate-400 text-xs min-w-[140px]">
          {isHovering ? '🔍 ' : '📊 Latest: '}
          {formatTime(displayData.time)}
        </div>
        <div>
          <span className="text-slate-400">O: </span>
          <span className="text-white font-mono">${displayData.open.toFixed(4)}</span>
        </div>
        <div>
          <span className="text-slate-400">H: </span>
          <span className="text-emerald-400 font-mono">${displayData.high.toFixed(4)}</span>
        </div>
        <div>
          <span className="text-slate-400">L: </span>
          <span className="text-red-400 font-mono">${displayData.low.toFixed(4)}</span>
        </div>
        <div>
          <span className="text-slate-400">C: </span>
          <span className="text-white font-mono">${displayData.close.toFixed(4)}</span>
        </div>
        <div>
          <span className="text-slate-400">Vol: </span>
          <span className="text-white font-mono">
            {displayData.volume.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </span>
        </div>
        {vwap && (
          <div>
            <span className="text-amber-400">VWAP: </span>
            <span className="text-white font-mono">${vwap.toFixed(4)}</span>
          </div>
        )}
        <div>
          <span className="text-slate-400">Chg: </span>
          <span className={displayData.change >= 0 ? 'text-emerald-400' : 'text-red-400'}>
            {displayData.change >= 0 ? '+' : ''}{displayData.changePercent.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* MA toggles */}
      <div className="flex items-center gap-2 mb-3 flex-wrap text-xs text-slate-400">
        <span className="text-slate-500">MA:</span>
        {maConfigs.map((ma) => (
          <button
            key={ma.period}
            type="button"
            onClick={() =>
              setMaVisibility((prev) => ({ ...prev, [ma.period]: !prev[ma.period] }))
            }
            className={`px-2 py-1 rounded border ${
              maVisibility[ma.period]
                ? 'border-slate-500 text-white'
                : 'border-slate-700 text-slate-500'
            }`}
            style={{ borderColor: ma.color }}
          >
            MA{ma.period}
          </button>
        ))}
      </div>

      {/* Price Chart */}
      <div className="mb-1">
        <div className="text-xs text-slate-500 mb-1">Price</div>
        <div ref={chartContainerRef} className="rounded-lg overflow-hidden" />
      </div>
      {/* Volume label is rendered inside the volume pane */}
    </div>
  );
}
