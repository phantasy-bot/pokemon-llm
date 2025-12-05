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

// Kanto gym badges with emoji mapping
const KANTO_BADGES: Record<BadgeType, { emoji: string; name: string }> = {
  Boulder: { emoji: "🪨", name: "Boulder Badge" },
  Cascade: { emoji: "💧", name: "Cascade Badge" },
  Thunder: { emoji: "⚡", name: "Thunder Badge" },
  Rainbow: { emoji: "🌈", name: "Rainbow Badge" },
  Soul: { emoji: "💜", name: "Soul Badge" },
  Marsh: { emoji: "🐸", name: "Marsh Badge" },
  Volcano: { emoji: "🌋", name: "Volcano Badge" },
  Earth: { emoji: "🌍", name: "Earth Badge" },
};

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
              {badges.map((badge, i) => {
                const badgeInfo = KANTO_BADGES[badge];
                return (
                  <div
                    key={`${badge}-${i}`}
                    className="badge"
                    title={badgeInfo?.name || badge}
                  >
                    <span className="badge-emoji">
                      {badgeInfo?.emoji || "🔒"}
                    </span>
                  </div>
                );
              })}
              {Array.from({ length: Math.max(0, 8 - badges.length) }).map(
                (_, index) => (
                  <div key={`empty-${index}`} className="badge empty"></div>
                ),
              )}
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
          <div className="pokemon-battle-log">
            <AnalysisPanel
            logs={logs}
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
