import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PixelChip, PixelEye, PixelBrain, PixelHierarchy, PixelSpeaker, PixelExternalLink } from '../icons/PixelIcons'

const TOKEN_ADDRESS = '0x000...000'
const COPY_RATE_LIMIT_MS = 500

interface FloatingText {
  id: number
  x: number
}

export function Architecture() {
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
      {/* LEFT COLUMN - Architecture Info */}
      <div className="persona-cards-column">
        <div className="persona-cards-desktop">
          
          {/* Card 1: System Overview */}
          <div className="info-card">
            <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
              <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>SYSTEM ARCHITECTURE</h4>
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
                The agent operates on a continuous perception-action loop. It observes the game state through visual and memory inputs, reasons about the best next move, and executes precise controller inputs.
              </p>
              <p>
                This closed-loop system allows Lass to navigate complex environments, battle trainers, and progress through the story autonomously.
              </p>
            </div>
          </div>

          {/* Card 2: Core Stack */}
          <div className="info-card info-card--dotted">
            <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
              <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>CORE STACK</h4>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelBrain size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Cognition:</strong> GLM-4 (Strategy & Reasoning)
                </div>
              </div>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelEye size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Vision:</strong> GLM-4V (Visual Analysis)
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelChip size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Environment:</strong> mGBA + Lua Interface
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px dashed rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelHierarchy size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Memory:</strong> Semantic Vector Store
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ color: 'var(--accent-primary-bright)' }}><PixelSpeaker size={24} /></div>
                <div style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                  <strong>Voice:</strong> Chatterbox TTS
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* MIDDLE COLUMN - Character with Holographic Effect */}
      <div className="holographic-afterimage persona-holographic">
        {/* Trail ghosts */}
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-1" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-2" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-3" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-4" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-5" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-6" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-7" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="trail-ghost trail-8" aria-hidden="true" />
        
        {/* Stationary ghosts */}
        <img src="/lass/lass-glasses-thinking.png" alt="" className="ghost-layer ghost-1" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="ghost-layer ghost-2" aria-hidden="true" />
        <img src="/lass/lass-glasses-thinking.png" alt="" className="ghost-layer ghost-3" aria-hidden="true" />
        
        {/* Main character */}
        <img src="/lass/lass-glasses-thinking.png" alt="Lass Thinking" className="main-character" />
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
