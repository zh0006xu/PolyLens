import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './contexts';
import { Layout } from './components/layout';
import { ScrollToTop } from './components/common';
import { Home } from './pages/Home';
import { MarketDetail } from './pages/MarketDetail';
import { TraderProfile } from './pages/TraderProfile';
import { TraderLeaderboard } from './pages/TraderLeaderboard';
import { Insights } from './pages/Insights';
import { WhaleAlertContainer } from './components/whale';
import { useWhaleWebSocket } from './hooks/useWebSocket';
import type { WhaleTrade } from './types';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      refetchOnWindowFocus: false,
    },
  },
});

function AppContent() {
  const [alerts, setAlerts] = useState<WhaleTrade[]>([]);

  const handleWhaleAlert = useCallback((trade: WhaleTrade) => {
    setAlerts((prev) => {
      // Keep only the last 3 alerts
      const newAlerts = [...prev, trade].slice(-3);
      return newAlerts;
    });
  }, []);

  const handleDismissAlert = useCallback((txHash: string, logIndex: number) => {
    setAlerts((prev) =>
      prev.filter((t) => !(t.tx_hash === txHash && t.log_index === logIndex))
    );
  }, []);

  useWhaleWebSocket({ onMessage: handleWhaleAlert });

  return (
    <>
      <BrowserRouter>
        <ScrollToTop />
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="market/:marketId" element={<MarketDetail />} />
            <Route path="trader/:address" element={<TraderProfile />} />
            <Route path="leaderboard" element={<TraderLeaderboard />} />
            <Route path="insights" element={<Insights />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <WhaleAlertContainer alerts={alerts} onDismiss={handleDismissAlert} />
    </>
  );
}

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
