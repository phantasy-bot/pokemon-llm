import { useState, useEffect, useRef, useCallback } from "react";
import type {
  PokemonGameState,
  LogEntry,
  Pokemon,
} from "../../types/gameTypes";
import type { PokemonDisplay } from "../../types/display";
import { AnalysisPanel } from "../analysis/AnalysisPanel";
import { GameStatusDisplay } from "./GameStatusDisplay";
import { RecentActions } from "../shared/RecentActions";
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
 * HighlightedCommentary - Parses commentary text to highlight platform mentions and special tokens
 * - Purple for Twitch mentions: "Username on Twitch"
 * - Green for Pump.fun mentions: "Username on Pump.fun" or "Username on Pump"
 * - Rainbow Holographic for "$LASS"
 */
function HighlightedCommentary({ text }: { text: string }) {
  const parts: React.ReactNode[] = [];
  
  // Combined regex using OR
  // We need to be careful about iteration order.
  // Easiest is to split by a master regex that catches all tokens of interest
  const masterRegex = /((\S+)\s+on\s+(?:Twitch|Pump\.fun|Pump))|(\$LASS)/gi;
  
  let lastIndex = 0;
  let match;
  
  while ((match = masterRegex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    
    const fullMatch = match[0];
    
    // Check which group matched
    if (match[3]) { // $LASS group
      parts.push(
        <span key={match.index} className="text-holographic">
          {fullMatch}
        </span>
      );
    } else if (match[1]) { // Platform mention group
      // We need to extract username/platform from the full match again or use nested groups
      // match[2] is username
      // We need platform. Let's re-parse or use the groups from master regex if careful.
      // match[1] is full string "User on Twitch"
      // match[2] is "User"
      // We need to find "Twitch" or "Pump" in match[1]
      
      // Let's re-run platform regex on just the match string for safety
      const pMatch = /(\S+)\s+on\s+(Twitch|Pump\.fun|Pump)/i.exec(fullMatch);
      if (pMatch) {
        const username = pMatch[1];
        const platform = pMatch[2];
        const isPumpfun = platform.toLowerCase().includes('pump');
        const colorClass = isPumpfun ? 'platform-mention--pumpfun' : 'platform-mention--twitch';
        
        parts.push(
          <span key={match.index} className={`platform-mention ${colorClass}`}>
            {username} on {platform}
          </span>
        );
      } else {
        parts.push(fullMatch); // Fallback
      }
    }
    
    lastIndex = match.index + fullMatch.length;
  }
  
  // Add remaining text after last match
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  
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

  return <HighlightedCommentary text={displayedText} />;
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







// TTS Commentary data from backend
interface TTSCommentary {
  text: string;
  duration_ms: number;
  playing: boolean;
  reply_to?: {
    username: string;
    platform: string;
    message?: string;
  };
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
  // lingerContext: the reply context to show while lingering
  const [lingerContext, setLingerContext] = useState<TTSCommentary['reply_to'] | undefined>(undefined);
  const lingerTimerRef = useRef<number | null>(null);
  
  // Handle TTS completion: start 6-second linger period
  // Text is passed in because ttsCommentary may be cleared by parent before this runs
  const handleTtsComplete = (spokenText: string, context?: TTSCommentary['reply_to']) => {
    if (spokenText) {
      setLingerText(spokenText);
      setLingerContext(context);
      
      // Clear any existing timer
      if (lingerTimerRef.current) {
        clearTimeout(lingerTimerRef.current);
      }
      
      // After 6 seconds, clear the linger text and context
      lingerTimerRef.current = window.setTimeout(() => {
        setLingerText(null);
        setLingerContext(undefined);
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


  // View Mode State: 'detailed' (3-col) or 'normal' (minimal 2-col)
  // Currently hardcoded to 'detailed' - auto-switching disabled for now
  const [viewMode, setViewMode] = useState<'detailed' | 'normal'>('detailed');
  
  // Track manual override to prevent fighting the auto-switcher if user clicked something
  const [manualOverride, setManualOverride] = useState(false);

  // Auto-switching: Minimal view ('normal') during name entry, Detailed view otherwise
  useEffect(() => {
    if (manualOverride) return;
    
    // Check if we are in a naming screen (nameEntryState is populated)
    const isNaming = !!gameState.nameEntryState;
    const targetMode = isNaming ? 'normal' : 'detailed';
    
    if (viewMode !== targetMode) {
      setViewMode(targetMode);
    }
  }, [gameState.nameEntryState, manualOverride, viewMode]);

  const toggleViewMode = () => {
    setManualOverride(true); // Disable auto-switcher if user interacts
    setViewMode(prev => prev === 'detailed' ? 'normal' : 'detailed');
  };

  const isProcessing = !!gameState.processingStatus ||
    gameState.gameStatus === "Thinking..." || 
    gameState.gameStatus === "Processing..." ||
    gameState.gameStatus === "Running..." ||
    gameState.gameStatus.includes("Auto");

  return (
    <div className={`pokemon-stream-overlay mode-${viewMode}`}>
      {/* Click handler on title to toggle view mode (Easter Egg / Control) */}
      <div 
        style={{ position: 'fixed', top: 0, left: 0, width: '20px', height: '20px', zIndex: 9999, cursor: 'pointer' }}
        onClick={toggleViewMode}
        title={`Switch to ${viewMode === 'detailed' ? 'Normal' : 'Detailed'} View`}
      />

      {/* Main content area */}
      <div className="pokemon-content">
        
        {/* Left Col / Main Container 
            In Normal mode: This expands to fill the screen
            In Detailed mode: This is just the left column
        */}
        <div className="pokemon-left-col character-column">
          {/* T3 Folder Container */}
          <div className="folder-container">
            {/* Normal Mode: Header Row with Title + Badges */}
            {viewMode === 'normal' && (
              <div className="folder-header-row">
                <div className="folder-title" onClick={toggleViewMode} style={{ cursor: 'pointer' }}>
                  Lass ✿
                </div>
                <div className="folder-badges">
                  {/* Inline badges for normal mode */}
                  {(['Boulder', 'Cascade', 'Thunder', 'Rainbow', 'Soul', 'Marsh', 'Volcano', 'Earth'] as const).map((badgeType) => {
                    const badgeIndex = ['Boulder', 'Cascade', 'Thunder', 'Rainbow', 'Soul', 'Marsh', 'Volcano', 'Earth'].indexOf(badgeType) + 1;
                    const isEarned = (gameState.badges || []).includes(badgeType);
                    return (
                      <div key={badgeType} className={`gym-badge ${isEarned ? 'earned' : 'unearned'}`}>
                        <img src={`/badges/${badgeIndex}.png`} alt="" className="gym-badge-image" />
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Detailed Mode: Original Title in header bar */}
            {viewMode === 'detailed' && (
              <div className="folder-title" onClick={toggleViewMode} style={{ cursor: 'pointer' }}>
                Lass ✿
              </div>
            )}

            {/* SVG Corner Cutout */}
            <div className="corner-container">
              <svg viewBox="0 0 200 48" className="corner-svg" preserveAspectRatio="none">
                <path 
                  d="M0,0 c6,0 11,5 11,11 v14 c0,6 5,11 11,11 H194 Q200,36 200,42 L200,0 Z" 
                  fill="var(--bg-panel)" 
                  stroke="none"
                />
                <path 
                  d="M0,0 c6,0 11,5 11,11 v14 c0,6 5,11 11,11 H194" 
                  fill="none" 
                  stroke="var(--border-default)" 
                  strokeWidth="1"
                  transform="translate(0, 0.5)"
                />
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

            {/* Folder Content Wrapper */}
            <div className="folder-content-wrapper">
              
              {/* PANE 1: Character & Goals (Always Visible) */}
              <div className="folder-pane folder-pane--left">
                {/* Normal Mode: Goals + "Replying To" Section */}
                {viewMode === 'normal' && (
                  <>
                    {/* Goals Section (Added to Minimal Mode) */}
                    <div className="goals-log" style={{ marginBottom: '16px' }}>
                      <span className="goals-log__label">LONG-TERM GOALS</span>
                      {(gameState.goals.primary === "Initializing..." || gameState.goals.primary === "Loading...") ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.7 }}>
                          <p style={{ textAlign: 'center' }}>Initializing goals<AnimatedDots /></p>
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

                    <div className="minimal-reply-section">
                      <div className="minimal-reply-section__label">REPLYING TO</div>
                      {(ttsCommentary?.reply_to || lingerContext) ? (
                        <div className="minimal-reply-section__content">
                          <span className={`minimal-reply-section__platform minimal-reply-section__platform--${(ttsCommentary?.reply_to?.platform || lingerContext?.platform || 'twitch').toLowerCase().includes('pump') ? 'pumpfun' : 'twitch'}`}>
                            {ttsCommentary?.reply_to?.platform || lingerContext?.platform || 'Twitch'}
                          </span>
                          <span className="minimal-reply-section__user">
                            @{ttsCommentary?.reply_to?.username || lingerContext?.username}
                          </span>
                          <p className="minimal-reply-section__message">
                            "{ttsCommentary?.reply_to?.message || lingerContext?.message}"
                          </p>
                        </div>
                      ) : (ttsCommentary?.playing || lingerText) ? (
                        <div className="minimal-reply-section__game-response">
                          RESPONDING TO GAME
                        </div>
                      ) : (
                        <div className="minimal-reply-section__empty">
                          <span>Waiting for chat messages<AnimatedDots /></span>
                        </div>
                      )}
                    </div>
                  </>
                )}

                  {/* Detailed Mode: Goals Section */}
                {viewMode === 'detailed' && (
                  <div className="folder-content">
                    <div className="goals-log">
                      <span className="goals-log__label">LONG-TERM GOALS</span>
                      {(gameState.goals.primary === "Initializing..." || gameState.goals.primary === "Loading...") ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.7 }}>
                          <p style={{ textAlign: 'center' }}>Initializing goals<AnimatedDots /></p>
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
                    
                    {/* Replying To Section (Compact in Detailed Mode) */}
                    <div className="detailed-reply-section">
                      <span className="detailed-reply-section__label">REPLYING TO</span>
                      {(ttsCommentary?.reply_to || lingerContext) ? (
                        <div className="detailed-reply-section__content">
                          <span className={`detailed-reply-section__platform detailed-reply-section__platform--${(ttsCommentary?.reply_to?.platform || lingerContext?.platform || 'twitch').toLowerCase().includes('pump') ? 'pumpfun' : 'twitch'}`}>
                            {ttsCommentary?.reply_to?.platform || lingerContext?.platform || 'Twitch'}
                          </span>
                          <span className="detailed-reply-section__user">
                            @{ttsCommentary?.reply_to?.username || lingerContext?.username}
                          </span>
                          <span className="detailed-reply-section__message">
                            "{ttsCommentary?.reply_to?.message || lingerContext?.message}"
                          </span>
                        </div>
                      ) : (
                        <span className="detailed-reply-section__empty">Waiting for chat<AnimatedDots /></span>
                      )}
                    </div>
                  </div>
                )}

                {/* Character Container */}
                <div className="character-container">
                  <div className="character-container__left">
                    <div className="character-container__commentary">
                      <span className="character-container__commentary-label">COMMENTARY</span>
                      <p className="character-container__commentary-text">
                        {ttsCommentary?.playing ? (
                          <SyncedTypewriterText 
                            key={ttsCommentary.text} 
                            text={ttsCommentary.text} 
                            durationMs={ttsCommentary.duration_ms}
                            onComplete={() => handleTtsComplete(ttsCommentary.text, ttsCommentary.reply_to)}
                          />
                        ) : lingerText ? (
                          <HighlightedCommentary text={lingerText} />
                        ) : (
                          <AnimatedEllipsis interval={600} />
                        )}                      </p>
                    </div>

                    {/* Recent Actions in Normal/Minimal Mode */}
                    {viewMode === 'normal' && (
                      <div className="character-container__recent-actions">
                        <RecentActions 
                          logs={logs} 
                          totalActions={gameState.actions} 
                          animateTrigger={gameState.animateActions} 
                          isWaitingForAction={!isProcessing}
                          isActive={isProcessing}
                          delayMs={1000}
                        />
                      </div>
                    )}

                    <div className="character-container__spacer" />
                  </div>
                  
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

              {/* PANE 2: Game Status (Only in Normal Mode) */}
              <div className="folder-pane folder-pane--right">
                 {/* This pane is only visible/active in Normal Mode */}
                 <div className="folder-content">
                    <GameStatusDisplay 
                      gameState={gameState} 
                      wsConnected={wsConnected} 
                      currentPokemon={currentPokemon}
                      hideBadges={true}
                    />
                 </div>
              </div>
            </div>

            {/* Sponsor (Bottom Left of Folder) */}
            <div className="folder-sponsor">
              <div style={{ position: 'relative', width: '64px', height: '64px' }}>
                <img 
                  src={sponsors[sponsorIndex].image} 
                  alt={sponsors[sponsorIndex].alt} 
                  className="folder-sponsor__image"
                  style={{ width: '100%', height: '100%' }}
                />
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

        {/* Center Column (Detailed Mode Only) */}
        {viewMode === 'detailed' && (
          <div className="pokemon-center-col">
            <GameStatusDisplay 
              gameState={gameState} 
              wsConnected={wsConnected} 
              currentPokemon={currentPokemon} 
            />
          </div>
        )}

        {/* Right Column (Detailed Mode Only) */}
        {viewMode === 'detailed' && (
          <div className="pokemon-right-col analysis-column">
            <div className="column-header">
              <div className="title">LLM LETS PLAY: <span className="title-accent">POKEMON RED</span></div>
            </div>
            
            <div className="pokemon-analysis-panel">
            <AnalysisPanel
                logs={logs}
                totalActions={gameState.actions}
                animateActions={gameState.animateActions}
                isProcessing={isProcessing}
                processingStatus={gameState.processingStatus}
                memoryWrite={memoryWrite}
                onMemoryWriteClear={onMemoryWriteClear}
                debugMode={gameState.debugMode}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

