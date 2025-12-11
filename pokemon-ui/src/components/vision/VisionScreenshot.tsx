import { useState, useRef, useEffect } from "react";
import "./VisionScreenshot.css";

interface VisionScreenshotProps {
  base64Data?: string; // New prop for strict sync
  compact?: boolean;
  className?: string;
}

export function VisionScreenshot({
  base64Data,
  compact = false,
  className = "",
}: VisionScreenshotProps) {
  const [screenshotSrc, setScreenshotSrc] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showStatic, setShowStatic] = useState(false); // CRT static effect
  const [staticPhase, setStaticPhase] = useState<'in' | 'full' | 'out'>('full'); // For fade animation
  const imageRef = useRef<HTMLImageElement>(null);
  const prevBase64Ref = useRef<string | undefined>(undefined);

  // Load screenshot when component mounts or dependencies change
  useEffect(() => {
    // STRICT SYNC: Only use the base64 data provided in the log.
    // Do NOT fetch /latest.png as it may be from the next cycle (ahead of analysis).
    if (base64Data) {
      // Check if this is a NEW screenshot (different from previous)
      const isNewScreenshot = prevBase64Ref.current && prevBase64Ref.current !== base64Data;
      
      if (isNewScreenshot) {
        // Show CRT static effect with fade in/out phases
        // Phase 1: Fade in static (200ms)
        setShowStatic(true);
        setStaticPhase('in');
        
        const fadeInTimer = setTimeout(() => {
          setStaticPhase('full');
        }, 200);
        
        // Phase 2: Hold static, then fade out and reveal new image (600ms)
        const revealTimer = setTimeout(() => {
          setStaticPhase('out');
          setScreenshotSrc(`data:image/png;base64,${base64Data}`);
        }, 600);
        
        // Phase 3: Remove static overlay (200ms after fade out starts)
        const cleanupTimer = setTimeout(() => {
          setShowStatic(false);
          setError(null);
          setIsLoading(false);
        }, 800);
        
        prevBase64Ref.current = base64Data;
        return () => {
          clearTimeout(fadeInTimer);
          clearTimeout(revealTimer);
          clearTimeout(cleanupTimer);
        };
      } else {
        // First load or same image - no effect needed
        setScreenshotSrc(`data:image/png;base64,${base64Data}`);
        setError(null);
        setIsLoading(false);
        prevBase64Ref.current = base64Data;
      }
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
        
        {/* CRT Static Noise Effect */}
        {showStatic && (
          <div className={`vision-screenshot__static vision-screenshot__static--${staticPhase}`}>
            <div className="vision-screenshot__static-overlay" />
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
            className={`vision-screenshot__image ${showStatic ? 'vision-screenshot__image--hidden' : ''}`}
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
