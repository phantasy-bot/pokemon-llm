import './LassMinimapOverlay.css';

interface LassMarking {
  x: number;
  y: number;
  type: 'N' | 'O' | 'E'; // N=NPC, O=Opening (map tile), E=Exit (Lass-discovered)
  opacity: number;
  age_hours?: number;
}

interface LassMinimapOverlayProps {
  markings?: LassMarking[];
  gridSize?: { width: number; height: number }; // Minimap grid dimensions (default 21x19)
}

// Helper to get human-readable marker name
function getMarkerLabel(type: 'N' | 'O' | 'E'): string {
  switch (type) {
    case 'N': return 'NPC';
    case 'O': return 'Opening';
    case 'E': return 'Exit';
    default: return type;
  }
}

/**
 * Translucent overlay showing Lass's markings on the minimap.
 * N = NPC (pink), O = Opening/Exit from map data (pink), E = Lass-discovered Exit (distinct color)
 * Opacity fades as markings age/decay.
 * Uses aspect-ratio constrained positioning to match the minimap image exactly.
 */
export function LassMinimapOverlay({
  markings = [],
  gridSize = { width: 21, height: 19 }, // Match the actual minimap grid size
}: LassMinimapOverlayProps) {
  if (!markings || markings.length === 0) {
    return null;
  }

  // Calculate aspect ratio for the overlay to match grid dimensions
  const aspectRatio = gridSize.width / gridSize.height;

  return (
    <div 
      className="lass-overlay"
      style={{
        // Match the aspect ratio of the grid so overlay positions align with image
        aspectRatio: aspectRatio,
      }}
    >
      {markings.map((mark, index) => {
        // Convert grid position to percentage of the grid
        // Note: positions are 0-indexed, so we use mark.x, mark.y directly
        const leftPct = (mark.x / gridSize.width) * 100;
        const topPct = (mark.y / gridSize.height) * 100;
        
        // Size of each cell as percentage of grid
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
            title={`${getMarkerLabel(mark.type)} at (${mark.x}, ${mark.y})${mark.age_hours ? ` - ${mark.age_hours}h ago` : ''}`}
          >
            <span className="lass-overlay__marker-text">{mark.type}</span>
          </div>
        );
      })}
    </div>
  );
}
