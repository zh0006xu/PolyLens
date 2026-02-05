import { Link } from 'react-router-dom';
import type { Market } from '../../types';
import { formatVolume, getMarketPrices, parseOutcomeNames, getResolvedOutcome } from '../../utils/format';
import { PriceBar } from './PriceBar';
import { Badge } from '../common/Badge';

interface MarketCardProps {
  market: Market;
}

export function MarketCard({ market }: MarketCardProps) {
  // Use latest trade prices if available, fallback to Gamma API prices
  const [yesPrice, noPrice] = getMarketPrices(market);
  const volume = market.volume || market.volume_24h || 0;
  const outcomeNames = parseOutcomeNames(market.outcomes);

  // Determine winning outcome for resolved markets
  const resolved = getResolvedOutcome(market.status, market.outcome_prices, outcomeNames);
  const isResolved = market.status === 'resolved' || market.status === 'closed';

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
            <Badge variant="default">Resolved</Badge>
          )}
        </div>

        {/* Question */}
        <h3 className="text-white font-medium text-sm leading-snug mb-3 line-clamp-2 min-h-[2.5rem]">
          {market.question || market.slug}
        </h3>

        {/* Price Bar or Resolved Outcome */}
        {isResolved ? (
          <div className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-semibold ${
            resolved?.winnerIndex === 0
              ? 'bg-emerald-500/20 text-emerald-400'
              : resolved?.winnerIndex === 1
                ? 'bg-red-500/20 text-red-400'
                : 'bg-slate-700/50 text-slate-300'
          }`}>
            {resolved?.winnerIndex === 0 && (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
            {resolved?.winnerIndex === 1 && (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            )}
            {resolved ? resolved.winner : 'Resolved'}
          </div>
        ) : (
          <PriceBar yesPrice={yesPrice} noPrice={noPrice} height="sm" />
        )}

        {/* Stats */}
        <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
          <span>Vol: ${formatVolume(volume)}</span>
          <span>{market.trade_count} trades</span>
        </div>
      </div>
    </Link>
  );
}
