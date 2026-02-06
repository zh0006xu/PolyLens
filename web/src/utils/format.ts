/**
 * Format a number as volume (e.g., 1.2M, 350K)
 */
export function formatVolume(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toFixed(0);
}

/**
 * Format a number as USD currency
 */
export function formatUSD(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format a price as percentage (0-100)
 */
export function formatPrice(price: number | null): string {
  if (price === null) return '-';
  return `${(price * 100).toFixed(0)}%`;
}

/**
 * Format a price as cents
 */
export function formatPriceCents(price: number | null): string {
  if (price === null) return '-';
  return `$${price.toFixed(2)}`;
}

/**
 * Format a date string
 */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date);
}

/**
 * Format a timestamp as relative time
 */
export function formatRelativeTime(timestamp: string | number): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHours = Math.floor(diffMin / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(date.toISOString());
}

/**
 * Truncate an address (0x1234...5678)
 */
export function truncateAddress(address: string, chars: number = 4): string {
  if (!address) return '';
  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`;
}

/**
 * Truncate a transaction hash
 */
export function truncateTxHash(hash: string, chars: number = 6): string {
  if (!hash) return '';
  return `${hash.slice(0, chars + 2)}...${hash.slice(-chars)}`;
}

/**
 * Parse outcome prices from JSON string
 */
export function parseOutcomePrices(pricesStr: string | null): [number, number] {
  if (!pricesStr) return [0.5, 0.5];
  try {
    const prices = JSON.parse(pricesStr);
    if (Array.isArray(prices) && prices.length >= 2) {
      return [parseFloat(prices[0]) || 0.5, parseFloat(prices[1]) || 0.5];
    }
  } catch {
    // ignore parse errors
  }
  return [0.5, 0.5];
}

/**
 * Get best available prices for a market
 * Priority: best_ask (order book) > latest trade prices > outcome_prices (Gamma API)
 *
 * Polymarket displays "buy" prices:
 * - YES price = best_ask (price to buy YES)
 * - NO price = 1 - best_bid (price to buy NO, since buying NO = selling YES)
 */
export function getMarketPrices(market: {
  outcome_prices?: string | null;
  latest_yes_price?: number | null;
  latest_no_price?: number | null;
  best_bid?: number | null;
  best_ask?: number | null;
}): [number, number] {
  // Prefer order book prices (best_ask for YES, 1-best_bid for NO)
  if (
    market.best_ask != null &&
    market.best_bid != null &&
    market.best_ask > 0 &&
    market.best_bid > 0
  ) {
    return [market.best_ask, 1 - market.best_bid];
  }
  // Fall back to latest trade prices
  if (
    market.latest_yes_price != null &&
    market.latest_no_price != null &&
    market.latest_yes_price > 0 &&
    market.latest_no_price > 0
  ) {
    return [market.latest_yes_price, market.latest_no_price];
  }
  // Fall back to outcome_prices from Gamma API
  return parseOutcomePrices(market.outcome_prices ?? null);
}

/**
 * Get sell prices for a market
 * - Sell YES price = best_bid (price you receive when selling YES)
 * - Sell NO price = 1 - best_ask (price you receive when selling NO)
 */
export function getMarketSellPrices(market: {
  outcome_prices?: string | null;
  latest_yes_price?: number | null;
  latest_no_price?: number | null;
  best_bid?: number | null;
  best_ask?: number | null;
}): [number, number] {
  // Prefer order book prices (best_bid for YES, 1-best_ask for NO)
  if (
    market.best_ask != null &&
    market.best_bid != null &&
    market.best_ask > 0 &&
    market.best_bid > 0
  ) {
    return [market.best_bid, 1 - market.best_ask];
  }
  // Fall back to latest trade prices (same as buy for fallback)
  if (
    market.latest_yes_price != null &&
    market.latest_no_price != null &&
    market.latest_yes_price > 0 &&
    market.latest_no_price > 0
  ) {
    return [market.latest_yes_price, market.latest_no_price];
  }
  // Fall back to outcome_prices from Gamma API
  return parseOutcomePrices(market.outcome_prices ?? null);
}

/**
 * Parse outcome names from JSON string
 * Returns array of outcome names, e.g., ["Clippers", "Nuggets"] or ["Yes", "No"]
 */
export function parseOutcomeNames(outcomesStr: string | null): string[] {
  if (!outcomesStr) return ['YES', 'NO'];
  try {
    const outcomes = JSON.parse(outcomesStr);
    if (Array.isArray(outcomes) && outcomes.length >= 2) {
      return outcomes.map(String);
    }
  } catch {
    // ignore parse errors
  }
  return ['YES', 'NO'];
}

/**
 * Get the resolved outcome for a closed market
 * Returns the winning outcome name or null if not resolved
 */
export function getResolvedOutcome(
  status: string | null,
  outcomePrices: string | null,
  outcomeNames: string[] = ['YES', 'NO']
): { winner: string; winnerIndex: number } | null {
  if (!status || (status !== 'closed' && status !== 'resolved')) return null;

  const [price0, price1] = parseOutcomePrices(outcomePrices);

  // Price >= 0.95 indicates the winning outcome
  if (price0 >= 0.95) {
    return { winner: outcomeNames[0] || 'YES', winnerIndex: 0 };
  }
  if (price1 >= 0.95) {
    return { winner: outcomeNames[1] || 'NO', winnerIndex: 1 };
  }

  return null;
}
