import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export function TraderSearch() {
  const [value, setValue] = useState('');
  const navigate = useNavigate();

  const isValidAddress = /^0x[a-fA-F0-9]{40}$/.test(value.trim());

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (isValidAddress) {
      navigate(`/trader/${value.trim()}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search wallet address..."
        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
      />
      <button
        type="submit"
        disabled={!isValidAddress}
        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
      >
        Go
      </button>
    </form>
  );
}
