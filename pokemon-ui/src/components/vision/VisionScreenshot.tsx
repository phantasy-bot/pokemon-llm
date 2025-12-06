import { useState, useRef, useEffect } from "react";
import "./VisionScreenshot.css";

interface VisionScreenshotProps {
  timestamp?: string;
  base64Data?: string; // New prop for strict sync
  compact?: boolean;
  className?: string;
}

// Constants
const RETRY_DELAY = 1000; // 1 second between retries
const MAX_RETRIES = 3;

export function VisionScreenshot({
  timestamp = "",
  base64Data,
  compact = false,
  className = "",
}: VisionScreenshotProps) {
  const [screenshotSrc, setScreenshotSrc] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const imageRef = useRef<HTMLImageElement>(null);

  // Generate cache-busting URL using provided timestamp from vision analysis
  const getScreenshotUrl = () => {
    // Use provided timestamp from vision analysis, or current time as fallback
    const timestampParam = timestamp || Date.now().toString();
    return `/latest.png?t=${timestampParam}`;
  };

  // Load screenshot with retry mechanism
  const loadScreenshot = (retryAttempt = 0) => {
    if (base64Data) {
      // PREFERRED: Use the strictly synchronized base64 data if available
      setScreenshotSrc(`data:image/png;base64,${base64Data}`);
      setIsLoading(false);
      setError(null);
      return;
    }

    const url = getScreenshotUrl();
    setScreenshotSrc(url);
    setIsLoading(true);
    setError(null);

    // Pre-load the image to check if it exists
    const img = new Image();
    img.onload = () => {
      setIsLoading(false);
      setError(null);
    };

    img.onerror = () => {
      if (retryAttempt < MAX_RETRIES) {
        // Retry after delay
        setTimeout(() => {
          loadScreenshot(retryAttempt + 1);
        }, RETRY_DELAY);
      } else {
        setIsLoading(false);
        setError("Failed to load screenshot");
      }
    };

    img.src = url;
  };

  // Load screenshot when component mounts or dependencies change
  useEffect(() => {
    loadScreenshot();
  }, [timestamp, base64Data]);

  // NOTE: Screenshot now uses the timestamp from vision analysis
  // This ensures the displayed screenshot matches when the vision was analyzed

  return (
    <div
      className={`vision-screenshot ${compact ? "vision-screenshot--compact" : ""} ${className}`}
    >
      {isLoading && (
        <div className="vision-screenshot__loading">
          <div className="vision-screenshot__loading-text">
            Loading screenshot...
          </div>
        </div>
      )}

      {(error || (!isLoading && !screenshotSrc)) && (
        <div className="vision-screenshot__placeholder-icon">
          ?
        </div>
      )}

      {!isLoading && !error && screenshotSrc && (
        <img
          ref={imageRef}
          src={screenshotSrc}
          alt="Vision analysis screenshot"
          className="vision-screenshot__image"
        />
      )}
    </div>
  );
}

