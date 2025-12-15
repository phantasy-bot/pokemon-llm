/**
 * StreamStartingScreen - "Stream Starting Soon" countdown overlay
 * 
 * Features:
 * - Black background with white flower pattern
 * - 5-minute countdown timer (configurable via VITE_STARTING_COUNTDOWN_MS)
 * - Holographic color transition when complete
 * - Preloads TTS during countdown
 */
import { useState, useEffect, useCallback } from 'react';
import './StreamStartingScreen.css';

// Get countdown duration from env, default to 5 minutes
const COUNTDOWN_MS = parseInt(import.meta.env.VITE_STARTING_COUNTDOWN_MS || '300000', 10);

interface StreamStartingScreenProps {
  onComplete: () => void;
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

export function StreamStartingScreen({ onComplete, forceStart = false }: StreamStartingScreenProps) {
  const [timeRemaining, setTimeRemaining] = useState(COUNTDOWN_MS);
  const [isTransitioning, setIsTransitioning] = useState(false);
  
  // Countdown timer
  useEffect(() => {
    if (isTransitioning) return;
    
    const startTime = Date.now();
    const endTime = startTime + COUNTDOWN_MS;
    
    const interval = setInterval(() => {
      const remaining = endTime - Date.now();
      setTimeRemaining(remaining);
      
      if (remaining <= 0) {
        clearInterval(interval);
        startTransition();
      }
    }, 100);
    
    return () => clearInterval(interval);
  }, [isTransitioning]);
  
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
