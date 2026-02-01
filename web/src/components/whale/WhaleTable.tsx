import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import type { WhaleTrade } from '../../types';
import { formatUSD, formatRelativeTime, truncateAddress, truncateTxHash } from '../../utils/format';
import { Badge } from '../common/Badge';
import { Spinner } from '../common/Spinner';

// Whale level based on single trade value
function getWhaleBadge(usdValue: number): { emoji: string; level: string } | null {
  if (usdValue >= 100000) return { emoji: '🐋', level: 'Whale' };
  if (usdValue >= 50000) return { emoji: '🦈', level: 'Shark' };
  if (usdValue >= 10000) return { emoji: '🐬', level: 'Dolphin' };
  if (usdValue >= 5000) return { emoji: '🐟', level: 'Fish' };
  return null;
}

type SortField = 'timestamp' | 'usd_value' | 'price' | 'size';
type SortDirection = 'asc' | 'desc';

interface WhaleTableProps {
  trades: WhaleTrade[];
  isLoading?: boolean;
  showMarket?: boolean;
  outcomeNames?: string[];
}

export function WhaleTable({ trades, isLoading, showMarket = false, outcomeNames }: WhaleTableProps) {
  const [sortField, setSortField] = useState<SortField>('timestamp');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const sortedTrades = useMemo(() => {
    return [...trades].sort((a, b) => {
      let aVal: number;
      let bVal: number;

      switch (sortField) {
        case 'timestamp':
          aVal = new Date(a.timestamp).getTime();
          bVal = new Date(b.timestamp).getTime();
          break;
        case 'usd_value':
          aVal = a.usd_value;
          bVal = b.usd_value;
          break;
        case 'price':
          aVal = a.price;
          bVal = b.price;
          break;
        case 'size':
          aVal = a.size;
          bVal = b.size;
          break;
        default:
          return 0;
      }

      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [trades, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      // Inactive: show both up and down chevrons stacked
      return (
        <svg className="w-3 h-3 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l4-4 4 4M8 15l4 4 4-4" />
        </svg>
      );
    }
    // Active: show single chevron for current direction
    return sortDirection === 'desc' ? (
      <svg className="w-3 h-3 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    ) : (
      <svg className="w-3 h-3 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      </svg>
    );
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className="text-center text-slate-400 py-8">
        No whale trades found
      </div>
    );
  }

  const getOutcomeDisplay = (outcome: string) => {
    if (!outcomeNames || outcomeNames.length < 2) {
      return outcome;
    }
    if (outcome === 'YES' || outcome === outcomeNames[0]) {
      return outcomeNames[0];
    }
    if (outcome === 'NO' || outcome === outcomeNames[1]) {
      return outcomeNames[1];
    }
    return outcome;
  };

  const formatTxHash = (hash: string) => {
    if (!hash) return '';
    return hash.startsWith('0x') ? hash : `0x${hash}`;
  };

  const SortableHeader = ({ field, children, align = 'left' }: { field: SortField; children: React.ReactNode; align?: 'left' | 'right' }) => (
    <th
      className={`text-${align} py-3 px-4 cursor-pointer hover:text-slate-200 transition-colors`}
      onClick={() => handleSort(field)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : ''}`}>
        {children}
        <SortIcon field={field} />
      </div>
    </th>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-400 text-xs uppercase tracking-wide border-b border-slate-800">
            <SortableHeader field="timestamp">Time</SortableHeader>
            <th className="text-left py-3 px-4">Trader</th>
            <th className="text-left py-3 px-4">Side</th>
            <th className="text-left py-3 px-4">Outcome</th>
            <SortableHeader field="price" align="right">Price</SortableHeader>
            <SortableHeader field="size" align="right">Size</SortableHeader>
            <SortableHeader field="usd_value" align="right">Value</SortableHeader>
            <th className="text-left py-3 px-4">Tx</th>
            {showMarket && <th className="text-left py-3 px-4">Market</th>}
          </tr>
        </thead>
        <tbody>
          {sortedTrades.map((trade) => {
            const displayOutcome = getOutcomeDisplay(trade.outcome);
            const isFirstOutcome = trade.outcome === 'YES' || trade.outcome === outcomeNames?.[0];
            const txHash = formatTxHash(trade.tx_hash);

            return (
              <tr
                key={`${trade.tx_hash}-${trade.log_index}`}
                className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                <td className="py-3 px-4 text-slate-400">
                  {formatRelativeTime(trade.timestamp)}
                </td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {(() => {
                      const badge = getWhaleBadge(trade.usd_value);
                      return badge ? (
                        <span title={badge.level} className="text-sm">
                          {badge.emoji}
                        </span>
                      ) : null;
                    })()}
                    <Link
                      to={`/trader/${trade.trader}`}
                      className="text-indigo-400 hover:text-indigo-300 font-mono"
                    >
                      {truncateAddress(trade.trader)}
                    </Link>
                    <a
                      href={`https://polygonscan.com/address/${trade.trader}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-500 hover:text-slate-300"
                      title="View on Polygonscan"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                    {trade.side}
                  </Badge>
                </td>
                <td className="py-3 px-4">
                  <Badge variant={isFirstOutcome ? 'success' : 'danger'}>
                    {displayOutcome}
                  </Badge>
                </td>
                <td className="py-3 px-4 text-right text-white font-mono">
                  ${trade.price.toFixed(2)}
                </td>
                <td className="py-3 px-4 text-right text-slate-300 font-mono">
                  {trade.size.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </td>
                <td className="py-3 px-4 text-right text-white font-bold">
                  {formatUSD(trade.usd_value)}
                </td>
                <td className="py-3 px-4">
                  <a
                    href={`https://polygonscan.com/tx/${txHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-400 hover:text-indigo-400 font-mono"
                  >
                    {truncateTxHash(trade.tx_hash)}
                  </a>
                </td>
                {showMarket && (
                  <td className="py-3 px-4 text-slate-300 max-w-xs truncate">
                    {trade.market_question || '-'}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
