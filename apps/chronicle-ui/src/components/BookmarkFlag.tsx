import { Lock, Unlock } from 'lucide-react';

interface BookmarkFlagProps {
  type: 'locked' | 'unlocked' | 'teaser';
  onClick?: () => void;
  className?: string;
  disabled?: boolean;
}

export function BookmarkFlag({ type, onClick, className = '', disabled }: BookmarkFlagProps) {
  const isTeaser = type === 'teaser';
  const isUnlocked = type === 'unlocked';
  
  // Gold/amber color scheme for lock icons
  const iconColor = isUnlocked ? 'text-emerald-600' : 'text-amber-500';
  const label = isTeaser 
    ? 'Unlockable Content' 
    : isUnlocked 
      ? 'Content Unlocked' 
      : 'Holder-Only Content';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        group flex items-center gap-2 px-3 py-2
        bg-white/90 backdrop-blur-sm rounded-lg
        border border-zinc-200 hover:border-zinc-300
        transition-all duration-200 active:scale-95
        disabled:opacity-40 disabled:cursor-not-allowed
        ${className}
      `}
      title={label}
    >
      {/* Gold lock icon */}
      <span className={`${iconColor} transition-colors`}>
        {isUnlocked ? <Unlock size={14} strokeWidth={2.5} /> : <Lock size={14} strokeWidth={2.5} />}
      </span>
      
      {/* Label text */}
      <span className="font-mono text-[10px] font-semibold text-zinc-600 uppercase tracking-wide">
        {label}
      </span>
    </button>
  );
}
