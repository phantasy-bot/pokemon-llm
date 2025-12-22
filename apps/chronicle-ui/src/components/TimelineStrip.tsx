import { Home, Award, Crown, MapPin } from 'lucide-react';
import { Drop } from '../lib/api';

interface TimelineStripProps {
  drops: Drop[];
  currentIndex: number;
  onSelect: (index: number) => void;
}

export function TimelineStrip({ drops, currentIndex, onSelect }: TimelineStripProps) {
  // drops are expected to be sorted Oldest -> Newest (ASC) by parent Timeline
  
  const getIcon = (drop: Drop) => {
    const title = drop.name.toLowerCase();
    if (title.includes("start")) return <Home size={10} />;
    if (title.includes("badge") || title.includes("defeat")) return <Award size={10} />;
    if (title.includes("champion") || title.includes("elite")) return <Crown size={10} />;
    if (title.includes("caught")) return <div className="w-1.5 h-1.5 rounded-full border border-current bg-white" />; 
    if (title.includes("route") || title.includes("city")) return <MapPin size={9} />;
    return <div className="w-1 h-1 rounded-full bg-current opacity-50" />; 
  };

  const windowSize = 12;
  const halfWindow = Math.floor(windowSize / 2);
  
  // Logic for windowing
  let start = Math.max(0, currentIndex - halfWindow);
  let end = Math.min(drops.length, start + windowSize);
  
  if (end - start < windowSize) {
    start = Math.max(0, end - windowSize);
  }
  
  const visibleItems = drops.slice(start, end).map((drop, idx) => ({
    drop,
    originalIndex: start + idx,
    isCurrent: (start + idx) === currentIndex
  }));

  return (
    <div className="flex items-center gap-1 h-full px-4 py-2 overflow-hidden">
      {start > 0 && <span className="text-xs text-ink-light">...</span>}
      
      {visibleItems.map((item, i) => (
        <button
          key={item.drop.id}
          onClick={() => onSelect(item.originalIndex)}
          className={`
            group relative flex items-center justify-center w-5 h-5 rounded-full transition-all
            ${item.isCurrent 
              ? 'bg-[#FDFBF7] text-black scale-125 z-10 shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] border border-black' 
              : item.originalIndex < currentIndex
                ? 'bg-black/80 text-white hover:bg-black hover:scale-110'  // Past: filled but slightly lighter
                : 'text-ink-light hover:bg-black/5 hover:scale-110'}       // Future: unfilled
          `}
          title={item.drop.name}
        >
          {getIcon(item.drop)}
          
          {/* Connecting line - solid only for past items, faded for current-to-next and beyond */}
          {(i < visibleItems.length - 1 || (end === drops.length)) && (
            <div className={`absolute top-1/2 -right-2 w-2 h-px -z-10 ${
              item.originalIndex < currentIndex 
                ? 'bg-black'           // Past: solid (traveled path)
                : 'bg-black/20'        // Current and future: faded
            }`} />
          )}
        </button>
      ))}
      
      {/* Future Championship Icon */}
      {end === drops.length && (
        <div className="relative flex items-center justify-center w-5 h-5 rounded-full text-zinc-300 cursor-not-allowed opacity-50 ml-1">
          <Crown size={10} />
          {/* Dotted line to future */}
          <div className="absolute top-1/2 -left-2 w-2 h-px -z-10 bg-black/10 border-t border-dotted" />
        </div>
      )}
    </div>
  );
}
