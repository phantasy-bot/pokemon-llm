import { useState, useRef } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PixelExternalLink } from './icons/PixelIcons'

// Token address - same as landing page
const TOKEN_ADDRESS = "0x0000000000000000000000000000000000000000"

// Rate limit: max 5 clicks per second (200ms minimum between animations)
const COPY_RATE_LIMIT_MS = 200

interface FloatingText {
  id: number
  x: number
}

interface LassSubpageLayoutProps {
  children: ReactNode
  characterImage?: string
  hideCharacter?: boolean
}

export function LassSubpageLayout({ children, characterImage = '/lass/lass-default.png', hideCharacter = false }: LassSubpageLayoutProps) {
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
      x: Math.random() * 40 - 20 // Random offset -20 to +20 px
    }
    setFloatingTexts(prev => [...prev, newFloat])
    
    // Remove this floating text after animation completes
    setTimeout(() => {
      setFloatingTexts(prev => prev.filter(f => f.id !== newFloat.id))
    }, 1000)
  }

  return (
    <div style={{
      display: 'flex',
      gap: '24px',
      width: '100%',
      minHeight: '100%'
    }}>
      {/* Left column - main content */}
      <div style={{
        flex: 1,
        paddingRight: '264px' // Leave space for right column (220px + 24px + 20px gap)
      }}>
        {children}
      </div>
      
      {/* Right column - character and buttons (fixed width matching corner cutout) */}
      <div style={{
        position: 'fixed',
        top: '60px',
        right: 0,
        width: '220px',
        height: 'calc(100vh - 60px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '0 16px 16px 16px', // Reduced right padding to 16px as requested
        zIndex: 50
      }}>
        {/* Character image at top - fills width */}
        {!hideCharacter && (
          <img 
            src={characterImage} 
            alt="Lass" 
            style={{
              width: '100%',
              height: 'auto',
              maxHeight: '45vh',
              objectFit: 'contain',
              imageRendering: 'pixelated',
              marginBottom: 'auto'
            }}
          />
        )}
        
        {/* Button stack at bottom */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          width: '100%',
          marginTop: 'auto',
          overflow: 'visible'
        }}>
          {/* CA Widget with floating copied texts */}
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
              border: '2px solid var(--accent-primary)',
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
            {/* Floating "copied" texts */}
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

          {/* Divider */}
          <div style={{
            height: '0',
            width: '100%',
            borderTop: '2px dotted black',
            margin: '4px 0'
          }} />

          {/* Action Buttons */}
          <Link 
            to="/lass" 
            className="pushdown-button" 
            style={{
              display: 'block',
              width: '100%',
              padding: '8px 12px',
              background: 'var(--cream)',
              border: '2px solid var(--accent-primary)',
              borderRadius: '10px',
              fontFamily: 'var(--font-display)',
              fontSize: '12px',
              letterSpacing: '1px',
              color: 'var(--text-primary)',
              textDecoration: 'none',
              textAlign: 'center',
              cursor: 'pointer',
              boxShadow: '3px 3px 0 rgba(0,0,0,0.12)'
            }}
          >
            READ DOCS
          </Link>
          <a 
            href="https://twitch.tv/llmletsplay" 
            target="_blank" 
            rel="noreferrer" 
            className="pushdown-button" 
            style={{
              display: 'block',
              width: '100%',
              padding: '8px 12px',
              background: '#9146FF',
              border: '2px solid #9146FF',
              borderRadius: '10px',
              fontFamily: 'var(--font-display)',
              fontSize: '12px',
              letterSpacing: '1px',
              color: 'white',
              textDecoration: 'none',
              textAlign: 'center',
              cursor: 'pointer',
              boxShadow: '3px 3px 0 rgba(0,0,0,0.12)'
            }}
          >
            WATCH STREAM
          </a>
        </div>
      </div>
    </div>
  )
}
