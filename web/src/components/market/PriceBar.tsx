interface PriceBarProps {
  yesPrice: number;
  noPrice: number;
  showLabels?: boolean;
  height?: 'sm' | 'md' | 'lg';
}

export function PriceBar({ yesPrice, noPrice, showLabels = true, height = 'md' }: PriceBarProps) {
  // Display percentages (actual prices, may not sum to 100%)
  const yesPercent = Math.round(yesPrice * 100);
  const noPercent = Math.round(noPrice * 100);

  // Normalize bar widths so they always fill 100% (handles bid-ask spread)
  const total = yesPrice + noPrice;
  const yesBarWidth = total > 0 ? (yesPrice / total) * 100 : 50;
  const noBarWidth = total > 0 ? (noPrice / total) * 100 : 50;

  const heightClasses = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className="w-full">
      {showLabels && (
        <div className="flex justify-between text-sm mb-1">
          <span className="text-emerald-400 font-medium">YES {yesPercent}%</span>
          <span className="text-red-400 font-medium">NO {noPercent}%</span>
        </div>
      )}
      <div className={`w-full ${heightClasses[height]} bg-slate-700 rounded-full overflow-hidden flex`}>
        <div
          className="bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-300"
          style={{ width: `${yesBarWidth}%` }}
        />
        <div
          className="bg-gradient-to-r from-red-400 to-red-500 transition-all duration-300"
          style={{ width: `${noBarWidth}%` }}
        />
      </div>
    </div>
  );
}
