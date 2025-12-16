import { useState, useEffect, useRef, useCallback } from "react";
import type {
  PokemonGameState,
  LogEntry,
  BadgeType,
  Pokemon,
} from "../../types/gameTypes";
import type { PokemonDisplay } from "../../types/display";
import { AnalysisPanel } from "../analysis/AnalysisPanel";
import { PokemonTeamBar } from "../pokemon/PokemonTeamBar";
import "./PokemonStreamOverlay.css";

/**
 * TalkingCharacter - Animated character with mouth movement during speech
 * 
 * Provides smooth lip-sync animation by cycling through mouth frames.
 * Gracefully falls back to static image if speaking frames don't exist.
 * 
 * Frame naming convention:
 * - Base: /lass/lass-default.png
 * - Speaking frames: /lass/lass-default-speak1.png, -speak2.png, etc.
 * - Wink frame (optional): /lass/lass-default-wink.png
 */
interface TalkingCharacterProps {
  baseImage: string;           // Base image path (e.g., "/lass/lass-default.png")
  isSpeaking: boolean;         // Whether character is currently speaking
  isWinking?: boolean;         // Whether to show wink frame
  speakFrameCount?: number;    // Number of speaking frames (default 3)
  speakInterval?: number;      // Ms between mouth frame changes (default 100)
  className?: string;
  alt?: string;
}

function TalkingCharacter({
  baseImage,
  isSpeaking,
  isWinking = false,
  speakFrameCount = 3,
  speakInterval = 100,
  className = "",
  alt = "Character"
}: TalkingCharacterProps) {
  const [currentFrame, setCurrentFrame] = useState(0);
  const [availableFrames, setAvailableFrames] = useState<string[]>([baseImage]);
  const [hasCheckedFrames, setHasCheckedFrames] = useState(false);
  const intervalRef = useRef<number | null>(null);
  
  // Generate frame paths based on base image
  const getFramePaths = useCallback(() => {
    // Extract path without extension: /lass/lass-default.png -> /lass/lass-default
    const lastDot = baseImage.lastIndexOf('.');
    const basePath = lastDot > 0 ? baseImage.slice(0, lastDot) : baseImage;
    const ext = lastDot > 0 ? baseImage.slice(lastDot) : '.png';
    
    const frames = [baseImage]; // Frame 0 is always the base (closed mouth)
    for (let i = 1; i <= speakFrameCount; i++) {
      frames.push(`${basePath}-speak${i}${ext}`);
    }
    return frames;
  }, [baseImage, speakFrameCount]);
  
  // Check which frames actually exist (preload test)
  useEffect(() => {
    const framePaths = getFramePaths();
    const validFrames: string[] = [baseImage];
    let loadedCount = 0;
    
    // Test load each speaking frame
    framePaths.slice(1).forEach((framePath) => {
      const img = new Image();
      img.onload = () => {
        validFrames.push(framePath);
        loadedCount++;
        if (loadedCount === framePaths.length - 1) {
          // All frames checked - sort to maintain order
          validFrames.sort((a, b) => {
            const aNum = a.match(/-speak(\d+)/)?.[1] || '0';
            const bNum = b.match(/-speak(\d+)/)?.[1] || '0';
            return parseInt(aNum) - parseInt(bNum);
          });
          setAvailableFrames(validFrames);
          setHasCheckedFrames(true);
        }
      };
      img.onerror = () => {
        loadedCount++;
        if (loadedCount === framePaths.length - 1) {
          setAvailableFrames(validFrames.length > 1 ? validFrames : [baseImage]);
          setHasCheckedFrames(true);
        }
      };
      img.src = framePath;
    });
    
    // If no speaking frames to check, just use base
    if (framePaths.length === 1) {
      setHasCheckedFrames(true);
    }
  }, [baseImage, getFramePaths]);
  
  // Animate through frames when speaking
  useEffect(() => {
    if (isSpeaking && availableFrames.length > 1 && hasCheckedFrames) {
      // Start animation
      intervalRef.current = window.setInterval(() => {
        setCurrentFrame(prev => {
          // Cycle through frames 0 -> 1 -> 2 -> 1 -> 0 -> 1 -> ... for natural mouth movement
          const maxFrame = availableFrames.length - 1;
          if (maxFrame <= 1) return prev === 0 ? 1 : 0;
          // Random for more natural look
          return Math.floor(Math.random() * availableFrames.length);
        });
      }, speakInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
        }
      };
    } else {
      // Not speaking - return to base frame
      setCurrentFrame(0);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [isSpeaking, availableFrames, hasCheckedFrames, speakInterval]);
  
  // Determine which image to show
  const getDisplayImage = (): string => {
    // Wink takes priority
    if (isWinking) {
      const lastDot = baseImage.lastIndexOf('.');
      const basePath = lastDot > 0 ? baseImage.slice(0, lastDot) : baseImage;
      const ext = lastDot > 0 ? baseImage.slice(lastDot) : '.png';
      return `${basePath}-wink${ext}`;
    }
    
    // Speaking animation
    if (isSpeaking && availableFrames.length > 1) {
      return availableFrames[currentFrame] || baseImage;
    }
    
    // Default
    return baseImage;
  };
  
  return (
    <img 
      src={getDisplayImage()}
      alt={alt}
      className={className}
      key={baseImage} // Force remount on base image change
    />
  );
}

// Typewriter text component - fixed speed per character (kept as fallback)


// Animated ellipsis placeholder: '' -> '.' -> '..' -> '...' -> '' -> ...

/**
 * HighlightedCommentary - Parses commentary text to highlight platform mentions
 * - Purple for Twitch mentions: "Username on Twitch"
 * - Green for Pump.fun mentions: "Username on Pump.fun" or "Username on Pump"
 */
function HighlightedCommentary({ text }: { text: string }) {
  // Match patterns like "Username on Twitch" or "Username on Pump.fun" or "Username on Pump"
  const parts: React.ReactNode[] = [];
  
  // Regex to match "Word(s) on Twitch" or "Word(s) on Pump.fun" or "Word(s) on Pump"
  // Captures: group 1 = username, group 2 = platform (Twitch, Pump.fun, or Pump)
  const platformMentionRegex = /(\S+)\s+on\s+(Twitch|Pump\.fun|Pump)/gi;
  
  let lastIndex = 0;
  let match;
  
  while ((match = platformMentionRegex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    
    const username = match[1];
    const platform = match[2];
    const isPumpfun = platform.toLowerCase().includes('pump');
    const colorClass = isPumpfun ? 'platform-mention--pumpfun' : 'platform-mention--twitch';
    
    // Add the highlighted mention
    parts.push(
      <span key={match.index} className={`platform-mention ${colorClass}`}>
        {username} on {platform}
      </span>
    );
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  
  // If no matches, just return the text
  if (parts.length === 0) {
    return <>{text}</>;
  }
  
  return <>{parts}</>;
}

function AnimatedEllipsis({ interval = 400 }: { interval?: number }) {
  const [dots, setDots] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setDots((prev) => (prev + 1) % 4); // 0, 1, 2, 3, 0, 1, ...
    }, interval);

    return () => clearInterval(timer);
  }, [interval]);

  return <>{'.'.repeat(dots)}</>;
}

// Synced typewriter - calculates speed from audio duration
// Starts immediately when mounted, ends when TTS audio should end
function SyncedTypewriterText({ 
  text, 
  durationMs,
  onComplete 
}: { 
  text: string; 
  durationMs: number;
  onComplete?: () => void;
}) {
  const [displayedText, setDisplayedText] = useState("");
  const timeoutRef = useRef<number | null>(null);
  const indexRef = useRef(0);
  // Use ref to avoid re-triggering useEffect when callback changes
  const onCompleteRef = useRef(onComplete);
  
  // Keep ref in sync with prop
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    // Reset and start animation
    setDisplayedText("");
    indexRef.current = 0;

    if (!text || !durationMs) {
      setDisplayedText(text || "");
      return;
    }

    // Calculate speed: duration / text.length = ms per character
    // Subtract a small buffer to ensure we finish slightly before audio ends
    const charDelayMs = Math.max(10, (durationMs - 200) / text.length);
    console.log(`SyncedTypewriter: ${text.length} chars, ${durationMs}ms = ${charDelayMs.toFixed(1)}ms/char`);

    const typeNextChar = () => {
      if (indexRef.current < text.length) {
        setDisplayedText(text.slice(0, indexRef.current + 1));
        indexRef.current++;
        timeoutRef.current = window.setTimeout(typeNextChar, charDelayMs);
      } else {
        // Animation complete - call via ref
        onCompleteRef.current?.();
      }
    };

    typeNextChar();

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [text, durationMs]); // Removed onComplete from deps - using ref instead

  return <>{displayedText}</>;
}

// Utility function to truncate large numbers
const formatLargeNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, "") + "K";
  }
  return num.toString();
};

// Animated dots component for loading states - fixed width so text doesn't shift
function AnimatedDots() {
  const [dots, setDots] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => {
        if (prev === '...') return '';
        return prev + '.';
      });
    }, 800); // Slower animation (was 500ms)
    return () => clearInterval(interval);
  }, []);
  
  // Fixed width span with dots left-aligned so text before doesn't shift
  return <span style={{ display: 'inline-block', width: '1.5em', textAlign: 'left' }}>{dots}</span>;
}

// Session timer that shows total game time since session started (h:m:s format)
function SessionTimer({ 
  sessionStartTime 
}: { 
  sessionStartTime?: number;
}) {
  const [elapsed, setElapsed] = useState<string>('0h 0m 0s');

  useEffect(() => {
    if (!sessionStartTime) {
      setElapsed('0h 0m 0s');
      return;
    }

    const updateTimer = () => {
      const now = Date.now();
      const diffMs = now - sessionStartTime;
      const totalSeconds = Math.floor(diffMs / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      setElapsed(`${hours}h ${minutes}m ${seconds}s`);
    };

    // Initial update
    updateTimer();
    
    // Tick every second
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [sessionStartTime]);

  return <span className="session-timer">{elapsed}</span>;
}

// Live cycle timer component that ticks every 0.1 seconds
// Uses timestamp-based approach for reliable reset to 0
function LiveCycleTimer({ 
  cycleNumber, 
}: { 
  cycleNumber: number; 
}) {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isFlashing, setIsFlashing] = useState(false);
  const cycleStartTimeRef = useRef<number>(Date.now()); // Track when cycle started
  const lastCycleRef = useRef<number>(cycleNumber);
  const timerRef = useRef<number | null>(null);

  // Tick every 0.1 second - calculate elapsed from start time
  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      const elapsed = (Date.now() - cycleStartTimeRef.current) / 1000;
      setElapsedTime(elapsed);
    }, 100);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Reset timer when cycle changes
  useEffect(() => {
    if (cycleNumber !== lastCycleRef.current) {
      // Cycle completed - flash and reset start time
      setIsFlashing(true);
      setTimeout(() => setIsFlashing(false), 500);
      cycleStartTimeRef.current = Date.now(); // Reset start time
      setElapsedTime(0);
      lastCycleRef.current = cycleNumber;
      console.log(`[CycleTimer] Reset to 0, new cycle: ${cycleNumber}`);
    }
  }, [cycleNumber]);

  return (
    <span className={`cycle-timer ${isFlashing ? 'cycle-timer--flash' : ''}`}>
      {elapsedTime.toFixed(1)}s
    </span>
  );
}

// Kanto gym badges with image paths (1.png - 8.png in order)
const KANTO_BADGES: Record<BadgeType, { image: string; name: string; index: number }> = {
  Boulder: { image: "/badges/1.png", name: "Boulder Badge", index: 1 },
  Cascade: { image: "/badges/2.png", name: "Cascade Badge", index: 2 },
  Thunder: { image: "/badges/3.png", name: "Thunder Badge", index: 3 },
  Rainbow: { image: "/badges/4.png", name: "Rainbow Badge", index: 4 },
  Soul: { image: "/badges/5.png", name: "Soul Badge", index: 5 },
  Marsh: { image: "/badges/6.png", name: "Marsh Badge", index: 6 },
  Volcano: { image: "/badges/7.png", name: "Volcano Badge", index: 7 },
  Earth: { image: "/badges/8.png", name: "Earth Badge", index: 8 },
};

// All badge types in order for silhouette display
const ALL_BADGE_TYPES: BadgeType[] = ["Boulder", "Cascade", "Thunder", "Rainbow", "Soul", "Marsh", "Volcano", "Earth"];

// TTS Commentary data from backend
interface TTSCommentary {
  text: string;
  duration_ms: number;
  playing: boolean;
}

interface PokemonStreamOverlayProps {
  gameState: PokemonGameState;
  wsConnected: boolean;
  logs: LogEntry[];
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
  ttsCommentary?: TTSCommentary | null;
  onTtsCommentaryComplete?: () => void;
}

import "../vision/VisionScreenshot.css"; // Import CRT styles

// Sponsors Configuration
const sponsors = [
  { 
    image: '/sponsors/mystery-gift.png', 
    link: 'https://mysterygift.fun', 
    alt: 'Mystery Gift',
    text: 'mysterygift.fun'
  },
  { 
    image: '/sponsors/phantasy.png', 
    link: 'https://phantasy.bot', 
    alt: 'Phantasy Bot',
    text: 'phantasy.bot'
  }
];

export function PokemonStreamOverlay({
  gameState,
  wsConnected,
  logs,
  memoryWrite,
  onMemoryWriteClear,
  ttsCommentary,
  onTtsCommentaryComplete,
}: PokemonStreamOverlayProps) {
  // Walking animation state
  const [walkingFrame, setWalkingFrame] = useState<1 | 2>(1);

  // Sponsor Rotation State
  const [sponsorIndex, setSponsorIndex] = useState(0);
  const [isSponsorSwitching, setIsSponsorSwitching] = useState(false);

  // Sponsor Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setIsSponsorSwitching(true);
      setTimeout(() => {
        setSponsorIndex((prev) => (prev + 1) % sponsors.length);
        setTimeout(() => setIsSponsorSwitching(false), 200);
      }, 200);
    }, 45000); // 45 seconds to match main site
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setWalkingFrame(prev => prev === 1 ? 2 : 1);
    }, 500);
    return () => clearInterval(timer);
  }, []);

  // Extract Pokemon data from game state
  const currentPokemon: PokemonDisplay[] = (gameState.currentTeam || []).map(
    (p: Pokemon) => ({
      id: p.id,
      name: p.name,
      nickname: p.nickname,
      level: p.level,
      type: p.type,
      type2: p.type2,
      hp: p.hp,
      maxHp: p.maxHp,
      hpPercent: p.maxHp > 0 ? (p.hp / p.maxHp) * 100 : 0,
      hpStatus: (p.hp <= 0
        ? "critical"
        : p.hp < p.maxHp * 0.3
          ? "wounded"
          : "healthy") as "healthy" | "wounded" | "critical",
      isFainted: p.hp <= 0,
      status: p.status,
    }),
  );

  // --- DYNAMIC AVATAR LOGIC ---
  const getAvatarImage = (): string => {
    // 0. INTRO/TITLE SCREEN DETECTION
    // During intro (Oak's dialogue, name entry, etc.) we don't have Pokemon yet
    // Use static image instead of oscillating walking frames
    const hasParty = currentPokemon && currentPokemon.length > 0 && currentPokemon.some(p => p && p.name);
    const isInIntro = !hasParty && !gameState.inBattle && !gameState.inMenu;
    
    if (isInIntro) {
      // During intro dialogue/name entry, use default static pose
      return "/lass/lass-default.png";
    }

    // 1. High Priority: Stressed/Low Health (only if active pokemon is critical)
    const activePokemon = currentPokemon?.[0];
    if (activePokemon && activePokemon.hpStatus === "critical") {
      return "/lass/lass-stressed.png";
    }

    // 2. Battle States
    // STRICT CHECK: Must be inBattle. battleType can be 'wild', 'trainer', etc.
    // We ignore cases where battleType is set but inBattle is false (stale data/default 0 value)
    if (gameState.inBattle) {
      const bType = (gameState.battleType || "").toLowerCase();
      
      if (bType.includes("gym") || bType.includes("leader") || bType.includes("elite")) {
        return "/lass/lass-battle-gym.png"; 
      }
      if (bType.includes("trainer") || bType.includes("rival")) {
        return "/lass/lass-battle-trainer.png";
      }
      if (bType.includes("wild")) {
        return "/lass/lass-battle-wild.png";
      }
      if (bType.includes("victory") || bType.includes("defeat")) { 
         return "/lass/lass-victory.png";
      }
      // Default battle fallback
      return "/lass/lass-battle-wild.png";
    }

    // 3. Dialog State
    // If text is printing and we are NOT in battle, show speaking avatar
    if (gameState.textState?.is_printing) {
      return "/lass/lass-speech.png";
    }

    // 4. Menu State
    if (gameState.inMenu) { 
      return "/lass/lass-menu.png";
    }

    // 5. Movement States (Biking/Surfing) - from movement_state
    const movementMode = gameState.movementState?.movement_mode;
    if (movementMode === "biking") {
      return "/lass/lass-biking.png";
    }
    if (movementMode === "surfing") {
      return "/lass/lass-surfing.png";
    }

    // 6. Default State (Overworld/Exploration) -> Animated walking
    return `/lass/lass-walking-${walkingFrame}.png`;
  };

  const avatarImage = getAvatarImage();

  // Commentary display state - controlled by TTS playback
  // lingerText: text to show after TTS completes (for 6 seconds)
  const [lingerText, setLingerText] = useState<string | null>(null);
  const lingerTimerRef = useRef<number | null>(null);
  
  // Handle TTS completion: start 6-second linger period
  // Text is passed in because ttsCommentary may be cleared by parent before this runs
  const handleTtsComplete = (spokenText: string) => {
    if (spokenText) {
      setLingerText(spokenText);
      
      // Clear any existing timer
      if (lingerTimerRef.current) {
        clearTimeout(lingerTimerRef.current);
      }
      
      // After 6 seconds, clear the linger text
      lingerTimerRef.current = window.setTimeout(() => {
        setLingerText(null);
      }, 6000);
    }
    
    // Notify parent that TTS is complete
    onTtsCommentaryComplete?.();
  };
  
  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (lingerTimerRef.current) {
        clearTimeout(lingerTimerRef.current);
      }
    };
  }, []);


  const badges = gameState.badges || [];
  const location = gameState.minimapLocation || "Unknown Area";

  return (
    <div className="pokemon-stream-overlay">
      {/* Main content area - no header, each column has its own header content */}
      <div className="pokemon-content">
        {/* Left Column - Character Panel (Lass + Goals) */}
        <div className="pokemon-left-col character-column">
          {/* T3 Folder Container */}
          <div className="folder-container">
            {/* Title in the header bar */}
            <div className="folder-title">Lass ✿</div>

            {/* SVG Corner Cutout */}
            <div className="corner-container">
              <svg viewBox="0 0 200 48" className="corner-svg" preserveAspectRatio="none">
                {/* Path 1: The Mask - fills the corner with background color */}
                <path 
                  d="M0,0 c6,0 11,5 11,11 v14 c0,6 5,11 11,11 H194 Q200,36 200,42 L200,0 Z" 
                  fill="var(--bg-panel)" 
                  stroke="none"
                />
                {/* Path 2: The Border (main curve) */}
                <path 
                  d="M0,0 c6,0 11,5 11,11 v14 c0,6 5,11 11,11 H194" 
                  fill="none" 
                  stroke="var(--border-default)" 
                  strokeWidth="1"
                  transform="translate(0, 0.5)"
                />
                {/* Path 3: The Rounded Corner Tip */}
                <path 
                  d="M194,36 Q200,36 200,42" 
                  fill="none" 
                  stroke="var(--border-default)" 
                  strokeWidth="1"
                  transform="translate(-0.5, 0.5)"
                />
              </svg>
            </div>

            {/* Stats positioned in the cutout space */}
            <div className="folder-stats">
              <div className="stat-item">
                <div className="stat-count">{gameState.cycle || 0}</div>
                <div className="stat-label">CYCLE</div>
              </div>
              <div className="stats-separator" />
              <div className="stat-item">
                <div className="stat-count">{gameState.actions.toLocaleString()}</div>
                <div className="stat-label">ACTIONS</div>
              </div>
              <div className="stats-separator" />
              <div className="stat-item">
                <div className="stat-count">{formatLargeNumber(gameState.tokensUsed)}</div>
                <div className="stat-label">TOKENS</div>
              </div>
            </div>

            {/* Folder Content */}
            <div className="folder-content">
              {/* Goals with TUI box styling */}
              <div className="goals-log">
                <span className="goals-log__label">LONG-TERM GOALS</span>
                {(gameState.goals.primary === "Initializing..." || gameState.goals.primary === "Loading...") ? (
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    height: '100%',
                    opacity: 0.7 
                  }}>
                    <p style={{ textAlign: 'center' }}>
                      Initializing goals<AnimatedDots />
                    </p>
                  </div>
                ) : (
                  <div className="goals-log__content">
                    <p><strong>1. </strong> {gameState.goals.primary}</p>
                    <p><strong>2. </strong> {gameState.goals.secondary}</p>
                    <p><strong>3. </strong> {gameState.goals.tertiary}</p>
                    <p><strong>NOTES: </strong> {gameState.otherGoals}</p>
                  </div>
                )}
              </div>

              {/* Character Container (2-column layout) */}
              <div className="character-container">
                {/* Left Column - Commentary */}
                <div className="character-container__left">
                  {/* 
                    Commentary display states:
                    1. TTS playing: synced typewriter animation
                    2. Linger period (6s after TTS): static completed text
                    3. Waiting: animated ellipsis placeholder
                  */}
                  <div className="character-container__commentary">
                    <span className="character-container__commentary-label">COMMENTARY</span>
                    <p className="character-container__commentary-text">
                      {ttsCommentary?.playing ? (
                        // State 1: TTS is playing - show synced typewriter
                        <SyncedTypewriterText 
                          key={ttsCommentary.text} // Force remount on new text
                          text={ttsCommentary.text} 
                          durationMs={ttsCommentary.duration_ms}
                          onComplete={() => handleTtsComplete(ttsCommentary.text)}
                        />
                      ) : lingerText ? (
                        // State 2: TTS just finished - show full text for 6 seconds with highlights
                        <HighlightedCommentary text={lingerText} />
                      ) : (
                        // State 3: Waiting for next TTS - show animated ellipsis
                        <AnimatedEllipsis interval={600} />
                      )}
                    </p>
                  </div>
                  <div className="character-container__spacer" />
                </div>
                
                {/* Right Column - Character Image */}
                <div className="character-container__right">
                  <TalkingCharacter 
                    baseImage={avatarImage}
                    isSpeaking={ttsCommentary?.playing ?? false}
                    className="lass-character"
                    alt="Lass Pokemon Trainer"
                    speakFrameCount={3}
                    speakInterval={120}
                  />
                </div>
              </div>
            </div>

            {/* Sponsor Section - Bottom Right */}
            <div className="folder-sponsor">
              <div style={{ position: 'relative', width: '64px', height: '64px' }}>
                <img 
                  src={sponsors[sponsorIndex].image} 
                  alt={sponsors[sponsorIndex].alt} 
                  className="folder-sponsor__image"
                  style={{ width: '100%', height: '100%' }}
                />
                
                {/* CRT Static Overlay */}
                {isSponsorSwitching && (
                   <div style={{ position: 'absolute', inset: 0, background: '#111', zIndex: 60, borderRadius: '4px', overflow: 'hidden' }}>
                     <div className="vision-screenshot__static-overlay" style={{ mixBlendMode: 'normal', opacity: 0.6 }} />
                   </div>
                )}
              </div>
              
              <a href={sponsors[sponsorIndex].link} target="_blank" rel="noopener noreferrer" className="folder-sponsor__link">
                {sponsors[sponsorIndex].text}
              </a>
            </div>
          </div>
        </div>

        {/* Center Column - Badges + Game Feed and Team */}
        <div className="pokemon-center-col">
          {/* Badges at top of center column */}
          <div className="column-header column-header--center">
            <div className="badges-widget">

              <div className="gym-badges">
                {ALL_BADGE_TYPES.map((badgeType) => {
                  const badgeInfo = KANTO_BADGES[badgeType];
                  const isEarned = badges.includes(badgeType);
                  return (
                    <div
                      key={badgeType}
                      className={`gym-badge ${isEarned ? 'earned' : 'unearned'}`}
                    >
                      <img 
                        src={badgeInfo.image} 
                        alt=""
                        className="gym-badge-image"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          </div>



          <div className="pokemon-game-feed">
            <div className="game-placeholder">
              Pokemon Game Feed Placeholder
            </div>
          </div>

          <div className="status">
            <span>
              {wsConnected ? (
                <>
                  <SessionTimer sessionStartTime={gameState.sessionStartTime} />
                </>
              ) : (
                <>Connecting<AnimatedEllipsis interval={400} /></>
              )}
            </span>
            <span
              className={`ws-status ${wsConnected ? "connected" : "disconnected"}`}
            >
              • {wsConnected ? "Connected" : "Disconnected"}
            </span>
            {wsConnected && (
              <span className="cycle-timing">
                Cycle: <LiveCycleTimer 
                  cycleNumber={gameState.cycle} 
                />
                {gameState.prevCycleTime !== undefined && gameState.prevCycleTime > 0 && (
                  <> | Prev: {gameState.prevCycleTime}s</>
                )}
                {gameState.avgCycleTime !== undefined && gameState.avgCycleTime > 0 && (
                  <> | Avg: {gameState.avgCycleTime}s</>
                )}
              </span>
            )}
          </div>

          <div className="pokemon-team-section">
            <PokemonTeamBar 
              pokemon={currentPokemon}
              minimapLocation={location}
              minimapTimestamp={gameState.minimapTimestamp ? gameState.minimapTimestamp.toString() : undefined}
              minimapVisible={gameState.minimapVisible}
              explorationPct={gameState.explorationPct}
              lassMarkings={gameState.lassMarkings}
              minimapGridSize={gameState.minimapGridSize}
            />
          </div>
        </div>

        {/* Right Column - Title + LLM Analysis */}
        <div className="pokemon-right-col analysis-column">
          {/* Title at top of right column */}
          <div className="column-header">
            <div className="title">LLM LETS PLAY: <span className="title-accent">POKEMON RED</span></div>
          </div>
          
          <div className="pokemon-analysis-panel">
          <AnalysisPanel
              logs={logs}
              totalActions={gameState.actions}
              animateActions={gameState.animateActions}
              isProcessing={
                !!gameState.processingStatus ||
                gameState.gameStatus === "Thinking..." || 
                gameState.gameStatus === "Processing..." ||
                gameState.gameStatus === "Running..." ||
                gameState.gameStatus.includes("Auto")
              }
              processingStatus={gameState.processingStatus}
              memoryWrite={memoryWrite}
              onMemoryWriteClear={onMemoryWriteClear}
              debugMode={gameState.debugMode}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
