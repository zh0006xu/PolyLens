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
