import { useState, useRef, useEffect } from "react";
import "./VisionScreenshot.css";

interface VisionScreenshotProps {
  timestamp?: string;
  compact?: boolean;
  className?: string;
}

// Constants
const RETRY_DELAY = 1000; // 1 second between retries
const MAX_RETRIES = 3;

export function VisionScreenshot({
  timestamp = "",
  compact = false,
  className = "",
}: VisionScreenshotProps) {
  const [screenshotSrc, setScreenshotSrc] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);

  const imageRef = useRef<HTMLImageElement>(null);

  // Generate cache-busting URL - always show the latest with current timestamp
  const getScreenshotUrl = () => {
    // Use provided timestamp from vision analysis, or current time
    const timestampParam = timestamp || Date.now().toString();
    return `/latest.png?t=${timestampParam}`;
  };

  // Load screenshot with retry mechanism
  const loadScreenshot = (retryAttempt = 0) => {
    const url = getScreenshotUrl();
    setScreenshotSrc(url);
    setIsLoading(true);
    setError(null);

    // Pre-load the image to check if it exists
    const img = new Image();
    img.onload = () => {
      setIsLoading(false);
      setError(null);
      setRetryCount(0); // Reset retry count on success
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
        setRetryCount(0);
      }
    };

    img.src = url;
  };

  // Load screenshot when component mounts or timestamp changes
  useEffect(() => {
    loadScreenshot();
  }, [timestamp]);

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

      {error && (
        <div className="vision-screenshot__error">
          <div className="vision-screenshot__error-text">{error}</div>
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

      {/* Debug info - can be removed later */}
      {process.env.NODE_ENV === "development" && (
        <div
          style={{
            position: "absolute",
            bottom: "2px",
            right: "2px",
            fontSize: "8px",
            color: "#666",
            background: "rgba(255,255,255,0.8)",
            padding: "1px 2px",
            borderRadius: "2px",
          }}
        >
          {timestamp ? `T:${timestamp.slice(-6)}` : "NO-TS"}
        </div>
      )}
    </div>
  );
}
