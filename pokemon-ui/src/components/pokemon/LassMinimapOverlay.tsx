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
  tileSize?: number; // Pixel size of each tile in the minimap
}

/**
 * Translucent overlay showing Lass's markings on the minimap.
 * N = NPC (pink), O = Opening/Exit (pink)
 * Opacity fades as markings age/decay.
 */
export function LassMinimapOverlay({
  markings = [],
  gridSize = { width: 10, height: 9 },
  tileSize = 16,
}: LassMinimapOverlayProps) {
  if (!markings || markings.length === 0) {
    return null;
  }

  // Calculate overlay dimensions based on minimap grid
  const overlayWidth = gridSize.width * tileSize;
  const overlayHeight = gridSize.height * tileSize;

  return (
    <div 
      className="lass-overlay"
      style={{
        width: overlayWidth,
        height: overlayHeight,
      }}
    >
      {markings.map((mark, index) => (
        <div
          key={`lass-mark-${index}-${mark.x}-${mark.y}`}
          className={`lass-overlay__marker lass-overlay__marker--${mark.type}`}
          style={{
            left: mark.x * tileSize,
            top: mark.y * tileSize,
            width: tileSize,
            height: tileSize,
            opacity: mark.opacity,
          }}
          title={`${mark.type === 'N' ? 'NPC' : 'Opening'} at (${mark.x}, ${mark.y})${mark.age_hours ? ` - ${mark.age_hours}h ago` : ''}`}
        >
          <span className="lass-overlay__marker-text">{mark.type}</span>
        </div>
      ))}
    </div>
  );
}
