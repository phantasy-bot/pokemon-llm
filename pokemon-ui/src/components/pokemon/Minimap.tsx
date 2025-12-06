import { useState, useEffect } from "react";

interface MinimapProps {
  location: string;
  visible?: boolean;
  className?: string;
  timestamp?: string; // Add timestamp prop
}

// Removed MINIMAP_POLL_INTERVAL

export function Minimap({
  location,
  visible = true,
  className = "",
  timestamp,
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

  return (
    <div className={`minimap ${className}`}>
      {/* Location header */}
      <div className="minimap__header">
        <span className="minimap__location">{location}</span>
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
            <span className="minimap__error-icon">🗺️</span>
            <span className="minimap__error-text">Map unavailable</span>
          </div>
        )}

        {minimapSrc && (
          <img
            src={minimapSrc}
            alt="Pokemon world minimap"
            className={`minimap__image ${minimapVisible ? "minimap__image--visible" : "minimap__image--hidden"}`}
            onLoad={handleMinimapLoad}
            onError={handleMinimapError}
            style={{ display: minimapVisible ? "block" : "none" }}
          />
        )}

        {!minimapVisible && !isLoading && !error && (
          <div className="minimap__placeholder">
            <span className="minimap__placeholder-icon">🗺️</span>
            <span className="minimap__placeholder-text">No map data</span>
          </div>
        )}
      </div>
    </div>
  );
}
