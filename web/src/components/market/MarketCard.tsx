import { Link } from 'react-router-dom';
import type { Market } from '../../types';
import { formatVolume, parseOutcomePrices } from '../../utils/format';
import { PriceBar } from './PriceBar';
import { Badge } from '../common/Badge';

interface MarketCardProps {
  market: Market;
}

export function MarketCard({ market }: MarketCardProps) {
  const [yesPrice, noPrice] = parseOutcomePrices(market.outcome_prices);
  const volume = market.volume || market.volume_24h || 0;

  // Check if market is resolved (status can be 'resolved' or 'closed')
  const isResolved = market.status === 'resolved' || market.status === 'closed';

  // Determine winning outcome for resolved markets
  const getResolvedOutcome = () => {
    if (!isResolved) return null;
    // If YES price is >= 0.95, YES won; if NO price is >= 0.95, NO won
    if (yesPrice >= 0.95) return 'YES';
    if (noPrice >= 0.95) return 'NO';
    return null;
  };
  const resolvedOutcome = getResolvedOutcome();

  return (
    <Link
      to={`/market/${market.id}`}
      className="block bg-slate-900 rounded-xl border border-slate-800 hover:border-slate-700 transition-all duration-200 overflow-hidden group"
    >
      {/* Image */}
      {market.image && (
        <div className="aspect-video w-full overflow-hidden bg-slate-800">
          <img
            src={market.image}
            alt={market.question || 'Market'}
            loading="lazy"
            decoding="async"
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
        </div>
      )}

      <div className="p-4">
        {/* Category & Status badges */}
        <div className="flex items-center gap-2 mb-2">
          {market.category && (
            <Badge variant="info">{market.category}</Badge>
          )}
          {market.status === 'active' && (
            <Badge variant="success">Active</Badge>
          )}
          {isResolved && (
            <Badge variant={resolvedOutcome === 'YES' ? 'success' : resolvedOutcome === 'NO' ? 'danger' : 'default'}>
              {resolvedOutcome ? `Resolved: ${resolvedOutcome}` : 'Resolved'}
            </Badge>
          )}
        </div>

        {/* Question */}
        <h3 className="text-white font-medium text-sm leading-snug mb-3 line-clamp-2 min-h-[2.5rem]">
          {market.question || market.slug}
        </h3>

        {/* Price Bar */}
        <PriceBar yesPrice={yesPrice} noPrice={noPrice} height="sm" />

        {/* Stats */}
        <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
          <span>Vol: ${formatVolume(volume)}</span>
          <span>{market.trade_count} trades</span>
        </div>
      </div>
    </Link>
  );
}
