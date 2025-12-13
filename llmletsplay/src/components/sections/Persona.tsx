
import { PixelBrain, PixelEye, PixelSpeaker } from '../icons/PixelIcons'


export function Persona() {
  return (
    <div className="section clearfix" style={{ 
      display: 'flex', 
      flexDirection: 'row', 
      gap: '60px', /* Increased gap */
      alignItems: 'stretch',
      minHeight: '75vh', /* Force reasonable height */
      position: 'relative'
    }}>
      {/* Left Column: Info & Specs */}
      <div style={{ flex: '1', minWidth: '340px', zIndex: 2, display: 'flex', flexDirection: 'column', paddingBottom: '40px' }}>
        
        {/* Trainer Card */}
        <div className="info-card" style={{ marginBottom: '32px' }}>
          <div className="info-card-header" style={{ marginBottom: '24px' }}>
            {/* Removed Text Badge */}
            <h4 style={{ fontSize: '28px', letterSpacing: '1px' }}>TRAINER CARD</h4>
          </div>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'min-content 1fr', 
            columnGap: '24px', 
            rowGap: '16px', 
            marginBottom: '32px',
            fontFamily: 'var(--font-mono)',
            fontSize: '14px'
          }}>
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold', letterSpacing: '2px', fontSize: '11px' }}>NAME</div>
             <div style={{ fontWeight: 'bold', fontSize: '16px' }}>LASS</div>
             
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
          
          {/* Gym Badges Section */}
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
               {[1,2,3,4,5,6,7,8].map(i => (
                 <img 
                   key={i} 
                   src={`/badges/${i}.png`} 
                   alt={`Badge ${i}`}
                   style={{ 
                     width: '40px', 
                     height: '40px', 
                     imageRendering: 'pixelated',
                     filter: 'drop-shadow(2px 2px 0 rgba(0,0,0,0.1))',
                     opacity: 0.8 /* Slightly dimmed to show "potential" or full if she has them? Assuming full for persona page showoff */ 
                   }} 
                 />
               ))}
            </div>
          </div>
        </div>

        {/* Technical Specs */}
        <div className="info-card" style={{ marginTop: 'auto' }}>
          <div className="info-card-header" style={{ marginBottom: '24px' }}>
            {/* Removed Text Badge */}
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
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px' }}>GLM4.6</div>
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
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px' }}>GLM4.6V</div>
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
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '22px' }}>CHATTERBOX</div>
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
        alignItems: 'flex-end', /* Bottom aligned */
        position: 'relative',
        minWidth: '300px'
      }}>
        {/* Absolute positioned image to ensure it hits bottom edge even if container is tall */}
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
              maxWidth: '600px', /* Larger */
              height: 'auto',
              maxHeight: '85vh',
              objectFit: 'contain',
              imageRendering: 'pixelated',
              filter: 'drop-shadow(0 20px 40px rgba(0,0,0,0.3))',
              transform: 'translateY(40px)', /* Push down to sit firmly on "floor" */
              transformOrigin: 'bottom center'
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
