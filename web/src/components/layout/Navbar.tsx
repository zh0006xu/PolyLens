import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useTheme, type ThemeMode } from '../../contexts';
import { fetchTraderLeaderboard } from '../../api/trader';

function SunIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

function SystemIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

function ThemeToggle() {
  const { mode, setMode } = useTheme();

  const modes: { value: ThemeMode; icon: typeof SunIcon; label: string }[] = [
    { value: 'light', icon: SunIcon, label: 'Light' },
    { value: 'dark', icon: MoonIcon, label: 'Dark' },
    { value: 'system', icon: SystemIcon, label: 'System' },
  ];

  return (
    <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
      {modes.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setMode(value)}
          className={`p-1.5 rounded-md transition-colors ${
            mode === value
              ? 'bg-indigo-600 text-white'
              : 'text-slate-400 hover:text-white'
          }`}
          title={label}
          aria-label={`Switch to ${label} mode`}
        >
          <Icon className="w-4 h-4" />
        </button>
      ))}
    </div>
  );
}

export function Navbar() {
  const { resolvedTheme } = useTheme();
  const queryClient = useQueryClient();
  const isLight = resolvedTheme === 'light';

  // Prefetch leaderboard data on hover
  const handleLeaderboardHover = () => {
    queryClient.prefetchQuery({
      queryKey: ['trader', 'leaderboard', 'PNL', 'DAY', 'OVERALL', 25, 0],
      queryFn: () => fetchTraderLeaderboard('PNL', 25, 0, 'DAY', 'OVERALL'),
      staleTime: 30 * 1000,
    });
  };

  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo - switches based on theme */}
          <Link to="/" className="flex items-center gap-2">
            <img
              src={isLight ? "/logo-light.png" : "/logo.png"}
              alt="PolyLens"
              className="h-8"
            />
            <span className="text-white font-semibold text-lg tracking-wide">PolyLens</span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Markets
            </Link>
            <Link
              to="/leaderboard"
              className="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
              onMouseEnter={handleLeaderboardHover}
            >
              Leaderboard
            </Link>
            <Link
              to="/insights"
              className="text-slate-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Insights
            </Link>
            <a
              href="https://polymarket.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors inline-flex items-center gap-1"
            >
              Polymarket
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>

            {/* Theme Toggle */}
            <ThemeToggle />
          </div>
        </div>
      </div>
    </nav>
  );
}
