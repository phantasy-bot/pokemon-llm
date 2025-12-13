import { useState, useRef, useEffect } from "react";
import "./VisionScreenshot.css";

interface VisionScreenshotProps {
  base64Data?: string; // New prop for strict sync
  isAnalyzing?: boolean; // Keep CRT effect active while analyzing
  compact?: boolean;
  className?: string;
}

export function VisionScreenshot({
  base64Data,
  isAnalyzing = false,
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
  const prevAnalyzingRef = useRef<boolean>(false); // Track previous isAnalyzing state

  // Handle isAnalyzing state transitions
  useEffect(() => {
    const wasAnalyzing = prevAnalyzingRef.current;
    prevAnalyzingRef.current = isAnalyzing;
    
    if (isAnalyzing && !wasAnalyzing) {
      // Started analyzing - show CRT static
      setShowStatic(true);
      setStaticPhase('full');
    } else if (!isAnalyzing && wasAnalyzing) {
      // Finished analyzing - fade out CRT static and reveal screenshot
      setStaticPhase('out');
      const timer = setTimeout(() => {
        setShowStatic(false);
      }, 300); // Quick fade out
      return () => clearTimeout(timer);
    }
  }, [isAnalyzing]);

  // Load screenshot when component mounts or base64Data changes
  useEffect(() => {
    // STRICT SYNC: Only use the base64 data provided in the log.
    // Do NOT fetch /latest.png as it may be from the next cycle (ahead of analysis).
    if (base64Data) {
      // Always update the screenshot source when we have data
      setScreenshotSrc(`data:image/png;base64,${base64Data}`);
      setError(null);
      setIsLoading(false);
      
      // Track for comparison
      const isNewScreenshot = prevBase64Ref.current && prevBase64Ref.current !== base64Data;
      prevBase64Ref.current = base64Data;
      
      // If NOT analyzing and got new screenshot, do a quick CRT transition
      if (isNewScreenshot && !isAnalyzing) {
        setShowStatic(true);
        setStaticPhase('in');
        
        const fadeInTimer = setTimeout(() => {
          setStaticPhase('full');
        }, 150);
        
        const fadeOutTimer = setTimeout(() => {
          setStaticPhase('out');
        }, 400);
        
        const cleanupTimer = setTimeout(() => {
          setShowStatic(false);
        }, 600);
        
        return () => {
          clearTimeout(fadeInTimer);
          clearTimeout(fadeOutTimer);
          clearTimeout(cleanupTimer);
        };
      }
    } else {
      // If no base64 data is present, show placeholder
      console.warn("VisionScreenshot: No base64Data provided. Showing placeholder.");
      setScreenshotSrc("");
      setIsLoading(false);
      setError("No screenshot data available");
    }
  }, [base64Data, isAnalyzing]);

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
