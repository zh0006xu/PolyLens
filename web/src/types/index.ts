// Market types
export interface Market {
  id: number;
  slug: string;
  question: string | null;
  status: string | null;
  yes_token_id: string | null;
  no_token_id: string | null;
  outcomes: string | null;
  outcome_prices: string | null;
  trade_count: number;
  volume_24h: number;
  // Extended fields
  image: string | null;
  icon: string | null;
  category: string | null;
  end_date: string | null;
  volume: number;
  liquidity: number;
  best_bid: number | null;
  best_ask: number | null;
}

export interface MarketListResponse {
  markets: Market[];
  total: number;
  has_more: boolean;
}

// Category types
export interface Category {
  slug: string;
  name: string;
  count: number;
}

export interface CategoryListResponse {
  categories: Category[];
}

// Metric types
export interface BuySellRatio {
  buy_volume: number;
  sell_volume: number;
  buy_count: number;
  sell_count: number;
  ratio: number;
  buy_percentage: number;
}

export interface VWAP {
  vwap: number;
  total_volume: number;
  trade_count: number;
}

export interface WhaleSignal {
  whale_buy_volume: number;
  whale_sell_volume: number;
  whale_buy_count: number;
  whale_sell_count: number;
  signal: 'bullish' | 'bearish' | 'neutral';
  signal_strength: number;
}

export interface TraderStats {
  unique_traders: number;
  unique_buyers: number;
  unique_sellers: number;
  avg_trade_size: number;
}

export interface NetFlow {
  net_flow: number;
  inflow: number;
  outflow: number;
}

export interface Metrics {
  market_id: number;
  token_id: string | null;
  period: string;
  buy_sell_ratio: BuySellRatio;
  vwap: VWAP;
  whale_signal: WhaleSignal;
  trader_stats: TraderStats;
  net_flow: NetFlow;
}

// K-line types
export interface Kline {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface KlineResponse {
  klines: Kline[];
  vwap: number | null;
}

// Whale trade types
export interface WhaleTrade {
  id: number;
  tx_hash: string;
  log_index: number;
  market_id: number | null;
  trader: string;
  side: string;
  outcome: string;
  price: number;
  size: number;
  usd_value: number;
  block_number: number;
  timestamp: string;
  market_question?: string;
}

export interface WhaleListResponse {
  trades: WhaleTrade[];
  total: number;
}

// Price response
export interface PriceResponse {
  market_id: number;
  yes_price: number | null;
  no_price: number | null;
  yes_token_id: string | null;
  no_token_id: string | null;
}

// Holder types
export interface Holder {
  proxyWallet: string | null;
  pseudonym: string | null;
  amount: number;
  outcomeIndex: number | null;
  profileImage: string | null;
  name: string | null;
  displayUsernamePublic: boolean | null;
  whale_level?: string | null;
}

export interface MarketHoldersResponse {
  token: string | null;
  holders: Holder[];
  yes_holders: Holder[];
  no_holders: Holder[];
}

// Trader profile types
export interface TraderSummary {
  address: string;
  // Core stats from Polymarket APIs
  positions_value: number | null;
  predictions: number | null;
  pnl: number | null;
  biggest_win: number | null;
  win_rate: number | null;
  // Calculated stats
  trade_count: number | null;
  total_volume: number | null;
  first_trade: string | null;
  last_trade: string | null;
  active_days: number | null;
  whale_level: string | null;
  max_trade_value: number;
  max_market_volume: number;
  // Profile info
  display_username_public?: boolean | null;
  name?: string | null;
  pseudonym?: string | null;
  bio?: string | null;
  profile_image?: string | null;
  x_username?: string | null;
  verified_badge?: boolean | null;
  proxy_wallet?: string | null;
  data_partial?: boolean | null;
}

export interface TraderTrade {
  proxyWallet?: string | null;
  side?: string | null;
  asset?: string | null;
  conditionId?: string | null;
  size?: number | null;
  price?: number | null;
  timestamp?: number | null;
  title?: string | null;
  slug?: string | null;
  icon?: string | null;
  eventSlug?: string | null;
  outcome?: string | null;
  outcomeIndex?: number | null;
  name?: string | null;
  pseudonym?: string | null;
  bio?: string | null;
  profileImage?: string | null;
  profileImageOptimized?: string | null;
  transactionHash?: string | null;
  usdValue?: number | null;
}

export interface TraderTradeListResponse {
  trades: TraderTrade[];
  has_more: boolean;
  offset: number;
  limit: number;
}

export interface TraderPosition {
  proxyWallet?: string | null;
  asset?: string | null;
  conditionId?: string | null;
  size?: number | null;
  avgPrice?: number | null;
  initialValue?: number | null;
  currentValue?: number | null;
  cashPnl?: number | null;
  percentPnl?: number | null;
  totalBought?: number | null;
  realizedPnl?: number | null;
  percentRealizedPnl?: number | null;
  curPrice?: number | null;
  redeemable?: boolean | null;
  mergeable?: boolean | null;
  title?: string | null;
  slug?: string | null;
  icon?: string | null;
  eventSlug?: string | null;
  outcome?: string | null;
  outcomeIndex?: number | null;
  oppositeOutcome?: string | null;
  oppositeAsset?: string | null;
  endDate?: string | null;
  negativeRisk?: boolean | null;
}

export interface TraderPositionSummary {
  total_positions: number;
  total_value: number;
  total_unrealized_pnl: number;
}

export interface TraderPositionsResponse {
  positions: TraderPosition[];
  summary: TraderPositionSummary;
}

export interface TraderProfileStats {
  buy_count: number;
  sell_count: number;
  buy_volume: number;
  sell_volume: number;
  yes_preference: number;
  avg_trade_size: number;
  categories: Record<string, number>;
  hourly_distribution: number[];
}

export interface TraderLeaderboardEntry {
  rank?: string | null;
  proxyWallet?: string | null;
  userName?: string | null;
  vol?: number | null;
  pnl?: number | null;
  profileImage?: string | null;
  xUsername?: string | null;
  verifiedBadge?: boolean | null;
  whale_level?: string | null;
}

export interface TraderLeaderboardResponse {
  traders: TraderLeaderboardEntry[];
}

export interface TraderValueResponse {
  value: number | null;
}

// PnL History types
export interface PnLDataPoint {
  timestamp: number;
  pnl: number;
}

export interface PnLHistoryResponse {
  data_points: PnLDataPoint[];
  total_pnl: number | null;
  period: string;
}

// Query params
export type SortOption = 'volume_desc' | 'volume_asc' | 'trades_desc' | 'trades_asc' | 'newest' | 'ending_soon';

export interface MarketQueryParams {
  limit?: number;
  offset?: number;
  status?: string;
  category?: string;
  sort?: SortOption;
  search?: string;
}

export interface KlineQueryParams {
  market_id: number;
  token_id?: string;
  interval?: string;
  limit?: number;
}

export interface TradeQueryParams {
  limit?: number;
  offset?: number;
  market_id?: number;
  side?: string;
  start_time?: string;
  end_time?: string;
  min_usd?: number;
  max_usd?: number;
}
