import { useEffect, useState } from 'react';
import type { WhaleTrade } from '../../types';
import { formatUSD, truncateAddress } from '../../utils/format';
import { Badge } from '../common/Badge';

interface WhaleAlertProps {
  trade: WhaleTrade;
  onClose: () => void;
  duration?: number;
}

export function WhaleAlert({ trade, onClose, duration = 5000 }: WhaleAlertProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Animate in
    requestAnimationFrame(() => {
      setIsVisible(true);
    });

    // Auto close
    const timer = setTimeout(() => {
      setIsLeaving(true);
      setTimeout(onClose, 300);
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 transition-all duration-300 transform ${
        isVisible && !isLeaving
          ? 'translate-x-0 opacity-100'
          : 'translate-x-full opacity-0'
      }`}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-xl p-4 max-w-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🐋</span>
              <span className="font-semibold text-white">Whale Alert!</span>
              <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
                {trade.side}
              </Badge>
              <Badge variant={trade.outcome === 'YES' ? 'success' : 'danger'}>
                {trade.outcome}
              </Badge>
            </div>
            <p className="text-slate-300 text-sm">
              <span className="text-indigo-400 font-mono">{truncateAddress(trade.trader)}</span>
              {' '}placed a{' '}
              <span className="text-white font-bold">{formatUSD(trade.usd_value)}</span>
              {' '}trade
            </p>
            {trade.market_question && (
              <p className="text-slate-400 text-xs mt-1 line-clamp-1">
                {trade.market_question}
              </p>
            )}
          </div>
          <button
            onClick={() => {
              setIsLeaving(true);
              setTimeout(onClose, 300);
            }}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

// Container to manage multiple alerts
interface WhaleAlertContainerProps {
  alerts: WhaleTrade[];
  onDismiss: (txHash: string, logIndex: number) => void;
}

export function WhaleAlertContainer({ alerts, onDismiss }: WhaleAlertContainerProps) {
  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {alerts.map((trade) => (
        <WhaleAlert
          key={`${trade.tx_hash}-${trade.log_index}`}
          trade={trade}
          onClose={() => onDismiss(trade.tx_hash, trade.log_index)}
        />
      ))}
    </div>
  );
}
