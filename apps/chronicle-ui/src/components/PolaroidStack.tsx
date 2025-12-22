interface PolaroidProps {
  src: string;
  alt: string;
  isStack?: boolean;
  className?: string;
  timestamp?: number;
}

export function Polaroid({ src, alt, isStack, className = "", timestamp }: PolaroidProps) {
  const date = timestamp ? new Date(timestamp) : null;
  
  // Format date in a casual handwritten style: "Dec 21, '25 • 3:45pm"
  const formatDateTime = (d: Date) => {
    const month = d.toLocaleDateString('en-US', { month: 'short' });
    const day = d.getDate();
    const year = d.getFullYear().toString().slice(-2);
    const time = d.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    }).toLowerCase().replace(' ', '');
    return `${month} ${day}, '${year} · ${time}`;
  };

  if (!src) {
    return (
      <div className={`polaroid-card flex items-center justify-center bg-gray-100 min-h-[200px] ${className}`}>
        <span className="font-mono text-xs text-gray-400">NO IMAGE</span>
      </div>
    );
  }

  return (
    <div className={`${isStack ? 'polaroid-stack' : ''} ${className}`}>
      <div className="polaroid-card !pb-3">
        <img 
          src={src} 
          alt={alt} 
          className="polaroid-image hover:grayscale transition-all duration-500" 
        />
        {/* Handwritten date caption - like writing on a polaroid */}
        {date && (
          <div className="pt-1.5 text-center">
            <span className="notebook-font text-base text-zinc-500 tracking-wide">
              {formatDateTime(date)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
