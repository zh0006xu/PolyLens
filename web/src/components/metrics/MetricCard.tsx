import { useState } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  tooltip?: {
    formula: string;
    meaning: string;
  };
}

export function MetricCard({ title, value, subtitle, trend, icon, tooltip }: MetricCardProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  const trendColors = {
    up: 'text-emerald-400',
    down: 'text-red-400',
    neutral: 'text-slate-400',
  };

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 relative">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-1 mb-1">
            <p className="text-slate-400 text-xs uppercase tracking-wide">{title}</p>
            {tooltip && (
              <div
                className="relative"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
              >
                <span className="info-tooltip-trigger w-3.5 h-3.5 rounded-full bg-slate-600 text-slate-300 text-[10px] flex items-center justify-center cursor-pointer hover:bg-slate-500">
                  !
                </span>
                {showTooltip && (
                  <div className="info-tooltip-content absolute z-50 bottom-full left-0 mb-2 w-64 p-3 bg-slate-700 text-slate-200 text-xs rounded-lg shadow-lg text-left normal-case font-normal">
                    <div className="text-slate-300 mb-2">{tooltip.formula}</div>
                    <div className="text-slate-300">{tooltip.meaning}</div>
                    <div className="absolute top-full left-4 border-4 border-transparent border-t-slate-700" />
                  </div>
                )}
              </div>
            )}
          </div>
          <p className={`text-xl font-bold ${trend ? trendColors[trend] : 'text-white'}`}>
            {value}
          </p>
          {subtitle && (
            <p className="text-slate-500 text-xs mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="text-slate-500 ml-2">{icon}</div>
        )}
      </div>
    </div>
  );
}
