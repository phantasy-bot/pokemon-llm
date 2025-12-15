import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { PixelExternalLink } from '../icons/PixelIcons'

// Sample battle data for display
const SAMPLE_PLAYER_POKEMON = {
  name: 'CHARMANDER',
  nickname: 'SPARKY',
  level: 12,
  hp: 32,
  maxHp: 38,
  types: ['Fire'],
  sprite: '/sprites/charmander.png',
  status: null,
}

const SAMPLE_ENEMY_POKEMON = {
  name: 'PIDGEY',
  level: 11,
  hpPercent: 45, // Enemy HP shown as percentage (we don't know exact values)
  types: ['Normal', 'Flying'],
  sprite: '/sprites/pidgey.png',
  status: null,
}

const SAMPLE_BATTLE_LOG = [
  { id: 1, text: "A wild PIDGEY appeared!", type: 'system' },
  { id: 2, text: "Go! SPARKY!", type: 'player' },
  { id: 3, text: "SPARKY used Ember!", type: 'player-action' },
  { id: 4, text: "It's super effective!", type: 'effective' },
  { id: 5, text: "Wild PIDGEY used Gust!", type: 'enemy-action' },
  { id: 6, text: "SPARKY used Scratch!", type: 'player-action' },
]

// Type color map
const TYPE_COLORS: Record<string, string> = {
  Fire: '#ff6b35',
  Water: '#4fc3f7',
  Grass: '#81c784',
  Electric: '#ffd54f',
  Normal: '#a8a878',
  Flying: '#a890f0',
  Poison: '#a040a0',
  Ground: '#e0c068',
  Rock: '#b8a038', 
  Bug: '#a8b820',
  Ghost: '#705898',
  Steel: '#b8b8d0',
  Psychic: '#f85888',
  Ice: '#98d8d8',
  Dragon: '#7038f8',
  Dark: '#705848',
  Fairy: '#ee99ac',
  Fighting: '#c03028',
}

// HP bar color based on percentage
const getHpColor = (percent: number) => {
  if (percent > 50) return '#4ade80' // Green
  if (percent > 25) return '#fbbf24' // Yellow
  return '#ef4444' // Red
}

// Battle Pokemon Card Component
function BattlePokemonCard({ 
  pokemon, 
  isPlayer = true,
  isEnemy = false,
}: { 
  pokemon: typeof SAMPLE_PLAYER_POKEMON | typeof SAMPLE_ENEMY_POKEMON
  isPlayer?: boolean
  isEnemy?: boolean
}) {
  const hpPercent = 'hp' in pokemon 
    ? (pokemon.hp / pokemon.maxHp) * 100 
    : pokemon.hpPercent
  
  const displayName = 'nickname' in pokemon && pokemon.nickname 
    ? pokemon.nickname 
    : pokemon.name

  return (
    <div className={`battle-pokemon-card ${isPlayer ? 'battle-pokemon-card--player' : 'battle-pokemon-card--enemy'}`}>
      {/* Pokemon Sprite Area */}
      <div className="battle-pokemon-sprite-container">
        <div className="battle-pokemon-sprite-glow" />
        <div 
          className="battle-pokemon-sprite"
          style={{
            backgroundImage: `url(${pokemon.sprite})`,
            transform: isEnemy ? 'scaleX(-1)' : 'none'
          }}
        >
          {/* Fallback gradient if sprite doesn't load */}
          <div className="battle-pokemon-sprite-fallback">
            {pokemon.name[0]}
          </div>
        </div>
      </div>

      {/* Info Panel */}
      <div className="battle-pokemon-info">
        <div className="battle-pokemon-header">
          <span className="battle-pokemon-name">{displayName}</span>
          <span className="battle-pokemon-level">Lv.{pokemon.level}</span>
        </div>

        {/* Type Badges */}
        <div className="battle-pokemon-types">
          {pokemon.types.map(type => (
            <span 
              key={type}
              className="battle-pokemon-type-badge"
              style={{ backgroundColor: TYPE_COLORS[type] || '#888' }}
            >
              {type}
            </span>
          ))}
        </div>

        {/* HP Bar */}
        <div className="battle-hp-container">
          <span className="battle-hp-label">HP</span>
          <div className="battle-hp-bar">
            <div 
              className="battle-hp-fill"
              style={{ 
                width: `${hpPercent}%`,
                backgroundColor: getHpColor(hpPercent)
              }}
            />
            <div className="battle-hp-shine" />
          </div>
          {'hp' in pokemon ? (
            <span className="battle-hp-text">{pokemon.hp}/{pokemon.maxHp}</span>
          ) : (
            <span className="battle-hp-text battle-hp-text--unknown">???</span>
          )}
        </div>

        {/* Status Effect */}
        {pokemon.status && (
          <div className="battle-pokemon-status">
            <span className="battle-status-badge">{pokemon.status}</span>
          </div>
        )}
      </div>
    </div>
  )
}

// Battle Log Component
function BattleLog({ entries }: { entries: typeof SAMPLE_BATTLE_LOG }) {
  return (
    <div className="battle-log">
      <div className="battle-log-header">
        <span className="battle-log-title">⚔️ BATTLE LOG</span>
      </div>
      <div className="battle-log-entries">
        {entries.map((entry, index) => (
          <div 
            key={entry.id}
            className={`battle-log-entry battle-log-entry--${entry.type}`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <span className="battle-log-arrow">▸</span>
            {entry.text}
          </div>
        ))}
      </div>
    </div>
  )
}

// VS Splash Animation Component
function VsSplash({ onComplete }: { onComplete: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onComplete, 2500)
    return () => clearTimeout(timer)
  }, [onComplete])

  return (
    <div className="battle-vs-splash">
      <div className="battle-vs-lightning battle-vs-lightning--left" />
      <div className="battle-vs-text">VS</div>
      <div className="battle-vs-lightning battle-vs-lightning--right" />
      <div className="battle-vs-burst" />
    </div>
  )
}

// Main Battle Component
export function Battle() {
  const [showVsSplash, setShowVsSplash] = useState(true)
  const [battleStarted, setBattleStarted] = useState(false)

  const handleSplashComplete = () => {
    setShowVsSplash(false)
    setBattleStarted(true)
  }

  return (
    <div className="battle-layout">
      {/* VS Splash Overlay */}
      {showVsSplash && <VsSplash onComplete={handleSplashComplete} />}

      {/* Main Battle Content */}
      <div className={`battle-content ${battleStarted ? 'battle-content--active' : ''}`}>
        
        {/* Battle Arena - Top Section */}
        <div className="battle-arena">
          {/* Decorative Elements */}
          <div className="battle-arena-bg">
            <div className="battle-arena-gradient" />
            <div className="battle-arena-scanlines" />
          </div>

          {/* Pokemon Battle Area */}
          <div className="battle-pokemon-field">
            {/* Player Side */}
            <div className="battle-side battle-side--player">
              <BattlePokemonCard pokemon={SAMPLE_PLAYER_POKEMON} isPlayer />
              <div className="battle-side-label">YOUR POKEMON</div>
            </div>

            {/* VS Divider */}
            <div className="battle-vs-divider">
              <div className="battle-vs-icon">⚡</div>
              <div className="battle-vs-line" />
              <div className="battle-vs-icon">⚡</div>
            </div>

            {/* Enemy Side */}
            <div className="battle-side battle-side--enemy">
              <BattlePokemonCard pokemon={SAMPLE_ENEMY_POKEMON} isEnemy />
              <div className="battle-side-label">WILD POKEMON</div>
            </div>
          </div>
        </div>

        {/* Bottom Section - Character + Battle Log */}
        <div className="battle-bottom-section">
          {/* Battle Log */}
          <div className="battle-log-container">
            <BattleLog entries={SAMPLE_BATTLE_LOG} />
          </div>

          {/* Lass Character with Holographic Effect */}
          <div className="battle-character-container">
            <div className="holographic-afterimage battle-holographic">
              {/* Stationary ghosts */}
              <img src="/lass/lass-victory.png" alt="" className="ghost-layer ghost-1" aria-hidden="true" />
              <img src="/lass/lass-victory.png" alt="" className="ghost-layer ghost-2" aria-hidden="true" />
              <img src="/lass/lass-victory.png" alt="" className="ghost-layer ghost-3" aria-hidden="true" />
              
              {/* Main character */}
              <img src="/lass/lass-victory.png" alt="Lass in Battle" className="main-character battle-main-character" />
            </div>
          </div>

          {/* Right Column - Stats and Actions */}
          <div className="battle-stats-column">
            {/* Battle Stats Card */}
            <div className="battle-stats-card">
              <div className="battle-stats-header">BATTLE STATS</div>
              <div className="battle-stat-row">
                <span className="battle-stat-label">TURNS</span>
                <span className="battle-stat-value">3</span>
              </div>
              <div className="battle-stat-row">
                <span className="battle-stat-label">DAMAGE</span>
                <span className="battle-stat-value">42</span>
              </div>
              <div className="battle-stat-row">
                <span className="battle-stat-label">ITEMS</span>
                <span className="battle-stat-value">0</span>
              </div>
            </div>

            {/* Spacer */}
            <div style={{ flex: 1 }} />

            {/* Action Buttons */}
            <div className="battle-actions">
              <Link 
                to="/lass" 
                className="pushdown-button battle-action-btn"
              >
                ← BACK
              </Link>
              <a 
                href="https://twitch.tv/llmletsplay" 
                target="_blank" 
                rel="noreferrer" 
                className="pushdown-button battle-action-btn battle-action-btn--twitch"
              >
                WATCH LIVE
                <PixelExternalLink size={12} />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
