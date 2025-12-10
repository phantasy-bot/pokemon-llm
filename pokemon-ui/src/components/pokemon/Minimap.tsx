import { useState, useEffect } from "react";
import { LassMinimapOverlay } from "./LassMinimapOverlay";

interface MinimapProps {
  location: string;
  visible?: boolean;
  className?: string;
  timestamp?: string; // Add timestamp prop
  explorationPct?: number; // Exploration percentage for current map
  lassMarkings?: Array<{
    x: number;
    y: number;
    type: 'N' | 'O';
    opacity: number;
    age_hours?: number;
  }>;
}

// Removed MINIMAP_POLL_INTERVAL

export function Minimap({
  location,
  visible = true,
  className = "",
  timestamp,
  explorationPct,
  lassMarkings,
}: MinimapProps) {
  const [minimapSrc, setMinimapSrc] = useState<string>("");
  const [minimapVisible, setMinimapVisible] = useState<boolean>(visible);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load minimap only when a valid timestamp is provided from backend
  // This prevents loading stale minimap files when app restarts
  useEffect(() => {
    // Only load if we have a valid timestamp from the backend
    // Don't auto-load on mount with Date.now() - wait for actual update
    if (!timestamp) {
      // No timestamp yet - stay in placeholder state
      setMinimapSrc("");
      setMinimapVisible(false);
      setIsLoading(false);
      setError(null);
      return;
    }
    
    const newSrc = `/minimap.png?t=${timestamp}`;
    setMinimapSrc(newSrc);
    setIsLoading(true);
    setError(null);
  }, [timestamp, location]); // Reload on timestamp or location change

  // Handle successful image load
  const handleMinimapLoad = () => {
    // Image loaded successfully (non-zero bytes, valid image format)
    setIsLoading(false);
    setError(null);
    setMinimapVisible(true);
  };

  // Handle image load error
  const handleMinimapError = (
    event: React.SyntheticEvent<HTMLImageElement, Event>,
  ) => {
    // Image failed to load (could be 0 bytes, missing, network error, corrupted)
    setIsLoading(false);
    setMinimapVisible(false);
    setError("Failed to load minimap");

    // Prevent broken image icon showing
    const img = event.target as HTMLImageElement;
    img.style.display = "none";
  };

  // Parse location to split map name, number and coordinates
  // Format expected: "MAP_NAME (Map ID) (X, Y)" or "MAP_NAME (ID) (X, Y)"
  const parseLocation = (loc: string): { mapName: string; mapNumber: string; coords: string } => {
    let coords = '';
    let rest = loc;
    
    // 1. Extract Coords: (X, Y) at end - look for two numbers with comma
    const coordMatch = loc.match(/\((\d+),?\s*(\d+)\)\s*$/);
    if (coordMatch) {
      coords = `(${coordMatch[1]}, ${coordMatch[2]})`;
      rest = loc.replace(/\((\d+),?\s*(\d+)\)\s*$/, '').trim();
    }
    
    // 2. Extract Map Number from rest: NAME (Map NUMBER) or NAME (NUMBER)
    let mapNumber = '';
    let mapName = rest;
    
    // Match "Name (Map 123)" or "Name (123)" - capture just the number
    const numMatch = rest.match(/^(.*?)\s*\((?:Map\s*)?([\d]+)\)\s*$/i);
    if (numMatch) {
        mapName = numMatch[1].trim();
        mapNumber = numMatch[2]; // Just the number
    }
    
    return { mapName, mapNumber, coords };
  };

  const { mapName, mapNumber, coords } = parseLocation(location);

  return (
    <div className={`minimap ${className}`}>
      {/* Location header - styled like Pokemon Team header */}
      <div className="minimap__header">
        <div className="minimap__header-left">
            <span className="minimap__location">{mapName}</span>
            {mapNumber && <span className="minimap__location-number">Map {mapNumber.replace(/[()]/g, '')}</span>}
        </div>
        {coords && <span className="minimap__coords">{coords}</span>}
      </div>


      {/* Minimap body */}
      <div className="minimap__body">
        {isLoading && (
          <div className="minimap__loading">
            <div className="minimap__loading-spinner"></div>
            <span className="minimap__loading-text">Loading map...</span>
          </div>
        )}

        {error && (
          <div className="minimap__error">
            <span className="minimap__error-text">Map unavailable</span>
          </div>
        )}

        {minimapSrc && (
          <div className="minimap__image-container">
            <img
              src={minimapSrc}
              alt="Pokemon world minimap"
              className={`minimap__image ${minimapVisible ? "minimap__image--visible" : "minimap__image--hidden"}`}
              onLoad={handleMinimapLoad}
              onError={handleMinimapError}
              style={{ display: minimapVisible ? "block" : "none" }}
            />
            {/* Lass's pink overlay with N/O markers - positioned over the image */}
            {minimapVisible && lassMarkings && lassMarkings.length > 0 && (
              <LassMinimapOverlay markings={lassMarkings} />
            )}
          </div>
        )}

        {!minimapVisible && !isLoading && !error && (
          <div className="minimap__placeholder">
            <img 
              src="/minimap-placeholder.png" 
              alt="No map data" 
              className="minimap__placeholder-image"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
        )}
      </div>

      {/* Exploration percentage display - OUTSIDE body, below it */}
      {explorationPct !== undefined && (
        <div className="minimap__exploration">
          <span className="minimap__exploration-label">EXPLORED</span>
          <span className="minimap__exploration-value">&nbsp;{explorationPct.toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}
