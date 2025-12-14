
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
      <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>TOKENOMICS</h4>
      </div>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'min-content 1fr', 
        columnGap: '24px', 
        rowGap: '16px', 
        marginBottom: '32px',
        fontFamily: 'var(--font-mono)',
        fontSize: '14px',
        alignItems: 'center'
      }}>
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>TOKEN</div>
         <div style={{ fontWeight: 'bold', fontSize: '16px' }}>$LASS</div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>MAX SUPPLY</div>
         <div style={{ fontSize: '16px' }}>1,000,000,000</div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>LAUNCH</div>
         <div style={{ fontSize: '16px' }}>FAIR LAUNCH (PUMP.FUN)</div>
      </div>
    
      {/* Decorative dotted line at bottom similar to trainer card but without badges */}
      <div style={{ 
        marginTop: 'auto', 
        paddingTop: '24px', 
        borderTop: '1px dashed rgba(0,0,0,0.1)',
        width: '100%',
        display: 'flex',
        justifyContent: 'center'
      }}>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', letterSpacing: '2px' }}>
          OFFICIAL TICKER
        </div>
      </div>
    </div>
  )

  // Disclaimer Card Component
  const DisclaimerCard = () => (
    <div className="info-card" style={{ display: 'flex', flexDirection: 'column' }}>
       <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>DISCLAIMER</h4>
      </div>
      
      <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '14px',
          lineHeight: '1.6',
          color: 'var(--text-primary)',
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
            <button 
              className="mobile-nav-btn prev"
              onClick={goToPrevCard}
              aria-label="Previous card"
            >
              {'<'}
            </button>
            
            <div className="mobile-card-container">
              {activeCardIndex === 0 ? <TokenomicsCard /> : <DisclaimerCard />}
            </div>

            <button 
              className="mobile-nav-btn next"
              onClick={goToNextCard}
              aria-label="Next card"
            >
              {'>'}
            </button>
            
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
              padding: '12px',
              background: 'var(--cream)',
              border: '2px solid var(--text-primary)',
              borderRadius: '12px',
              textDecoration: 'none',
              color: 'var(--text-primary)',
              fontWeight: 'bold',
              fontFamily: 'var(--font-display)',
              letterSpacing: '1px',
              boxShadow: '4px 4px 0px rgba(0,0,0,0.2)'
            }}
          >
            READ DOCS
          </a>
          
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
              padding: '12px',
              background: 'var(--accent-primary)',
              border: '2px solid var(--text-primary)',
              borderRadius: '12px',
              textDecoration: 'none',
              color: 'white',
              fontWeight: 'bold',
              fontFamily: 'var(--font-display)',
              letterSpacing: '1px',
              boxShadow: '4px 4px 0px rgba(0,0,0,0.2)'
            }}
          >
            WATCH STREAM
          </a>
        </div>
      </div>

       {/* Holographic Character - Positioned absolutely in the center of the right column space visually */}
       <div className="persona-holographic">
          <div className="holographic-wrapper" style={{ height: '100%', display: 'flex', alignItems: 'flex-end' }}>
             {/* Character Image with Holographic Afterimage */}
             <div className="holographic-afterimage">
                {/* Fixed Character Image */}
                <img src="/lass/lass-idle.gif" alt="Lass" className="main-character" />
                
                {/* Ghost copies for effect */}
                <img src="/lass/lass-idle.gif" alt="" className="ghost-1" aria-hidden="true" />
                <img src="/lass/lass-idle.gif" alt="" className="ghost-2" aria-hidden="true" />
                <img src="/lass/lass-idle.gif" alt="" className="ghost-3" aria-hidden="true" />
             </div>
          </div>
       </div>

    </div>
  )
}
