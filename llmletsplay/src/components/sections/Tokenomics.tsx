import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PixelBrain, PixelEye, PixelSpeaker, PixelGenderFemale, PixelExternalLink } from '../icons/PixelIcons'

const TOKEN_ADDRESS = '0x000...000'
const COPY_RATE_LIMIT_MS = 500

interface FloatingText {
  id: number
  x: number
}

/* Duplicated layout from Persona.tsx but with distinct content */
export function Tokenomics() {
  const [floatingTexts, setFloatingTexts] = useState<FloatingText[]>([])
  const [activeCardIndex, setActiveCardIndex] = useState(0) // 0 = Tokenomics, 1 = Disclaimer
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

  // Card navigation for mobile
  const goToPrevCard = () => setActiveCardIndex(prev => prev === 0 ? 1 : 0)
  const goToNextCard = () => setActiveCardIndex(prev => prev === 0 ? 1 : 0)

  // Tokenomics Card Component
  const TokenomicsCard = () => (
    <div className="info-card">
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '140px 1fr', 
        columnGap: '24px', 
        rowGap: '16px', 
        marginBottom: '32px',
        fontFamily: 'var(--font-mono)',
        fontSize: '14px',
        alignItems: 'center'
      }}>
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>NAME</div>
         <div style={{ fontWeight: 'bold', fontSize: '16px' }}>Lass</div>

         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>TICKER</div>
         <div style={{ fontWeight: 'bold', fontSize: '16px' }}>$LASS</div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>MAX SUPPLY</div>
         <div style={{ fontSize: '16px' }}>1,000,000,000</div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>LAUNCH TYPE</div>
         <div style={{ fontSize: '16px' }}>FAIR LAUNCH (PUMP.FUN)</div>

         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>LAUNCH DATE</div>
         <div style={{ fontSize: '16px' }}>December 20, 2025</div>
      </div>

      {/* Trade Buttons */}
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        fontWeight: 'bold',
        color: 'var(--text-secondary)',
        letterSpacing: '2px',
        textAlign: 'center',
        marginBottom: '12px',
        borderTop: '1px dashed rgba(255,255,255,0.1)',
        paddingTop: '20px'
      }}>
        SWAP ON
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(3, 1fr)', 
        gap: '8px'
      }}>
        <a 
          href="#" 
          target="_blank"
          rel="noopener noreferrer"
          className="pushdown-button"
          style={{
            padding: '8px',
            background: '#131825',
            border: '2px solid #5F45FF',
            borderRadius: '8px',
            fontSize: '10px',
            fontWeight: 'bold',
            fontFamily: 'var(--font-display)',
            color: '#00C2FF',
            textAlign: 'center',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '2px 2px 0 rgba(0,0,0,0.1)'
          }}
        >
          RAYDIUM
        </a>
        <a 
          href={`https://pump.fun/${TOKEN_ADDRESS}`}
          target="_blank"
          rel="noopener noreferrer"
          className="pushdown-button"
          style={{
            padding: '8px',
            background: '#10B981',
            border: '2px solid #059669',
            borderRadius: '8px',
            fontSize: '10px',
            fontWeight: 'bold',
            fontFamily: 'var(--font-display)',
            color: 'white',
            textAlign: 'center',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '2px 2px 0 rgba(0,0,0,0.1)'
          }}
        >
          PUMP.FUN
        </a>
        <a 
          href="#" 
          target="_blank"
          rel="noopener noreferrer"
          className="pushdown-button"
          style={{
            padding: '8px',
            background: '#282C34',
            border: '2px solid #6E7381',
            borderRadius: '8px',
            fontSize: '10px',
            fontWeight: 'bold',
            fontFamily: 'var(--font-display)',
            color: 'white',
            textAlign: 'center',
            textDecoration: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '2px 2px 0 rgba(0,0,0,0.1)'
          }}
        >
          DEXSCREENER
        </a>
      </div>
    
    </div>
  )

  // Disclaimer Card Component
  const DisclaimerCard = () => (
    <div className="info-card info-card--dotted" style={{ display: 'flex', flexDirection: 'column' }}>
       <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>DISCLAIMER</h4>
      </div>
      
      <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '14px',
          lineHeight: '1.6',
          color: 'rgba(255, 255, 255, 0.9)',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '0 16px'
      }}>
        <p>
          $LASS is just an entertainment/fan token for supporting our Lass character. 
        </p>
        <p style={{ marginTop: '16px' }}>
          It has no inherent value.
        </p>
      </div>
    </div>
  )

  return (
    <div className="persona-layout">
        <div className="persona-cards-column">
          {/* Desktop: Grid View */}
          <div className="persona-cards-desktop">
            <TokenomicsCard />
            <DisclaimerCard />
          </div>

          {/* Mobile: Carousel View */}
          <div className="persona-cards-mobile">
            <div className="persona-card-carousel">
              {activeCardIndex === 0 ? <TokenomicsCard /> : <DisclaimerCard />}
            </div>
          
          {/* Card Navigation Buttons - Fixed bottom left on mobile */}
          <div className="persona-card-nav">
            <button 
              onClick={goToPrevCard}
              className="persona-card-nav-btn"
              aria-label="Previous card"
            >
              ◀
            </button>
            <button 
              onClick={goToNextCard}
              className="persona-card-nav-btn"
              aria-label="Next card"
            >
              ▶
            </button>
          </div>
            
            {/* Pagination dots */}
            <div className="mobile-dots">
              <div 
                className={`mobile-dot ${activeCardIndex === 0 ? 'active' : ''}`}
                onClick={() => setActiveCardIndex(0)}
              />
              <div 
                className={`mobile-dot ${activeCardIndex === 1 ? 'active' : ''}`}
                onClick={() => setActiveCardIndex(1)}
              />
            </div>
          </div>
        </div>

        {/* Right Column Layout - Identical to Persona for consistency */}
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

          <a 
            href="#" 
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

       {/* MIDDLE COLUMN - Character with Holographic Effect (Fixed Bottom) */}
       <div className="holographic-afterimage persona-holographic">
        {/* Trail ghosts */}
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-1" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-2" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-3" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-4" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-5" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-6" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-7" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="trail-ghost trail-8" aria-hidden="true" />
        
        {/* Stationary ghosts */}
        <img src="/lass/lass-tokenomics.png" alt="" className="ghost-layer ghost-1" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="ghost-layer ghost-2" aria-hidden="true" />
        <img src="/lass/lass-tokenomics.png" alt="" className="ghost-layer ghost-3" aria-hidden="true" />
        
        {/* Main character */}
        <img src="/lass/lass-tokenomics.png" alt="Lass" className="main-character" />
       </div>

    </div>
  )
}
