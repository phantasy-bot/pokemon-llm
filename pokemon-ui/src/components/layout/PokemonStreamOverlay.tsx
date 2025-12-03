import type {
  PokemonGameState,
  LogEntry,
  BadgeType,
  Pokemon,
} from "../../types/gameTypes";
import type { PokemonDisplay } from "../../types/display";
import { BattleLog } from "../battle/BattleLog";
import { Minimap } from "../pokemon/Minimap";
import { PokemonTeamBar } from "../pokemon/PokemonTeamBar";
import "./PokemonStreamOverlay.css";

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
}

export function PokemonStreamOverlay({
  gameState,
  wsConnected,
  logs,
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
        <div className="pokemon-header__stats">
          <div className="pokemon-stats-widget">
            <div className="pokemon-stats-widget__actions-container">
              <div className="widget-title">ACTIONS</div>
              <div className="actions-count">
                {gameState.actions.toLocaleString()}
              </div>
              <div className="subinfo">
                <span>Model: {gameState.modelName}</span>
                <span>Tokens: {gameState.tokensUsed.toLocaleString()}</span>
                <span>
                  GG: T-{gameState.ggValue !== null ? gameState.ggValue : "N/A"}{" "}
                  | Summary: T-
                  {gameState.summaryValue !== null
                    ? gameState.summaryValue
                    : "N/A"}
                </span>
              </div>
            </div>
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
          <div className="title">LLM PLAYS POKÉMON</div>
        </div>

        {/* Main content area */}
        <div className="pokemon-content">
          {/* Left Column - Battle Log */}
          <div className="pokemon-left-col">
            <div className="status">
              <span>Game Status: {gameState.gameStatus}</span>
              <span
                className={`ws-status ${wsConnected ? "connected" : "disconnected"}`}
              >
                • {wsConnected ? "Connected" : "Disconnected"}
              </span>
            </div>

            <div className="pokemon-battle-log">
              <BattleLog logs={logs} />
            </div>
          </div>

          {/* Center Column - Goals */}
          <div className="pokemon-goals">
            <div className="goals-log">
              <h3>Primary Goal</h3>
              <p className="log-entry">{gameState.goals.primary}</p>
              <h3>Secondary Goals</h3>
              <ul>
                <li className="log-entry">{gameState.goals.secondary}</li>
              </ul>
              <h3>Tertiary Goal</h3>
              <p className="log-entry">{gameState.goals.tertiary}</p>
              <h3>Other Notes</h3>
              <p className="log-entry">{gameState.otherGoals}</p>
            </div>
          </div>

          {/* Right Column - Minimap and Team */}
          <div className="pokemon-right-col">
            <div className="pokemon-game-feed">
              <div className="game-placeholder">
                Pokemon Game Feed Placeholder
              </div>
              <Minimap
                location={location}
                visible={gameState.minimapVisible}
                className="pokemon-minimap"
              />
            </div>

            {/* Pokemon Team Bar */}
            <div className="pokemon-team-section">
              <PokemonTeamBar pokemon={currentPokemon} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
