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
  gridSize?: { width: number; height: number }; // Minimap grid dimensions
}

/**
 * Translucent overlay showing Lass's markings on the minimap.
 * N = NPC (pink), O = Opening/Exit (pink)
 * Opacity fades as markings age/decay.
 */
export function LassMinimapOverlay({
  markings = [],
  gridSize = { width: 10, height: 9 },
}: LassMinimapOverlayProps) {
  if (!markings || markings.length === 0) {
    return null;
  }

  // Use percentage-based positioning so overlay scales with the minimap image
  // Each marker position is converted to a percentage of the grid

  return (
    <div className="lass-overlay">
      {markings.map((mark, index) => {
        // Convert grid coordinates to percentages
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
