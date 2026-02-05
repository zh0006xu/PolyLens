import { useState, useMemo, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMarket } from '../hooks/useMarkets';
import { useMetrics } from '../hooks/useMetrics';
import { useWhales } from '../hooks/useWhales';
import { useKlines } from '../hooks/useKlines';
import { useMarketHolders } from '../hooks/useHolders';
import { useTheme } from '../contexts';
import { PriceBar } from '../components/market';
import { MetricsPanel } from '../components/metrics';
import { WhaleTable } from '../components/whale';
import { KlineChart } from '../components/chart/KlineChart';
import { Badge } from '../components/common';
import { Spinner } from '../components/common';
import { TraderLevelBadge, TRADER_LEVELS } from '../components/trader';
import { getMarketPrices, formatVolume, formatDate, parseOutcomeNames, truncateAddress, getResolvedOutcome } from '../utils/format';

export function MarketDetail() {
  const { marketId } = useParams<{ marketId: string }>();
  const id = marketId ? parseInt(marketId, 10) : undefined;
  const { resolvedTheme } = useTheme();
  const isLight = resolvedTheme === 'light';

  // Scroll to top when navigating to a new market
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [marketId]);

  const [selectedOutcomeIdx, setSelectedOutcomeIdx] = useState(0);
  const [period, setPeriod] = useState('24h');
  const [klineInterval, setKlineInterval] = useState('5m');
  const [whaleThreshold, setWhaleThreshold] = useState(1000);
  const [whaleLimit, setWhaleLimit] = useState(20);
  const holderLimit = 10;

  const { data: market, isLoading: marketLoading } = useMarket(id);
  const { data: holdersData, isLoading: holdersLoading } = useMarketHolders(id, holderLimit);

  // Parse outcome names from market data
  const outcomeNames = useMemo(() => {
    if (!market?.outcomes) return ['YES', 'NO'];
    return parseOutcomeNames(market.outcomes);
  }, [market?.outcomes]);

  // Compute selected outcome name based on current index
  const currentOutcomeName = selectedOutcomeIdx === 0 ? outcomeNames[0] : outcomeNames[1];
  const tokenId = selectedOutcomeIdx === 0 ? market?.yes_token_id : market?.no_token_id;

  const { data: metrics, isLoading: metricsLoading } = useMetrics(id, period, tokenId || undefined);
  const { data: whalesData, isLoading: whalesLoading } = useWhales(id, whaleLimit, whaleThreshold);
  const { data: klineData, isLoading: klinesLoading } = useKlines({
    market_id: id || 0,
    token_id: tokenId || undefined,
    interval: klineInterval,
    limit: 1000,
  });

  if (marketLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!market) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 text-lg">Market not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 mt-4 inline-block">
          Back to Markets
        </Link>
      </div>
    );
  }

  // Use latest trade prices if available, fallback to Gamma API prices
  const [currentPrice0, currentPrice1] = getMarketPrices(market);

  // Check if market is resolved
  const isResolved = market.status === 'resolved' || market.status === 'closed';
  const resolvedOutcome = getResolvedOutcome(market.status, market.outcome_prices, outcomeNames);

  // Polymarket URL - use event_slug if available, fallback to market slug
  const polymarketUrl = market.event_slug
    ? `https://polymarket.com/event/${market.event_slug}`
    : `https://polymarket.com/market/${market.slug}`;

  // Count of displayed whale trades
  const displayedWhaleCount = whalesData?.trades?.length || 0;
  const totalWhaleCount = whalesData?.total ?? displayedWhaleCount;
  const hasMoreWhales = whalesData?.total ? whalesData.total > whaleLimit : false;

  const handleLoadMoreWhales = () => {
    setWhaleLimit((prev) => prev + 20);
  };

  const getHolderName = (
    name?: string | null,
    pseudonym?: string | null,
    wallet?: string | null,
    displayPublic?: boolean | null
  ) => {
    if (pseudonym) return pseudonym;
    if (displayPublic && name) return name;
    return name || (wallet ? truncateAddress(wallet) : 'Unknown');
  };

  const getInitials = (label: string) => {
    const clean = label.replace(/[^a-zA-Z0-9 ]/g, '').trim();
    if (!clean) return '?';
    const parts = clean.split(' ').filter(Boolean);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          to="/"
          className="text-slate-400 hover:text-white p-2 -ml-2 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            {market.category && <Badge variant="info">{market.category}</Badge>}
            {market.status === 'active' ? (
              <Badge variant="success">Active</Badge>
            ) : (
              (() => {
                const resolved = getResolvedOutcome(market.status, market.outcome_prices, outcomeNames);
                if (resolved) {
                  return (
                    <Badge variant={resolved.winnerIndex === 0 ? 'success' : 'danger'}>
                      Resolved: {resolved.winner}
                    </Badge>
                  );
                }
                return <Badge variant="default">Resolved</Badge>;
              })()
            )}
            <a
              href={polymarketUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
            >
              View on Polymarket
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
          <h1 className="text-2xl font-bold text-white">{market.question || market.slug}</h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-slate-400">
            <span>Total Vol: ${formatVolume(market.volume || 0)}</span>
            {market.volume_24h && <span>24h: ${formatVolume(market.volume_24h)}</span>}
            {market.end_date && <span>Ends: {formatDate(market.end_date)}</span>}
            <span>{market.trade_count} trades</span>
          </div>
        </div>
      </div>

      {/* Price/Outcome Section */}
      <div className={`rounded-xl border p-6 ${isLight ? 'bg-white border-slate-200' : 'bg-slate-900 border-slate-800'}`}>
        {isResolved ? (
          /* Resolved Market - Show final outcome */
          <div className="text-center py-4">
            <div className="text-sm text-slate-400 mb-2">Final Outcome</div>
            <div className={`inline-flex items-center gap-3 px-8 py-4 rounded-xl text-2xl font-bold ${
              resolvedOutcome?.winnerIndex === 0
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : resolvedOutcome?.winnerIndex === 1
                  ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                  : 'bg-slate-700/50 text-slate-300 border border-slate-600'
            }`}>
              {resolvedOutcome?.winnerIndex === 0 && (
                <svg className="w-7 h-7" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              )}
              {resolvedOutcome?.winnerIndex === 1 && (
                <svg className="w-7 h-7" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              {resolvedOutcome ? resolvedOutcome.winner : 'Resolved'}
            </div>
          </div>
        ) : (
          /* Active Market - Show price selector */
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={() => setSelectedOutcomeIdx(0)}
                  className={`px-6 py-3 rounded-lg font-bold text-lg transition-colors ${selectedOutcomeIdx === 0
                      ? 'bg-emerald-500'
                      : isLight
                        ? 'bg-slate-100 hover:bg-slate-200'
                        : 'bg-slate-800 hover:bg-slate-700'
                    }`}
                >
                  <span className={selectedOutcomeIdx === 0 ? 'text-white' : isLight ? 'text-slate-400' : 'text-slate-300'}>
                    {outcomeNames[0]}
                  </span>
                  {' '}
                  <span className={selectedOutcomeIdx === 0 ? 'text-white/60' : isLight ? 'text-slate-500' : 'text-slate-500'}>
                    {(currentPrice0 * 100).toFixed(1)}¢
                  </span>
                </button>
                <button
                  onClick={() => setSelectedOutcomeIdx(1)}
                  className={`px-6 py-3 rounded-lg font-bold text-lg transition-colors ${selectedOutcomeIdx === 1
                      ? 'bg-red-400'
                      : isLight
                        ? 'bg-slate-100 hover:bg-slate-200'
                        : 'bg-slate-800 hover:bg-slate-700'
                    }`}
                >
                  <span className={selectedOutcomeIdx === 1 ? 'text-white' : isLight ? 'text-slate-400' : 'text-slate-300'}>
                    {outcomeNames[1]}
                  </span>
                  {' '}
                  <span className={selectedOutcomeIdx === 1 ? 'text-white/60' : isLight ? 'text-slate-500' : 'text-slate-500'}>
                    {(currentPrice1 * 100).toFixed(1)}¢
                  </span>
                </button>
              </div>
            </div>
            <PriceBar yesPrice={currentPrice0} noPrice={currentPrice1} height="lg" />
          </>
        )}
      </div>

      {/* Metrics Panel */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Market Metrics - <span className="text-indigo-400">{currentOutcomeName}</span>
        </h2>
        <MetricsPanel
          metrics={metrics}
          isLoading={metricsLoading}
          period={period}
          onPeriodChange={setPeriod}
        />
      </div>

      {/* K-line Chart */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">
            Price Chart - <span className="text-indigo-400">{currentOutcomeName}</span>
          </h2>
          <div className="flex items-center gap-2">
            {['1m', '5m', '15m', '1h', '4h', '1d'].map((interval) => (
              <button
                key={interval}
                onClick={() => setKlineInterval(interval)}
                className={`px-2 py-1 rounded text-xs font-medium transition-colors ${klineInterval === interval
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-white'
                  }`}
              >
                {interval}
              </button>
            ))}
          </div>
        </div>
        <KlineChart
          klines={klineData?.klines || []}
          vwap={klineData?.vwap}
          isLoading={klinesLoading}
          height={400}
        />
      </div>

      {/* Top Holders */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-white">Top Holders</h2>
            <div className="group relative inline-flex">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-slate-800 border border-slate-700 text-slate-300 cursor-help">
                Badge Levels
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </span>
              <div className="hidden group-hover:block absolute left-0 top-full mt-2 z-10 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 shadow-lg w-56">
                {[TRADER_LEVELS.whale, TRADER_LEVELS.shark, TRADER_LEVELS.dolphin, TRADER_LEVELS.fish].map((level) => (
                  <div key={level.level} className="flex items-start gap-2">
                    <span>{level.emoji}</span>
                    <span>
                      <span className="text-slate-100">{level.label}:</span> {level.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <span className="text-xs text-slate-500">Powered by Polymarket</span>
        </div>
        {holdersLoading ? (
          <div className="flex justify-center items-center py-6">
            <Spinner size="sm" />
          </div>
        ) : holdersData?.holders?.length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              {
                label: outcomeNames[0],
                color: 'text-emerald-400',
                border: 'border-emerald-600/40',
                holders: holdersData.yes_holders || [],
                price: currentPrice0,
              },
              {
                label: outcomeNames[1],
                color: 'text-red-400',
                border: 'border-red-600/40',
                holders: holdersData.no_holders || [],
                price: currentPrice1,
              },
            ].map(({ label, color, border, holders, price }) => {
              const columnHolders = holders;
              return (
                <div key={label} className={`rounded-lg border ${border} bg-slate-900/60 p-3`}>
                  <div className={`text-sm font-semibold ${color} mb-2`}>{label} Top Holders</div>
                  {columnHolders.length ? (
                    <div className={`divide-y ${isLight ? 'divide-slate-200' : 'divide-slate-800'}`}>
                      {columnHolders.map((holder, index) => {
                        const displayName = getHolderName(
                          holder.name,
                          holder.pseudonym,
                          holder.proxyWallet,
                          holder.displayUsernamePublic
                        );
                        return (
                          <div
                            key={`${holder.proxyWallet || 'holder'}-${label}-${index}`}
                            className="flex items-center justify-between py-3"
                          >
                            <div className="flex items-center gap-3">
                              <div className="w-8 text-slate-500 text-sm">#{index + 1}</div>
                              {holder.proxyWallet ? (
                                <Link
                                  to={`/trader/${holder.proxyWallet}`}
                                  className="flex items-center gap-3 hover:text-indigo-300 transition-colors"
                                >
                                  <div className="h-9 w-9 rounded-full bg-slate-800 border border-slate-700 overflow-hidden flex items-center justify-center text-xs text-slate-300">
                                    {holder.profileImage ? (
                                      <img
                                        src={holder.profileImage}
                                        alt={displayName}
                                        className="h-full w-full object-cover"
                                      />
                                    ) : (
                                      getInitials(displayName)
                                    )}
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-sm text-white font-medium">{displayName}</span>
                                      <TraderLevelBadge level={holder.whale_level} volume={(Number(holder.amount) || 0) * price} size="sm" />
                                    </div>
                                    <div className="text-xs text-slate-500">
                                      {truncateAddress(holder.proxyWallet)}
                                    </div>
                                  </div>
                                </Link>
                              ) : (
                                <>
                                  <div className="h-9 w-9 rounded-full bg-slate-800 border border-slate-700 overflow-hidden flex items-center justify-center text-xs text-slate-300">
                                    {holder.profileImage ? (
                                      <img
                                        src={holder.profileImage}
                                        alt={displayName}
                                        className="h-full w-full object-cover"
                                      />
                                    ) : (
                                      getInitials(displayName)
                                    )}
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-1.5">
                                      <span className="text-sm text-white font-medium">{displayName}</span>
                                      <TraderLevelBadge level={holder.whale_level} volume={(Number(holder.amount) || 0) * price} size="sm" />
                                    </div>
                                    <div className="text-xs text-slate-500">Wallet hidden</div>
                                  </div>
                                </>
                              )}
                            </div>
                            <div className="text-right">
                              <div className="text-sm text-white">{formatVolume(Number(holder.amount) || 0)}</div>
                              <div className="text-xs text-slate-500">shares</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">No holders for this outcome.</p>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-slate-400 text-sm">No holder data available.</p>
        )}
      </div>

      {/* Whale Trades */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
          <h2 className="text-lg font-semibold text-white">Whale Trades</h2>
          <div className="flex items-center gap-2">
            <span className="text-slate-400 text-sm">Min USD:</span>
            <select
              value={whaleThreshold}
              onChange={(e) => {
                setWhaleThreshold(Number(e.target.value));
                setWhaleLimit(20); // Reset limit when threshold changes
              }}
              className="bg-slate-800 border border-slate-700 text-white text-sm rounded px-3 py-1 focus:outline-none focus:border-indigo-500"
            >
              <option value={100}>$100</option>
              <option value={500}>$500</option>
              <option value={1000}>$1,000</option>
              <option value={5000}>$5,000</option>
              <option value={10000}>$10,000</option>
              <option value={50000}>$50,000</option>
            </select>
            <span className="text-slate-500 text-sm">({totalWhaleCount} trades)</span>
          </div>
        </div>
        <WhaleTable
          trades={whalesData?.trades || []}
          isLoading={whalesLoading}
          outcomeNames={outcomeNames}
        />
        {hasMoreWhales && (
          <div className="mt-4 text-center">
            <button
              onClick={handleLoadMoreWhales}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg text-sm transition-colors"
            >
              Load More
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
