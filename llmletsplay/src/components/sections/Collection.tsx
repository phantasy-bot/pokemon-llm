import { useState, useRef } from 'react'
import { HoloCard } from '../HoloCard'
import { PixelExternalLink } from '../icons/PixelIcons'

const TOKEN_ADDRESS = '0x000...000'
const COPY_RATE_LIMIT_MS = 500

interface FloatingText {
  id: number
  x: number
}

export function Collection() {
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

  const cards = [
    {
      name: 'Lass (Base Set)',
      rarity: 'common',
      description: 'The original Lass from Base Set.',
      image: '/cards/lass-base-set-bs-75.jpg',
      dataAttributes: { 'data-supertype': 'trainer' }
    },
    {
      name: 'Lass (Base Set 2)',
      rarity: 'common',
      description: 'Lass from Base Set 2.',
      image: '/cards/lass-base-set-2-b2-104.jpg',
      dataAttributes: { 'data-supertype': 'trainer' }
    }
  ]

  return (
    <div className="persona-layout">
        <div className="persona-cards-column">
          <div className="persona-cards-desktop">
            {/* Info Card */}
            <div className="info-card">
              <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
                <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>COLLECTION GOAL</h4>
              </div>
              
              <div style={{ 
                marginBottom: '32px',
                fontFamily: 'var(--font-mono)',
                fontSize: '14px',
                textAlign: 'center',
                lineHeight: '1.6',
                padding: '0 16px'
              }}>
                 <p>
                   Our goal is to collect all variations of the Lass card from the original Pokemon TCG Base Set.
                   This includes <strong>Shadowless</strong>, <strong>First Edition</strong>, and <strong>Unlimited</strong> prints.
                 </p>
                 <p style={{ marginTop: '16px', color: 'var(--text-secondary)' }}>
                   Help us complete the ultimate Lass shrine!
                 </p>
              </div>
            </div>

            {/* Cards Grid */}
            <div style={{ 
              display: 'flex', 
              gap: '20px', 
              flexWrap: 'wrap', 
              justifyContent: 'center',
              marginBottom: '40px'
            }}>
               {cards.map((card, idx) => (
                 <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                   <HoloCard cardType={card} isActive={true} />
                   <span style={{ 
                     fontFamily: 'var(--font-display)', 
                     fontSize: '18px',
                     color: 'var(--text-primary)',
                     letterSpacing: '1px'
                   }}>
                     {card.name}
                   </span>
                 </div>
               ))}
            </div>
          </div>
        </div>

        {/* Right Column Layout */}
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
