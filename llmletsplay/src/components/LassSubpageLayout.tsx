import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { PixelExternalLink } from './icons/PixelIcons'

// Token address - same as landing page
const TOKEN_ADDRESS = "0x0000000000000000000000000000000000000000"

interface LassSubpageLayoutProps {
  children: ReactNode
  characterImage?: string
  hideCharacter?: boolean
}

export function LassSubpageLayout({ children, characterImage = '/lass/lass-default.png', hideCharacter = false }: LassSubpageLayoutProps) {
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
        paddingRight: '240px' // Leave space for right column
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
        padding: '8px 0',
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
          marginTop: 'auto'
        }}>
          {/* CA Widget */}
          <div 
            onClick={() => navigator.clipboard.writeText(TOKEN_ADDRESS)}
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
              boxShadow: '3px 3px 0 rgba(0,0,0,0.12)'
            }}
          >
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
