import type { PokemonGameState, BadgeType } from "../../types/gameTypes";
import type { PokemonDisplay } from "../../types/display";
import { PokemonTeamBar } from "../pokemon/PokemonTeamBar";

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

// Animated dots component for loading states
function AnimatedEllipsis({ interval = 400 }: { interval?: number }) {
  // Simple implementation - can be imported if shared, or redefined
  const [dots, setDots] = React.useState(0);
  React.useEffect(() => {
    const timer = setInterval(() => setDots(d => (d + 1) % 4), interval);
    return () => clearInterval(timer);
  }, [interval]);
  return <>{'.'.repeat(dots)}</>;
}

// Session timer
function SessionTimer({ sessionStartTime }: { sessionStartTime?: number }) {
  const [elapsed, setElapsed] = React.useState('0h 0m 0s');
  React.useEffect(() => {
    if (!sessionStartTime) return;
    const update = () => {
      const diff = Math.floor((Date.now() - sessionStartTime) / 1000);
      const h = Math.floor(diff / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;
      setElapsed(`${h}h ${m}m ${s}s`);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [sessionStartTime]);
  return <span className="session-timer">{elapsed}</span>;
}

// Live cycle timer
function LiveCycleTimer({ cycleNumber }: { cycleNumber: number }) {
  const [elapsed, setElapsed] = React.useState(0);
  const startRef = React.useRef(Date.now());
  const lastCycleRef = React.useRef(cycleNumber);
  
  React.useEffect(() => {
    const timer = setInterval(() => {
       setElapsed((Date.now() - startRef.current) / 1000);
    }, 100);
    return () => clearInterval(timer);
  }, []);

  React.useEffect(() => {
    if (cycleNumber !== lastCycleRef.current) {
      startRef.current = Date.now();
      setElapsed(0);
      lastCycleRef.current = cycleNumber;
    }
  }, [cycleNumber]);

  return <span className="cycle-timer">{elapsed.toFixed(1)}s</span>;
}

import React from "react";

interface GameStatusDisplayProps {
  gameState: PokemonGameState;
  wsConnected: boolean;
  currentPokemon: PokemonDisplay[];
  hideBadges?: boolean;
}

export function GameStatusDisplay({ gameState, wsConnected, currentPokemon, hideBadges = false }: GameStatusDisplayProps) {
  const badges = gameState.badges || [];
  const location = gameState.minimapLocation || "Unknown Area";

  return (
    <div className="game-status-display">
      {/* Badges at top - hidden when hideBadges is true */}
      {!hideBadges && (
        <div className="column-header column-header--center">
          <div className="badges-widget">
            <div className="gym-badges">
              {ALL_BADGE_TYPES.map((badgeType) => {
                const badgeInfo = KANTO_BADGES[badgeType];
                const isEarned = badges.includes(badgeType);
                return (
                  <div key={badgeType} className={`gym-badge ${isEarned ? 'earned' : 'unearned'}`}>
                    <img src={badgeInfo.image} alt="" className="gym-badge-image" />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Game Feed Placeholder */}
      <div className="pokemon-game-feed">
        <div className="game-placeholder">
          Pokemon Game Feed Placeholder
        </div>
      </div>

      {/* Status Bar */}
      <div className="status">
        <span>
          {wsConnected ? (
            <SessionTimer sessionStartTime={gameState.sessionStartTime} />
          ) : (
            <>Connecting<AnimatedEllipsis interval={400} /></>
          )}
        </span>
        <span className={`ws-status ${wsConnected ? "connected" : "disconnected"}`}>
          • {wsConnected ? "Connected" : "Disconnected"}
        </span>
        {wsConnected && (
          <span className="cycle-timing">
            Cycle: <LiveCycleTimer cycleNumber={gameState.cycle} />
            {gameState.prevCycleTime !== undefined && gameState.prevCycleTime > 0 && (
              <> | Prev: {gameState.prevCycleTime}s</>
            )}
            {gameState.avgCycleTime !== undefined && gameState.avgCycleTime > 0 && (
              <> | Avg: {gameState.avgCycleTime}s</>
            )}
          </span>
        )}
      </div>

      {/* Pokemon Team Bar */}
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
  );
}
