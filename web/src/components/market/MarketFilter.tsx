import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Category, SortOption } from '../../types';

interface MarketFilterProps {
  categories: Category[];
  selectedCategory: string | null;
  onCategoryChange: (category: string | null) => void;
  sortBy: SortOption;
  onSortChange: (sort: SortOption) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  // New filter props
  status?: string;
  onStatusChange?: (status: string) => void;
  hiddenCategories?: string[];
  onHiddenCategoriesChange?: (categories: string[]) => void;
}

export function MarketFilter({
  categories,
  selectedCategory,
  onCategoryChange,
  sortBy,
  onSortChange,
  searchQuery,
  onSearchChange,
  status = 'active',
  onStatusChange,
  hiddenCategories = [],
  onHiddenCategoriesChange,
}: MarketFilterProps) {
  const [localSearch, setLocalSearch] = useState(searchQuery);
  const [showFilters, setShowFilters] = useState(false);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const navigate = useNavigate();

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearchChange(localSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [localSearch, onSearchChange]);

  // Check scroll position
  const checkScrollPosition = () => {
    const container = scrollContainerRef.current;
    if (container) {
      setCanScrollLeft(container.scrollLeft > 0);
      setCanScrollRight(
        container.scrollLeft < container.scrollWidth - container.clientWidth - 1
      );
    }
  };

  useEffect(() => {
    checkScrollPosition();
    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('scroll', checkScrollPosition);
      window.addEventListener('resize', checkScrollPosition);
      return () => {
        container.removeEventListener('scroll', checkScrollPosition);
        window.removeEventListener('resize', checkScrollPosition);
      };
    }
  }, [categories]);

  const scroll = (direction: 'left' | 'right') => {
    const container = scrollContainerRef.current;
    if (container) {
      const scrollAmount = 200;
      container.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  const sortOptions: { value: SortOption; label: string }[] = [
    { value: 'volume_desc', label: '24hr Volume' },
    { value: 'volume_asc', label: 'Volume (Low)' },
    { value: 'trades_desc', label: 'Most Trades' },
    { value: 'newest', label: 'Newest' },
    { value: 'ending_soon', label: 'Ending Soon' },
  ];

  const statusOptions = [
    { value: 'active', label: 'Active' },
    { value: 'all', label: 'All' },
    { value: 'closed', label: 'Resolved' },
  ];

  // Categories to hide (common high-volume ones)
  const hideOptions = [
    { key: 'Sports', label: 'Hide sports?' },
    { key: 'Crypto', label: 'Hide crypto?' },
    { key: 'Earnings', label: 'Hide earnings?' },
  ];

  const toggleHideCategory = (cat: string) => {
    if (!onHiddenCategoriesChange) return;
    if (hiddenCategories.includes(cat)) {
      onHiddenCategoriesChange(hiddenCategories.filter((c) => c !== cat));
    } else {
      onHiddenCategoriesChange([...hiddenCategories, cat]);
    }
  };

  // Check if any filters are active
  const hasActiveFilters =
    sortBy !== 'volume_desc' ||
    status !== 'active' ||
    hiddenCategories.length > 0;

  const clearAllFilters = () => {
    onSortChange('volume_desc');
    onStatusChange?.('active');
    onHiddenCategoriesChange?.([]);
  };

  return (
    <div className="space-y-3">
      {/* Row 1: Search Bar */}
      <div className="relative">
        <input
          type="text"
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              const trimmed = localSearch.trim();
              if (/^0x[a-fA-F0-9]{40}$/.test(trimmed)) {
                navigate(`/trader/${trimmed}`);
              }
            }
          }}
          placeholder="Search markets or address..."
          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 pl-10 text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <svg
          className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        {localSearch && (
          <button
            type="button"
            onClick={() => setLocalSearch('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Row 2: Category tabs with scroll */}
      <div className="flex items-center gap-2">
        {/* Left scroll arrow */}
        <button
          type="button"
          onClick={() => scroll('left')}
          className={`flex-shrink-0 p-1.5 rounded-lg transition-colors ${
            canScrollLeft
              ? 'text-slate-400 hover:text-white hover:bg-slate-800'
              : 'text-slate-700 cursor-default'
          }`}
          disabled={!canScrollLeft}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Scrollable category container */}
        <div
          ref={scrollContainerRef}
          className="flex-1 flex items-center gap-2 overflow-x-auto scrollbar-hide"
        >
          {/* All button */}
          <button
            type="button"
            onClick={() => onCategoryChange(null)}
            className={`flex-shrink-0 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              selectedCategory === null
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
            }`}
          >
            All
          </button>

          {/* Category buttons */}
          {categories.map((category) => (
            <button
              key={category.slug}
              type="button"
              onClick={() => onCategoryChange(category.slug)}
              className={`flex-shrink-0 px-4 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                selectedCategory === category.slug
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              {category.name}
            </button>
          ))}
        </div>

        {/* Right scroll arrow */}
        <button
          type="button"
          onClick={() => scroll('right')}
          className={`flex-shrink-0 p-1.5 rounded-lg transition-colors ${
            canScrollRight
              ? 'text-slate-400 hover:text-white hover:bg-slate-800'
              : 'text-slate-700 cursor-default'
          }`}
          disabled={!canScrollRight}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* Settings button */}
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`flex-shrink-0 p-2 rounded-lg transition-colors ${
            showFilters || hasActiveFilters
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
            />
          </svg>
        </button>
      </div>

      {/* Row 3: Filters (collapsible) */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-3 py-2 px-1 bg-slate-900/50 rounded-lg">
          {/* Sort by */}
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-sm">Sort by</span>
            <select
              value={sortBy}
              onChange={(e) => onSortChange(e.target.value as SortOption)}
              className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-sm">Status:</span>
            <select
              value={status}
              onChange={(e) => onStatusChange?.(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-indigo-500 cursor-pointer"
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Divider */}
          <div className="h-6 w-px bg-slate-700" />

          {/* Hide checkboxes */}
          {hideOptions.map((option) => (
            <label
              key={option.key}
              className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer hover:text-white transition-colors"
            >
              <input
                type="checkbox"
                checked={hiddenCategories.includes(option.key)}
                onChange={() => toggleHideCategory(option.key)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0 cursor-pointer"
              />
              {option.label}
            </label>
          ))}

          {/* Divider */}
          <div className="h-6 w-px bg-slate-700" />

          {/* Clear Filters */}
          <button
            type="button"
            onClick={clearAllFilters}
            disabled={!hasActiveFilters}
            className={`text-sm px-3 py-1.5 rounded-lg transition-colors ${
              hasActiveFilters
                ? 'text-red-400 hover:text-red-300 hover:bg-slate-800'
                : 'text-slate-600 cursor-not-allowed'
            }`}
          >
            Clear filters
          </button>
        </div>
      )}
    </div>
  );
}
