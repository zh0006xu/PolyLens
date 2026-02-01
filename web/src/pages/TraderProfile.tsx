import { useParams, Link } from 'react-router-dom';
import { TraderHeader, TraderStats, TraderHistory, TraderPositions, TraderPatterns } from '../components/trader';
import { Spinner } from '../components/common';
import { useTraderSummary } from '../hooks/useTrader';

export function TraderProfile() {
  const { address } = useParams<{ address: string }>();
  const { data: summary, isLoading } = useTraderSummary(address);

  if (!address || !/^0x[a-fA-F0-9]{40}$/.test(address)) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 text-lg">Invalid wallet address</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 mt-4 inline-block">
          Back to Markets
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-400 text-lg">Trader not found</p>
        <Link to="/" className="text-indigo-400 hover:text-indigo-300 mt-4 inline-block">
          Back to Markets
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <TraderHeader
        address={address}
        whaleLevel={summary.whale_level}
        totalVolume={summary.total_volume}
        displayUsernamePublic={summary.display_username_public}
        name={summary.name}
        pseudonym={summary.pseudonym}
        profileImage={summary.profile_image}
        xUsername={summary.x_username}
        verifiedBadge={summary.verified_badge}
      />

      <TraderStats summary={summary} />

      <TraderPositions address={address} />
      <TraderPatterns address={address} />
      <TraderHistory address={address} />
    </div>
  );
}
