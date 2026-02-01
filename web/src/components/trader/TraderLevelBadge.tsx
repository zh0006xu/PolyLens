import { Badge } from '../common/Badge';

export interface TraderLevelInfo {
  level: string;
  emoji: string;
  label: string;
  variant: 'default' | 'success' | 'danger' | 'warning' | 'info';
  description: string;
}

// Level definitions based on trading volume
export const TRADER_LEVELS: Record<string, TraderLevelInfo> = {
  whale: {
    level: 'whale',
    emoji: '🐋',
    label: 'Whale',
    variant: 'success',
    description: 'Single trade ≥ $10,000 AND single market value ≥ $50,000',
  },
  shark: {
    level: 'shark',
    emoji: '🦈',
    label: 'Shark',
    variant: 'info',
    description: 'Single trade ≥ $5,000 AND single market value ≥ $10,000',
  },
  dolphin: {
    level: 'dolphin',
    emoji: '🐬',
    label: 'Dolphin',
    variant: 'warning',
    description: 'Single trade $500-$5,000 OR single market value $2,000-$10,000',
  },
  fish: {
    level: 'fish',
    emoji: '🐟',
    label: 'Fish',
    variant: 'default',
    description: 'Below dolphin thresholds',
  },
};

// Volume-only estimation is not PHASE5-compliant; keep as opt-in fallback only.
export function estimateLevelFromVolume(vol: number | null | undefined): TraderLevelInfo | null {
  return null;
}

export function getLevelInfo(level: string | null | undefined): TraderLevelInfo {
  if (!level) return TRADER_LEVELS.fish;
  return TRADER_LEVELS[level.toLowerCase()] || TRADER_LEVELS.fish;
}

interface TraderLevelBadgeProps {
  level?: string | null;
  volume?: number | null;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export function TraderLevelBadge({ level, volume, showLabel = true, size = 'md' }: TraderLevelBadgeProps) {
  void volume;
  const levelInfo = level ? getLevelInfo(level) : null;

  if (!levelInfo) return null;

  if (size === 'sm') {
    return (
      <div className="group relative inline-flex">
        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs bg-slate-800 border border-slate-700 cursor-help">
          <span>{levelInfo.emoji}</span>
          <span className="text-slate-300">{levelInfo.label}</span>
        </span>
        <div className="hidden group-hover:block absolute left-0 top-full mt-1 z-10 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 whitespace-nowrap shadow-lg">
          {levelInfo.description}
        </div>
      </div>
    );
  }

  return (
    <div className="group relative inline-flex">
      <Badge variant={levelInfo.variant}>
        <span className="cursor-help">
          {levelInfo.emoji} {showLabel && levelInfo.label}
        </span>
      </Badge>
      <div className="hidden group-hover:block absolute left-0 top-full mt-1 z-10 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-300 whitespace-nowrap shadow-lg">
        {levelInfo.description}
      </div>
    </div>
  );
}
