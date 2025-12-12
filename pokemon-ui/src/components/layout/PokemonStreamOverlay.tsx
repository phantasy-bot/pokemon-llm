import { useState, useEffect, useRef } from "react";
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

// Typewriter text component - fixed speed per character (kept as fallback)


// Animated ellipsis placeholder: '' -> '.' -> '..' -> '...' -> '' -> ...
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
function LiveCycleTimer({ 
  cycleNumber, 
}: { 
  cycleNumber: number; 
}) {
  const [elapsedTime, setElapsedTime] = useState(0); // Always start at 0
  const [isFlashing, setIsFlashing] = useState(false);
  const lastCycleRef = useRef<number | null>(null); // Start as null to detect first render
  const timerRef = useRef<number | null>(null);

  // Tick every 0.1 second
  useEffect(() => {
    timerRef.current = window.setInterval(() => {
      setElapsedTime(prev => prev + 0.1);
    }, 100); // 100ms = 0.1s

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Reset timer and flash when cycle changes
  useEffect(() => {
    // First render: just set the ref, don't reset (timer already at 0)
    if (lastCycleRef.current === null) {
      lastCycleRef.current = cycleNumber;
      return;
    }
    
    // Subsequent renders: reset if cycle changed
    if (cycleNumber !== lastCycleRef.current) {
      // Cycle completed - flash and reset to 0
      setIsFlashing(true);
      setTimeout(() => setIsFlashing(false), 500);
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

    // 6. Default State (Overworld/Exploration) -> Animated
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
                        // State 2: TTS just finished - show full text for 6 seconds
                        <>{lingerText}</>
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
                  <img 
                    src={avatarImage}
                    alt="Lass Pokemon Trainer" 
                    className="lass-character"
                    // Add key to force re-animation if needed, or just let src swap
                    key={avatarImage} 
                  />
                </div>
              </div>
            </div>

            {/* Sponsor Section - Bottom Right */}
            <div className="folder-sponsor">
              <img 
                src="/sponsors/mystery-gift.png" 
                alt="Mystery Gift Sponsor" 
                className="folder-sponsor__image"
              />
              <a href="https://mysterygift.fun" target="_blank" rel="noopener noreferrer" className="folder-sponsor__link">
                mysterygift.fun
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
              Game Status: {wsConnected ? gameState.gameStatus : (<>Connecting<AnimatedEllipsis interval={400} /></>)}
              {wsConnected && gameState.sessionStartTime && (
                <> | <SessionTimer sessionStartTime={gameState.sessionStartTime} /></>
              )}
            </span>
            <span
              className={`ws-status ${wsConnected ? "connected" : "disconnected"}`}
            >
              • {wsConnected ? "Connected" : "Disconnected"}
            </span>
            {wsConnected && gameState.cyclesEnabled && (
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
