import { Link } from 'react-router-dom';
import { truncateAddress } from '../../utils/format';
import { TraderLevelBadge } from './TraderLevelBadge';

interface TraderHeaderProps {
  address: string;
  whaleLevel?: string | null;
  totalVolume?: number | null;
  displayUsernamePublic?: boolean | null;
  name?: string | null;
  pseudonym?: string | null;
  profileImage?: string | null;
  xUsername?: string | null;
  verifiedBadge?: boolean | null;
}

export function TraderHeader({
  address,
  whaleLevel = 'fish',
  totalVolume,
  displayUsernamePublic,
  name,
  pseudonym,
  profileImage,
  xUsername,
  verifiedBadge,
}: TraderHeaderProps) {
  const canShowUsername = displayUsernamePublic && !!name;
  const polymarketUrl = `https://polymarket.com/profile/${address}`;

  return (
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
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-slate-800 border border-slate-700 overflow-hidden flex items-center justify-center text-xs text-slate-300">
              {profileImage ? (
                <img src={profileImage} alt={name || pseudonym || address} className="h-full w-full object-cover" />
              ) : (
                (name || pseudonym || truncateAddress(address)).slice(0, 2).toUpperCase()
              )}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">
                {canShowUsername ? name : truncateAddress(address)}
              </h1>
              {canShowUsername && (xUsername || verifiedBadge) && (
                <div className="text-xs text-slate-500 flex items-center gap-2">
                  {xUsername && <span>@{xUsername}</span>}
                  {verifiedBadge && <span className="text-emerald-400">Verified</span>}
                </div>
              )}
            </div>
          </div>
          <button
            onClick={() => navigator.clipboard.writeText(address)}
            className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 group relative"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span className="hidden group-hover:block absolute left-1/2 -translate-x-1/2 top-full mt-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-300 whitespace-nowrap z-10">
              Copy address
            </span>
          </button>
          <a
            href={`https://polygonscan.com/address/${address}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            View on Polygonscan
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
          <a
            href={polymarketUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            View on Polymarket
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        <TraderLevelBadge level={whaleLevel} volume={totalVolume} />
      </div>
    </div>
  );
}
