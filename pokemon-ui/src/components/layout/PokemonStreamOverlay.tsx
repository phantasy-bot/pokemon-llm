import type {
  PokemonGameState,
  LogEntry,
  BadgeType,
  Pokemon,
} from "../../types/gameTypes";
import type { PokemonDisplay } from "../../types/display";
import { AnalysisPanel } from "../analysis/AnalysisPanel";
import { Minimap } from "../pokemon/Minimap";
import { PokemonTeamBar } from "../pokemon/PokemonTeamBar";
import "./PokemonStreamOverlay.css";

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

interface PokemonStreamOverlayProps {
  gameState: PokemonGameState;
  wsConnected: boolean;
  logs: LogEntry[];
  memoryWrite?: string | null;
  onMemoryWriteClear?: () => void;
}

export function PokemonStreamOverlay({
  gameState,
  wsConnected,
  logs,
  memoryWrite,
  onMemoryWriteClear,
}: PokemonStreamOverlayProps) {
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
  const badges = gameState.badges || [];
  const location = gameState.minimapLocation || "Unknown Area";

  return (
    <div className="pokemon-stream-overlay">
      {/* Header with Pokemon theming */}
      <div className="pokemon-header">
        {/* Left side - Title with Model Badge */}
        <div className="pokemon-header__left">
          <div className="title-section">
            <div className="title">LLM PLAYS POKÉMON</div>
            <div className="model-badge">{gameState.modelName}</div>
          </div>
        </div>

        {/* Center - Badges */}
        <div className="pokemon-header__center">
          <div className="badges-widget">
            <div className="widget-title">BADGES - {badges.length}/8</div>
            <div className="badges">
              {ALL_BADGE_TYPES.map((badgeType) => {
                const badgeInfo = KANTO_BADGES[badgeType];
                const isEarned = badges.includes(badgeType);
                return (
                  <div
                    key={badgeType}
                    className={`badge ${isEarned ? 'earned' : 'unearned'}`}
                    title={badgeInfo.name}
                  >
                    <img 
                      src={badgeInfo.image} 
                      alt={badgeInfo.name}
                      className="badge-image"
                    />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right side - Tokens and Actions */}
        <div className="pokemon-header__right">
          <div className="stats-row">
            <div className="stat-item">
              <div className="stat-count">
                {formatLargeNumber(gameState.tokensUsed)}
              </div>
              <div className="stat-label">TOKENS</div>
            </div>
            <div className="stat-item">
              <div className="stat-count">
                {gameState.actions.toLocaleString()}
              </div>
              <div className="stat-label">ACTIONS</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div className="pokemon-content">
        {/* Left Column - Battle Log Only */}
        <div className="pokemon-left-col">
          <div className="pokemon-analysis-panel">
            <AnalysisPanel
            logs={logs}
            isProcessing={
              gameState.gameStatus === "Thinking..." || 
              gameState.gameStatus === "Processing..." ||
              gameState.gameStatus === "Running..." ||
              gameState.gameStatus.includes("Auto")
            }
            totalActions={gameState.actions}
            memoryWrite={memoryWrite}
            onMemoryWriteClear={onMemoryWriteClear}
          />
          </div>
        </div>

        {/* Center Column - Goals and Minimap */}
        <div className="pokemon-goals">
          <div className="goals-log">
            <h3>Primary Goal</h3>
            <p className="log-entry">{gameState.goals.primary}</p>
            <h3>Secondary Goal</h3>
            <p className="log-entry">{gameState.goals.secondary}</p>
            <h3>Tertiary Goal</h3>
            <p className="log-entry">{gameState.goals.tertiary}</p>
            <h3>Other Notes</h3>
            <p className="log-entry">{gameState.otherGoals}</p>
          </div>
          {/* Minimap Overlay */}
          <Minimap
            location={location}
            visible={gameState.minimapVisible}
            className="minimap-overlay"
            timestamp={logs.length > 0 ? (logs[0].timestamp || Date.now()).toString() : Date.now().toString()}
          />
        </div>

        {/* Right Column - Game Status, Game Feed and Team */}
        <div className="pokemon-right-col">
          <div className="status">
            <span>Game Status: {gameState.gameStatus}</span>
            <span
              className={`ws-status ${wsConnected ? "connected" : "disconnected"}`}
            >
              • {wsConnected ? "Connected" : "Disconnected"}
            </span>
          </div>

          <div className="pokemon-game-feed">
            <div className="game-placeholder">
              Pokemon Game Feed Placeholder
            </div>
          </div>

          {/* Pokemon Team Bar */}
          <div className="pokemon-team-section">
            <PokemonTeamBar pokemon={currentPokemon} />
          </div>
        </div>
      </div>
    </div>
  );
}
