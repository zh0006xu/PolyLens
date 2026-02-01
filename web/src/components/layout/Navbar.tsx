import { Link } from 'react-router-dom';

export function Navbar() {
  return (
    <nav className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <img src="/logo.png" alt="PolyLens" className="h-8" />
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
            >
              Leaderboard
            </Link>
            <a
              href="https://polymarket.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Polymarket ↗
            </a>
          </div>
        </div>
      </div>
    </nav>
  );
}
