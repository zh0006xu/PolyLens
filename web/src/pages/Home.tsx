import { useState, useMemo } from 'react';
import { useInfiniteMarkets } from '../hooks/useMarkets';
import { useCategories } from '../hooks/useCategories';
import { MarketGrid, MarketFilter } from '../components/market';
import type { SortOption } from '../types';

export function Home() {
  const [category, setCategory] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortOption>('volume_desc');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('active');
  const [hiddenCategories, setHiddenCategories] = useState<string[]>([]);

  const { data: categoriesData } = useCategories();
  const categories = categoriesData?.categories || [];

  const {
    data,
    isLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useInfiniteMarkets({
    limit: 20,
    category: category || undefined,
    sort: sortBy,
    search: search || undefined,
    status: status === 'all' ? undefined : status,
  });

  // Filter out hidden categories from markets
  const markets = useMemo(() => {
    const allMarkets = data?.pages.flatMap((page) => page.markets) || [];
    if (hiddenCategories.length === 0) {
      return allMarkets;
    }
    return allMarkets.filter((market) => {
      if (!market.category) return true;
      // Check if market's category matches any hidden category (case-insensitive)
      return !hiddenCategories.some(
        (hidden) => market.category?.toLowerCase().includes(hidden.toLowerCase())
      );
    });
  }, [data, hiddenCategories]);

  const total = data?.pages[0]?.total || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Markets</h1>
          <p className="text-slate-400 text-sm mt-1">
            {total.toLocaleString()} markets available
            {hiddenCategories.length > 0 && (
              <span className="ml-2 text-slate-500">
                (hiding: {hiddenCategories.join(', ')})
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Filters */}
      <MarketFilter
        categories={categories}
        selectedCategory={category}
        onCategoryChange={setCategory}
        sortBy={sortBy}
        onSortChange={setSortBy}
        searchQuery={search}
        onSearchChange={setSearch}
        status={status}
        onStatusChange={setStatus}
        hiddenCategories={hiddenCategories}
        onHiddenCategoriesChange={setHiddenCategories}
      />

      {/* Market Grid */}
      <MarketGrid
        markets={markets}
        isLoading={isLoading}
        hasMore={hasNextPage}
        onLoadMore={() => fetchNextPage()}
        loadingMore={isFetchingNextPage}
      />
    </div>
  );
}
