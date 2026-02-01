import { useEffect, useRef } from 'react';
import type { Market } from '../../types';
import { MarketCard } from './MarketCard';
import { Spinner } from '../common/Spinner';

interface MarketGridProps {
  markets: Market[];
  isLoading?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadingMore?: boolean;
}

export function MarketGrid({
  markets,
  isLoading,
  hasMore,
  onLoadMore,
  loadingMore,
}: MarketGridProps) {
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Infinite scroll: auto-load when sentinel element is visible
  useEffect(() => {
    if (!hasMore || !onLoadMore || loadingMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          onLoadMore();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    const sentinel = loadMoreRef.current;
    if (sentinel) {
      observer.observe(sentinel);
    }

    return () => {
      if (sentinel) {
        observer.unobserve(sentinel);
      }
    };
  }, [hasMore, onLoadMore, loadingMore]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (markets.length === 0) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 text-lg">No markets found</p>
      </div>
    );
  }

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {markets.map((market) => (
          <MarketCard key={market.id} market={market} />
        ))}
      </div>

      {/* Sentinel element for infinite scroll */}
      {hasMore && (
        <div ref={loadMoreRef} className="flex justify-center mt-8 py-4">
          {loadingMore && (
            <div className="flex items-center gap-2 text-slate-400">
              <Spinner size="sm" />
              Loading more...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
