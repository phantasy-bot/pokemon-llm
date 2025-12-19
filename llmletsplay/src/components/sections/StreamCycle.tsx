import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PixelEye, PixelBrain, PixelAttack, PixelExternalLink, PixelChatEmail, PixelThinkChat } from '../icons/PixelIcons'

const TOKEN_ADDRESS = '0x000...000'
const COPY_RATE_LIMIT_MS = 500

interface FloatingText {
  id: number
  x: number
}

// Card 1: Game Loop
function GameLoopCard() {
  return (
    <div className="info-card">
      <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>GAME LOOP</h4>
      </div>
      
      <div style={{ 
        fontFamily: 'var(--font-mono)',
        fontSize: '14px',
        lineHeight: '1.6',
        color: 'var(--text-primary)',
        textAlign: 'left',
        marginBottom: '16px'
      }}>
        <p style={{ marginBottom: '16px' }}>
          The heartbeat of the agent. The cycle runs every <strong>25-75 seconds</strong>, balancing game progress with entertaining commentary.
        </p>
        <p>
          Each loop is a discrete step where Lass perceives the world, thinks about her goals, and acts accordingly.
        </p>
      </div>
    </div>
  )
}

// Card 2: Process Stages
function ProcessStagesCard() {
  return (
    <div className="info-card info-card--dotted">
      <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>PROCESS STAGES</h4>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
          <div style={{ color: 'var(--accent-primary-bright)' }}><PixelEye size={24} /></div>
          <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <strong>Observation:</strong> Analyzing screenshots & RAM state
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
          <div style={{ color: 'var(--accent-primary-bright)' }}><PixelBrain size={24} /></div>
          <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <strong>Reasoning:</strong> LLM decides next best move
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
          <div style={{ color: 'var(--accent-primary-bright)' }}><PixelAttack size={24} /></div>
          <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <strong>Action:</strong> Executing precise button inputs
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ color: 'var(--accent-primary-bright)' }}><PixelThinkChat size={24} /></div>
          <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <strong>Reaction:</strong> Generating speech & commentary
          </div>
        </div>
      </div>
    </div>
  )
}

// Card 3: Commentary Types
function CommentaryTypesCard() {
  return (
    <div className="info-card info-card--dotted">
      <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>COMMENTARY TYPES</h4>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
          <div style={{ color: 'var(--accent-primary-bright)' }}><PixelThinkChat size={24} /></div>
          <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <strong>Cycle Commentary:</strong> Reacts to game events in real-time (Priority 100)
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ color: 'var(--accent-primary-bright)' }}><PixelChatEmail size={24} /></div>
          <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
            <strong>Chat Interaction:</strong> Responds to Twitch chat asynchronously (Priority 50)
          </div>
        </div>
      </div>
    </div>
  )
}

export function StreamCycle() {
  const [floatingTexts, setFloatingTexts] = useState<FloatingText[]>([])
  const [activeCardIndex, setActiveCardIndex] = useState(0)
  const lastCopyTime = useRef(0)
  const nextId = useRef(0)

  const totalCards = 3

  const handleCopy = () => {
    const now = Date.now()
    if (now - lastCopyTime.current < COPY_RATE_LIMIT_MS) {
      return // Rate limited
    }
    lastCopyTime.current = now

    navigator.clipboard.writeText(TOKEN_ADDRESS)
    
    // Add a new floating text with random x offset
    const newFloat: FloatingText = {
      id: nextId.current++,
      x: Math.random() * 60 - 30 // Random offset between -30px and 30px
    }
    setFloatingTexts(prev => [...prev, newFloat])
    
    // Remove after animation completes (1s)
    setTimeout(() => {
      setFloatingTexts(prev => prev.filter(f => f.id !== newFloat.id))
    }, 1000)
  }

  return (
    <div className="persona-layout">
      {/* LEFT COLUMN - Stream Cycle Info */}
      <div className="persona-cards-column">
        {/* Desktop: Show all cards */}
        <div className="persona-cards-desktop">
          <GameLoopCard />
          <ProcessStagesCard />
          <CommentaryTypesCard />
        </div>

        {/* Mobile: Carousel */}
        <div className="persona-cards-mobile">
          <div className="persona-card-carousel">
            {activeCardIndex === 0 && <GameLoopCard />}
            {activeCardIndex === 1 && <ProcessStagesCard />}
            {activeCardIndex === 2 && <CommentaryTypesCard />}
          </div>
          
          {/* Navigation */}
          <div className="persona-card-nav">
            <button 
              className="persona-card-nav-btn"
              onClick={() => setActiveCardIndex(prev => prev === 0 ? totalCards - 1 : prev - 1)}
            >
              &#9664;
            </button>
            <div className="mobile-dots">
              {Array.from({ length: totalCards }).map((_, i) => (
                <span 
                  key={i} 
                  className={`mobile-dot ${i === activeCardIndex ? 'active' : ''}`}
                  onClick={() => setActiveCardIndex(i)}
                />
              ))}
            </div>
            <button 
              className="persona-card-nav-btn"
              onClick={() => setActiveCardIndex(prev => prev === totalCards - 1 ? 0 : prev + 1)}
            >
              &#9654;
            </button>
          </div>
        </div>
      </div>

      {/* MIDDLE COLUMN - Character with Holographic Effect */}
      <div className="holographic-afterimage persona-holographic">
        {/* Trail ghosts */}
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-1" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-2" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-3" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-4" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-5" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-6" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-7" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="trail-ghost trail-8" aria-hidden="true" />
        
        {/* Stationary ghosts */}
        <img src="/lass/lass-victory.png" alt="" className="ghost-layer ghost-1" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="ghost-layer ghost-2" aria-hidden="true" />
        <img src="/lass/lass-victory.png" alt="" className="ghost-layer ghost-3" aria-hidden="true" />
        
        {/* Main character */}
        <img src="/lass/lass-victory.png" alt="Lass Victory" className="main-character" />
      </div>

      {/* RIGHT COLUMN - Sponsor Image + Buttons */}
      <div className="persona-right-column">
        {/* Phantasy Agent Framework - links to phantasy.bot */}
        <a 
          href="https://phantasy.bot" 
          target="_blank" 
          rel="noopener noreferrer"
          className="persona-sponsor-link"
          style={{ textDecoration: 'none' }}
        >
          <img 
            src="/sponsors/phantasy.png" 
            alt="Phantasy" 
            style={{
              width: '100%',
              height: 'auto',
              imageRendering: 'pixelated',
              borderRadius: '8px'
            }}
          />
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            color: 'rgba(0,0,0,0.4)',
            textAlign: 'center',
            marginTop: '6px'
          }}>
            agent framework
          </div>
        </a>
        
        {/* Spacer to push buttons to bottom */}
        <div style={{ flex: 1 }} />
        
        {/* Button stack at bottom */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          width: '100%',
          overflow: 'visible'
        }}>
          {/* CA Widget */}
          <div 
            onClick={handleCopy}
            className="pushdown-button"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              padding: '10px 12px',
              background: 'var(--cream)',
              border: '2px solid var(--text-primary)',
              borderRadius: '10px',
              fontFamily: 'var(--font-display)',
              fontSize: '12px',
              letterSpacing: '1px',
              cursor: 'pointer',
              boxShadow: '3px 3px 0 rgba(0,0,0,0.12)',
              position: 'relative',
              overflow: 'visible'
            }}
          >
            {floatingTexts.map(ft => (
              <span
                key={ft.id}
                style={{
                  position: 'absolute',
                  top: '-20px',
                  left: `calc(50% + ${ft.x}px)`,
                  transform: 'translateX(-50%)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  color: 'var(--accent-primary)',
                  pointerEvents: 'none',
                  animation: 'floatUp 1s ease-out forwards'
                }}
              >
                copied
              </span>
            ))}
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--text-primary)',
              userSelect: 'none',
              whiteSpace: 'nowrap'
            }}>
              {`CA: ${TOKEN_ADDRESS.slice(0, 5)}...${TOKEN_ADDRESS.slice(-3)}`}
            </span>
            <a 
              href={`https://pump.fun/${TOKEN_ADDRESS}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-primary)'
              }}
              title="View on Pump.fun"
            >
              <PixelExternalLink size={14} />
            </a>
          </div>

          <div style={{
            width: '95%',
            height: '2px', // Height of the dots
            margin: '4px auto', // Centered with margin
            background: 'radial-gradient(circle, var(--text-primary) 1px, transparent 1px)',
            backgroundSize: '6px 2px', // Spacing of dots
            opacity: 0.3
          }} />

          <Link 
            to="/lass" 
            className="pushdown-button"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '8px 12px',
              background: 'var(--cream)',
              border: '2px solid var(--accent-primary)',
              borderRadius: '10px',
              textDecoration: 'none',
              color: 'var(--text-primary)',
              fontWeight: 'bold',
              fontFamily: 'var(--font-display)',
              letterSpacing: '1px',
              boxShadow: '3px 3px 0 rgba(0,0,0,0.12)',
              fontSize: '12px'
            }}
          >
            READ DOCS
          </Link>
          
          <a
            href="https://twitch.tv/lassplayspokemon"
            target="_blank"
            rel="noopener noreferrer"
            className="pushdown-button"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '8px 12px',
              background: '#9146FF',
              border: '2px solid #9146FF',
              borderRadius: '10px',
              textDecoration: 'none',
              color: 'white',
              fontWeight: 'bold',
              fontFamily: 'var(--font-display)',
              letterSpacing: '1px',
              boxShadow: '3px 3px 0 rgba(0,0,0,0.12)',
              fontSize: '12px'
            }}
          >
            WATCH STREAM
          </a>
        </div>
      </div>
    </div>
  )
}
