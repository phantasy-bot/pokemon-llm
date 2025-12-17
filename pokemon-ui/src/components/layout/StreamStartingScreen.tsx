/**
 * StreamStartingScreen - "Stream Starting Soon" countdown overlay
 * 
 * Features:
 * - Black background with white flower pattern
 * - Countdown timer (duration from backend via countdownSeconds prop)
 * - Holographic color transition when complete
 * - Preloads TTS during countdown
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import './StreamStartingScreen.css';

interface StreamStartingScreenProps {
  onComplete: () => void;
  // Countdown duration in seconds (from backend)
  countdownSeconds?: number;
  // Optional: skip countdown if backend signals early
  forceStart?: boolean;
}

// Format milliseconds as MM:SS
function formatTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// Flower background (same pattern as Just Chatting, but white on black)
function FlowerBackground() {
  const rows = [];
  const rowCount = 14;
  const flowersPerRow = 40;
  
  for (let row = 0; row < rowCount; row++) {
    const flowers = [];
    for (let i = 0; i < flowersPerRow; i++) {
      flowers.push(
        <span key={i} className="flower-icon flower-spin-cw">✿</span>
      );
    }
    
    rows.push(
      <div 
        key={row} 
        className="flower-row"
        style={{ animationDelay: `${row * -1.5}s` }}
      >
        {flowers}
        {flowers}
        {flowers}
      </div>
    );
  }
  
  return <div className="starting-flower-background">{rows}</div>;
}

export function StreamStartingScreen({ onComplete, countdownSeconds = 300, forceStart = false }: StreamStartingScreenProps) {
  // Convert seconds to milliseconds for internal timer
  const countdownMs = countdownSeconds * 1000;
  const [timeRemaining, setTimeRemaining] = useState(countdownMs);
  const [isTransitioning, setIsTransitioning] = useState(false);
  // Track if we've received the actual countdown from backend
  const [hasReceivedCountdown, setHasReceivedCountdown] = useState(false);
  // Use ref to track the actual end time (doesn't change when effect re-runs)
  const endTimeRef = useRef<number | null>(null);
  
  // When countdownSeconds changes from default, start the timer
  useEffect(() => {
    if (countdownSeconds !== 300 && !hasReceivedCountdown) {
      // We received a non-default countdown from backend
      setHasReceivedCountdown(true);
      setTimeRemaining(countdownSeconds * 1000);
      endTimeRef.current = Date.now() + countdownSeconds * 1000;
    }
  }, [countdownSeconds, hasReceivedCountdown]);
  
  // Countdown timer - only runs after we've received countdown from backend
  useEffect(() => {
    if (isTransitioning) return;
    if (!hasReceivedCountdown) return; // Don't start until backend sends countdown
    
    // Set end time if not already set
    if (endTimeRef.current === null) {
      endTimeRef.current = Date.now() + countdownMs;
    }
    
    const interval = setInterval(() => {
      if (endTimeRef.current === null) return;
      
      const remaining = endTimeRef.current - Date.now();
      setTimeRemaining(remaining);
      
      if (remaining <= 0) {
        clearInterval(interval);
        startTransition();
      }
    }, 100);
    
    return () => clearInterval(interval);
  }, [isTransitioning, hasReceivedCountdown, countdownMs]);
  
  // Handle force start from backend
  useEffect(() => {
    if (forceStart && !isTransitioning) {
      startTransition();
    }
  }, [forceStart, isTransitioning]);
  
  const startTransition = useCallback(() => {
    setIsTransitioning(true);
    setTimeRemaining(0);
    // Color transition plays, then complete
  }, []);
  
  // After transition animation completes
  const handleTransitionEnd = useCallback(() => {
    onComplete();
  }, [onComplete]);
  
  return (
    <div className={`stream-starting-screen ${isTransitioning ? 'transitioning' : ''}`}>
      <div className="starting-background-layer">
        <FlowerBackground />
      </div>
      
      <div className={`starting-content ${isTransitioning ? 'shake-and-transition' : ''}`}
           onAnimationEnd={isTransitioning ? handleTransitionEnd : undefined}>
        <h1 className="starting-title">STREAM STARTING SOON</h1>
        <div className="countdown-timer">
          {formatTime(timeRemaining)}
        </div>
        <div className="starting-subtitle">
          <span className="flower-icon">✿</span>
          <span>with Lass</span>
          <span className="flower-icon">✿</span>
        </div>
      </div>
    </div>
  );
}
