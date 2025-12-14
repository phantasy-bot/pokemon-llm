
import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { PixelBrain, PixelEye, PixelSpeaker, PixelGenderFemale, PixelExternalLink } from '../icons/PixelIcons'

const TOKEN_ADDRESS = '0x000...000'
const COPY_RATE_LIMIT_MS = 500

interface FloatingText {
  id: number
  x: number
}

// Kanto badge data for display
const KANTO_BADGES = [
  { id: 1, name: 'Boulder', leader: 'Brock' },
  { id: 2, name: 'Cascade', leader: 'Misty' },
  { id: 3, name: 'Thunder', leader: 'Lt. Surge' },
  { id: 4, name: 'Rainbow', leader: 'Erika' },
  { id: 5, name: 'Soul', leader: 'Koga' },
  { id: 6, name: 'Marsh', leader: 'Sabrina' },
  { id: 7, name: 'Volcano', leader: 'Blaine' },
  { id: 8, name: 'Earth', leader: 'Giovanni' },
]

// Currently earned badges (empty for now - Lass hasn't earned any yet)
const earnedBadges: number[] = []


export function Persona() {
  const [floatingTexts, setFloatingTexts] = useState<FloatingText[]>([])
  const [activeCardIndex, setActiveCardIndex] = useState(0) // 0 = Trainer, 1 = Tech Specs
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

  // Trainer Card Component
  const TrainerCard = () => (
    <div className="info-card">
      <div className="info-card-header" style={{ marginBottom: '24px', textAlign: 'center' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>TRAINER CARD</h4>
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
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>NAME</div>
         <div style={{ fontWeight: 'bold', fontSize: '16px' }}>LASS</div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>GENDER</div>
         <div style={{ fontSize: '16px', display: 'flex', alignItems: 'center', gap: '6px' }}>
           FEMALE
           <PixelGenderFemale size={16} color="var(--accent-primary)" />
         </div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>GOAL</div>
         <div style={{ fontSize: '16px' }}>POKEMON MASTER</div>
         
         <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>NATURE</div>
         <div style={{ fontSize: '16px' }}>BUBBLY / ENERGETIC</div>
      </div>

      {/* Gym Badges Section - 4x2 Grid */}
      <div style={{ 
        marginTop: 'auto', 
        paddingTop: '24px', 
        borderTop: '1px dashed rgba(0,0,0,0.1)',
        width: '100%'
      }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(4, 1fr)', 
          gap: '12px', 
          justifyItems: 'center',
          width: '100%' 
        }}>
           {KANTO_BADGES.map(badge => {
             const isEarned = earnedBadges.includes(badge.id)
             return (
               <div 
                 key={badge.id}
                 title={`${badge.name} Badge - ${badge.leader}`}
                 style={{ 
                   width: '40px', 
                   height: '40px', 
                   display: 'flex',
                   alignItems: 'center',
                   justifyContent: 'center',
                   position: 'relative'
                 }} 
               >
                 <img 
                   src={`/badges/${badge.id}.png`}
                   alt={`${badge.name} Badge`}
                   style={{
                     width: '100%',
                     height: '100%',
                     objectFit: 'contain',
                     imageRendering: 'pixelated',
                     filter: isEarned ? 'none' : 'grayscale(100%) opacity(0.4)',
                     transition: 'filter 0.3s ease'
                   }}
                 />
               </div>
             )
           })}
        </div>
      </div>
    </div>
  )

  // Technical Specs Card Component
  const TechSpecsCard = () => (
    <div className="info-card info-card--dotted">
      <div className="info-card-header" style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>SPECS</h4>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Spec Item: Brain */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '16px',
          borderBottom: '1px solid rgba(0,0,0,0.05)',
          paddingBottom: '16px'
        }}>
          <div style={{ color: 'var(--text-primary)' }}><PixelBrain size={40} /></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '2px' }}>AGENT BRAIN</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px', letterSpacing: '3px' }}>GLM4.6</div>
          </div>
          <a 
            href="https://alkahest.ai" 
            target="_blank" 
            rel="noopener noreferrer"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color: 'rgba(255,255,255,0.5)',
              textDecoration: 'none',
              whiteSpace: 'nowrap'
            }}
          >
            Powered by Alkahest
          </a>
        </div>

        {/* Spec Item: Vision */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '16px',
          borderBottom: '1px solid rgba(0,0,0,0.05)',
          paddingBottom: '16px'
        }}>
          <div style={{ color: 'var(--text-primary)' }}><PixelEye size={40} /></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '2px' }}>VISION MODEL</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px', letterSpacing: '3px' }}>GLM4.6V</div>
          </div>
          <a 
            href="https://alkahest.ai" 
            target="_blank" 
            rel="noopener noreferrer"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color: 'rgba(255,255,255,0.5)',
              textDecoration: 'none',
              whiteSpace: 'nowrap'
            }}
          >
            Powered by Alkahest
          </a>
        </div>

        {/* Spec Item: Voice */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '16px'
        }}>
          <div style={{ color: 'var(--text-primary)' }}><PixelSpeaker size={40} /></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '2px' }}>VOICE SYNTHESIS</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px', letterSpacing: '3px' }}>CHATTERBOX</div>
          </div>
          <a 
            href="https://alkahest.ai" 
            target="_blank" 
            rel="noopener noreferrer"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '9px',
              color: 'rgba(255,255,255,0.5)',
              textDecoration: 'none',
              whiteSpace: 'nowrap'
            }}
          >
            Powered by Alkahest
          </a>
        </div>
      </div>
    </div>
  )

  return (
    <div className="persona-layout">
      {/* LEFT COLUMN - Trainer Card & Technical Specs (Desktop) / Card Carousel (Mobile) */}
      <div className="persona-cards-column">
        {/* Desktop: Show both cards stacked */}
        <div className="persona-cards-desktop">
          <TrainerCard />
          <TechSpecsCard />
        </div>

        {/* Mobile: Show one card at a time with navigation */}
        <div className="persona-cards-mobile">
          <div className="persona-card-carousel">
            {activeCardIndex === 0 ? <TrainerCard /> : <TechSpecsCard />}
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
        </div>
      </div>

      {/* MIDDLE COLUMN - Character with Holographic Effect (Fixed Bottom) */}
      <div className="holographic-afterimage persona-holographic">
        {/* Trail ghosts */}
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-1" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-2" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-3" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-4" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-5" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-6" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-7" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="trail-ghost trail-8" aria-hidden="true" />
        
        {/* Stationary ghosts */}
        <img src="/lass/lass-hello.png" alt="" className="ghost-layer ghost-1" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="ghost-layer ghost-2" aria-hidden="true" />
        <img src="/lass/lass-hello.png" alt="" className="ghost-layer ghost-3" aria-hidden="true" />
        
        {/* Main character */}
        <img src="/lass/lass-hello.png" alt="Lass" className="main-character" />
      </div>

      {/* RIGHT COLUMN - Sponsor Image + Buttons (Fixed) */}
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
            marginTop: '4px'
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
            width: '95%',
            borderTop: '2px dotted black',
            margin: '4px auto'
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
