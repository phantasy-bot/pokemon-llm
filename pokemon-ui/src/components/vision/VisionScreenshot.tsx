import { useState, useRef, useEffect } from "react";
import "./VisionScreenshot.css";

interface VisionScreenshotProps {
  base64Data?: string; // New prop for strict sync
  compact?: boolean;
  className?: string;
}

// Constants
const FALLBACK_SRC = "/placeholder.png"; // Optional fallback

export function VisionScreenshot({
  base64Data,
  compact = false,
  className = "",
}: VisionScreenshotProps) {
  const [screenshotSrc, setScreenshotSrc] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  // Load screenshot when component mounts or dependencies change
  useEffect(() => {
    // STRICT SYNC: Only use the base64 data provided in the log.
    // Do NOT fetch /latest.png as it may be from the next cycle (ahead of analysis).
    if (base64Data) {
      setScreenshotSrc(`data:image/png;base64,${base64Data}`);
      setError(null); // Clear any previous error
      setIsLoading(false);
    } else {
      // If no base64 data is present, we should NOT show an outdated or future image.
      // Show empty state or keep previous if desired, but for now we set empty to indicate "No Vision Data"
      console.warn("VisionScreenshot: No base64Data provided. Skipping render to prevent desync.");
      setScreenshotSrc(""); // Clear the source to show placeholder/loading
      setIsLoading(false); // Not loading, but no data
      setError("No screenshot data available"); // Indicate the reason
    }
  }, [base64Data]);

  // NOTE: Screenshot now uses the timestamp from vision analysis
  // This ensures the displayed screenshot matches when the vision was analyzed
  
  return (
    <div className={`vision-screenshot ${compact ? "compact" : ""} ${className}`}>
      <div className="vision-screenshot__container">
        {isLoading && (
          <div className="vision-screenshot__loading">
            <div className="vision-screenshot__spinner" />
          </div>
        )}
        
        {error ? (
          <div className="vision-screenshot__error">
            <span>{error}</span>
          </div>
        ) : screenshotSrc ? (
          <img
            ref={imageRef}
            src={screenshotSrc}
            alt="Game Screenshot"
            className="vision-screenshot__image"
            onError={() => {
              setIsLoading(false);
              setError("Failed to render image");
            }}
          />
        ) : (
          <div className="vision-screenshot__placeholder">
             {/* Show nothing or placeholder if no image */}
             <div className="vision-screenshot__placeholder-icon" />
          </div>
        )}
      </div>
    </div>
  );
}
