import './LassMinimapOverlay.css';

interface LassMarking {
  x: number;
  y: number;
  type: 'N' | 'O';
  opacity: number;
  age_hours?: number;
}

interface LassMinimapOverlayProps {
  markings?: LassMarking[];
  gridSize?: { width: number; height: number }; // Minimap grid dimensions (default 21x19)
}

/**
 * Translucent overlay showing Lass's markings on the minimap.
 * N = NPC (pink), O = Opening/Exit (pink)
 * Opacity fades as markings age/decay.
 * Uses percentage-based positioning to match the image exactly.
 */
export function LassMinimapOverlay({
  markings = [],
  gridSize = { width: 21, height: 19 }, // Match the actual minimap grid size
}: LassMinimapOverlayProps) {
  if (!markings || markings.length === 0) {
    return null;
  }

  return (
    <div className="lass-overlay">
      {markings.map((mark, index) => {
        // Convert grid position to percentage of overlay
        const leftPct = (mark.x / gridSize.width) * 100;
        const topPct = (mark.y / gridSize.height) * 100;
        const widthPct = (1 / gridSize.width) * 100;
        const heightPct = (1 / gridSize.height) * 100;

        return (
          <div
            key={`lass-mark-${index}-${mark.x}-${mark.y}`}
            className={`lass-overlay__marker lass-overlay__marker--${mark.type}`}
            style={{
              left: `${leftPct}%`,
              top: `${topPct}%`,
              width: `${widthPct}%`,
              height: `${heightPct}%`,
              opacity: mark.opacity,
            }}
            title={`${mark.type === 'N' ? 'NPC' : 'Opening'} at (${mark.x}, ${mark.y})${mark.age_hours ? ` - ${mark.age_hours}h ago` : ''}`}
          >
            <span className="lass-overlay__marker-text">{mark.type}</span>
          </div>
        );
      })}
    </div>
  );
}
