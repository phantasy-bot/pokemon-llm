
import { PixelBrain, PixelEye, PixelSpeaker, PixelGenderFemale } from '../icons/PixelIcons'

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
  return (
    <div className="section clearfix" style={{ 
      display: 'flex', 
      flexDirection: 'row', 
      gap: '60px', 
      alignItems: 'stretch',
      flex: 1, /* Fill available space */
      height: '100%', /* Ensure explicit height if flex fails in specific router context */
      minHeight: 0, /* Allow flex shrinking if needed but we want growth */
      position: 'relative'
    }}>
      {/* Left Column: Info & Specs */}
      <div style={{ flex: '1', minWidth: '340px', zIndex: 2, display: 'flex', flexDirection: 'column', paddingBottom: '40px' }}>
        
        {/* Trainer Card */}
        <div className="info-card" style={{ marginBottom: '32px' }}>
          <div className="info-card-header" style={{ marginBottom: '24px' }}>
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
            alignItems: 'center' /* Fix horizontal alignment */
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
             
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>STYLE</div>
             <div style={{ fontSize: '16px' }}>CUTE & STRONG</div>
             
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>NATURE</div>
             <div style={{ fontSize: '16px' }}>BUBBLY / ENERGETIC</div>
          </div>

          <p style={{ lineHeight: '1.8', color: 'var(--text-primary)', fontSize: '15px', marginBottom: '24px' }}>
            Lass is an autonomous AI agent running a custom LLM loop. She experiences the world 
            frame-by-frame, managing her own memory, strategy, and team. She loves interacting 
            with chat and takes immense pride in her Pokemon.
          </p>
          
          {/* Gym Badges Section - EMPTY */}
          <div style={{ 
            marginTop: 'auto', 
            paddingTop: '24px', 
            borderTop: '1px dashed rgba(0,0,0,0.1)' 
          }}>
            <div style={{ 
              fontSize: '11px', 
              fontWeight: 'bold', 
              color: 'var(--text-secondary)', 
              letterSpacing: '2px', 
              marginBottom: '16px' 
            }}>
              KANTO BADGES
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
               {/* 8 Kanto Badges with images */}
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

        {/* Technical Specs */}
        <div className="info-card" style={{ marginTop: 'auto' }}>
          <div className="info-card-header" style={{ marginBottom: '24px' }}>
            <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>TECHNICAL SPECS</h4>
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
              <div>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '2px' }}>AGENT BRAIN</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px', letterSpacing: '3px' }}>GLM4.6</div>
              </div>
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
              <div>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '2px' }}>VISION MODEL</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px', letterSpacing: '3px' }}>GLM4.6V</div>
              </div>
            </div>

            {/* Spec Item: Voice */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '16px'
            }}>
              <div style={{ color: 'var(--text-primary)' }}><PixelSpeaker size={40} /></div>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '2px' }}>VOICE SYNTHESIS</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px', letterSpacing: '3px' }}>CHATTERBOX</div>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* Right Column: Hero Image - Sticky/Fixed-ish behavior inside Flex */}
      <div style={{ 
        flex: '1', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'flex-end', 
        position: 'relative',
        minWidth: '300px'
      }}>
        {/* Absolute positioned image to ensure it hits bottom edge */}
        <div style={{
           position: 'absolute',
           bottom: 0,
           left: '50%',
           transform: 'translateX(-50%)',
           width: '100%',
           display: 'flex',
           justifyContent: 'center',
           alignItems: 'flex-end',
           height: '100%',
           pointerEvents: 'none'
        }}>
           <img 
            src="/lass/lass-hello.png" 
            alt="Lass" 
            style={{
              width: '100%',
              maxWidth: '600px',
              height: 'auto',
              maxHeight: '90vh', /* Taller max-height */
              objectFit: 'contain',
              imageRendering: 'pixelated',
              filter: 'drop-shadow(0 20px 40px rgba(0,0,0,0.3))',
              transform: 'translateY(0)', /* No transform Y, sit exactly on bottom */
              transformOrigin: 'bottom center',
              /* Negative bottom margin if needed to overlap folder padding/border? */
              marginBottom: '-2px' 
            }}
          />
        </div>
        
        {/* Decorative Element behind */}
        <div style={{
          position: 'absolute',
          bottom: '50px',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '90%',
          height: '20px',
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.2) 0%, rgba(0,0,0,0) 70%)',
          zIndex: -1,
          pointerEvents: 'none',
          filter: 'blur(10px)'
        }} />
      </div>
      
    </div>
  )
}
