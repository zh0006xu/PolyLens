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
                <svg
                  className="w-3 h-3 text-slate-500 hover:text-slate-300 cursor-help"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {showTooltip && (
                  <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-slate-700 text-slate-200 text-xs rounded-lg shadow-lg">
                    <div className="font-semibold text-white mb-1">Formula:</div>
                    <div className="text-slate-300 mb-2">{tooltip.formula}</div>
                    <div className="font-semibold text-white mb-1">Meaning:</div>
                    <div className="text-slate-300">{tooltip.meaning}</div>
                    <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-700" />
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
