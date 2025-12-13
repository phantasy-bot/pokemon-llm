import { useState, useRef } from 'react'
import { FolderContainer } from './FolderContainer'
import { Link, useNavigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { PixelHome2, PixelHeart, PixelExternalLink } from './icons/PixelIcons'

const navItems = [
  { id: 'home', label: 'Home', icon: <PixelHome2 size={18} /> },
  { id: 'lass', label: 'Lass Plays Pokemon', icon: <PixelHeart size={18} /> }, 
]

// Token address - update this to your contract address
const TOKEN_ADDRESS = "0x0000000000000000000000000000000000000000"

// Rate limit: max 5 clicks per second (200ms minimum between animations)
const COPY_RATE_LIMIT_MS = 200

interface FloatingText {
  id: number
  x: number
}

export function LandingPage() {
  const [floatingTexts, setFloatingTexts] = useState<FloatingText[]>([])
  const lastCopyTime = useRef(0)
  const nextId = useRef(0)
  const navigate = useNavigate()

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

  const handleNavigate = (id: string) => {
    if (id === 'home') navigate('/')
    if (id === 'lass') navigate('/lass')
  }

  const buttonStyle = {
    display: 'block',
    width: '100%',
    padding: '10px 16px',
    background: 'var(--cream)',
    border: '2px solid var(--accent-primary)',
    borderRadius: '10px',
    fontFamily: 'var(--font-display)',
    fontSize: '14px',
    letterSpacing: '2px',
    color: 'var(--text-primary)',
    textDecoration: 'none',
    textAlign: 'center' as const,
    cursor: 'pointer',
    boxShadow: '3px 3px 0 rgba(0,0,0,0.12)',
    transition: 'transform 0.1s, box-shadow 0.1s'
  }

  return (
    <div className="app-container">
      <Sidebar
        navItems={navItems}
        activeSection="home"
        onNavigate={handleNavigate}
      />
      <main className="main-wrapper" style={{ position: 'relative', overflow: 'hidden' }}>
        <FolderContainer title="LLM LET'S PLAY" titleStyle={{ fontSize: '64px', letterSpacing: '8px', marginTop: '-20px' }}>
          <div className="landing-content" style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            height: '100%',
            textAlign: 'center',
            position: 'relative',
            zIndex: 10,
            paddingTop: '40px'
          }}>
            {/* Content area - buttons moved to fixed corner */}
          </div>

          {/* Large Fixed Character Image - centered relative to title */}
          <img 
              src="/lass/lass-glasses.png" 
              alt="Lass" 
              style={{
                position: 'fixed',
                bottom: '-20px',
                left: '50%',
                transform: 'translateX(-50%)',
                height: '75vh',
                maxHeight: '700px',
                objectFit: 'contain',
                imageRendering: 'pixelated',
                zIndex: 1,
                pointerEvents: 'none',
                filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.15))'
              }}
            />
        </FolderContainer>

        {/* Fixed Bottom-Right Button Stack */}
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '16px',
          zIndex: 100,
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          width: '180px'
        }}>
          {/* CA Widget with floating copied texts */}
          <div 
            onClick={handleCopy}
            className="pushdown-button"
            style={{
              ...buttonStyle,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              position: 'relative',
              flexWrap: 'nowrap'
            }}
          >
            {/* Multiple Floating Copied Texts */}
            {floatingTexts.map(f => (
              <span 
                key={f.id}
                style={{
                  position: 'absolute',
                  top: '-30px',
                  left: `calc(50% + ${f.x}px)`,
                  transform: 'translateX(-50%)',
                  fontFamily: 'var(--font-display)',
                  fontSize: '14px',
                  color: 'var(--accent-primary)',
                  fontWeight: 'bold',
                  animation: 'floatUp 1s ease-out forwards',
                  pointerEvents: 'none'
                }}
              >
                Copied!
              </span>
            ))}
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
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
              <PixelExternalLink size={16} />
            </a>
          </div>

          {/* Divider */}
          <div style={{
            height: '0',
            width: '100%',
            borderTop: '2px dotted black',
            margin: '6px 0'
          }} />

          {/* Action Buttons */}
          <Link to="/lass" className="pushdown-button" style={{...buttonStyle, lineHeight: 1, paddingTop: '8px', paddingBottom: '12px'}}>
            READ DOCS
          </Link>
          <a href="https://twitch.tv/llmletsplay" target="_blank" rel="noreferrer" className="pushdown-button" style={{...buttonStyle, background: '#9146FF', color: 'white', borderColor: '#9146FF', lineHeight: 1, paddingTop: '8px', paddingBottom: '12px'}}>
            WATCH STREAM
          </a>
        </div>

        {/* CSS Animation for floating text and pushdown effect */}
        <style>{`
          @keyframes floatUp {
            0% {
              opacity: 1;
              transform: translateX(-50%) translateY(0);
            }
            100% {
              opacity: 0;
              transform: translateX(-50%) translateY(-20px);
            }
          }
          .pushdown-button:active {
            transform: translateY(2px);
            box-shadow: 1px 1px 0 rgba(0,0,0,0.12) !important;
          }
        `}</style>
      </main>
    </div>
  )
}
