import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PixelLoadingCircle, PixelEye, PixelBrain, PixelSpeaker, PixelAttack, PixelExternalLink, PixelMessage, PixelTerminal } from '../icons/PixelIcons'

const TOKEN_ADDRESS = '0x000...000'
const COPY_RATE_LIMIT_MS = 500

interface FloatingText {
  id: number
  x: number
}

export function StreamCycle() {
  const [floatingTexts, setFloatingTexts] = useState<FloatingText[]>([])
  const lastCopyTime = useRef(0)
  const nextId = useRef(0)

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
        <div className="persona-cards-desktop">
          
          {/* Card 1: Game Loop */}
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

          {/* Card 2: Process Stages */}
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
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelSpeaker size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Reaction:</strong> Generating speech & commentary
                </div>
              </div>
            </div>
          </div>

          {/* Card 3: Commentary Types */}
          <div className="info-card info-card--dotted">
            <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
              <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>COMMENTARY TYPES</h4>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelSpeaker size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Cycle Commentary:</strong> Reacts to game events in real-time (Priority 100)
                </div>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelMessage size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Chat Interaction:</strong> Responds to Twitch chat asynchronously (Priority 50)
                </div>
              </div>
            </div>
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
              borderRadius: '12px',
              cursor: 'pointer',
              position: 'relative',
              boxShadow: '4px 4px 0px rgba(0,0,0,0.2)'
            }}
          >
            <div style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '12px',
              fontWeight: 'bold',
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              CA: {TOKEN_ADDRESS}
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px'
            }}>
              <PixelExternalLink size={16} />
            </div>
            
            {/* Floating +1s for click feedback */}
            {floatingTexts.map(float => (
              <div
                key={float.id}
                className="pixel-float-text"
                style={{
                  left: `calc(50% + ${float.x}px)`
                }}
              >
                COPIED!
              </div>
            ))}
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
