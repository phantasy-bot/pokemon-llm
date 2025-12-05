import { useState, useEffect, useRef, useCallback } from "react";

interface MinimapProps {
  location: string;
  visible?: boolean;
  className?: string;
}

const MINIMAP_POLL_INTERVAL = 1000; // 1 second (matches Vue app)

export function Minimap({
  location,
  visible = true,
  className = "",
}: MinimapProps) {
  const [minimapSrc, setMinimapSrc] = useState<string>("");
  const [minimapVisible, setMinimapVisible] = useState<boolean>(visible);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [failedAttempts, setFailedAttempts] = useState<number>(0);
  const [hasSuccessfullyLoaded, setHasSuccessfullyLoaded] =
    useState<boolean>(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Polling function that accesses latest state
  const pollMinimap = useCallback(() => {
    // Only show loading state if we haven't failed too many times or we've successfully loaded before
    setFailedAttempts((current) => {
      const shouldShowLoading = current < 3 || hasSuccessfullyLoaded;

      // Force browser to re-fetch by adding cache-busting query parameter
      const newSrc = `/minimap.png?t=${Date.now()}`;
      setMinimapSrc(newSrc);

      if (shouldShowLoading) {
        setIsLoading(true);
      }
      setError(null);

      return current;
    });
  }, [hasSuccessfullyLoaded]);

  useEffect(() => {
    // Start polling when component mounts
    const startPolling = () => {
      // Clear any existing interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }

      // Set up polling interval
      intervalRef.current = setInterval(pollMinimap, MINIMAP_POLL_INTERVAL);

      // Initial attempt
      const initialSrc = `/minimap.png?t=${Date.now()}`;
      setMinimapSrc(initialSrc);
      setIsLoading(true);
    };

    // Start polling
    startPolling();

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [pollMinimap]);

  // Handle successful image load
  const handleMinimapLoad = () => {
    // Image loaded successfully (non-zero bytes, valid image format)
    setIsLoading(false);
    setError(null);
    setMinimapVisible(true);
    setFailedAttempts(0);
    setHasSuccessfullyLoaded(true);
  };

  // Handle image load error
  const handleMinimapError = (
    event: React.SyntheticEvent<HTMLImageElement, Event>,
  ) => {
    // Image failed to load (could be 0 bytes, missing, network error, corrupted)
    setIsLoading(false);
    setMinimapVisible(false);
    setError("Failed to load minimap");
    setFailedAttempts((prev) => prev + 1);

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
            ref={imageRef}
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
