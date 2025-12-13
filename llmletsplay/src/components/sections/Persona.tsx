

export function Persona() {
  return (
    <div className="section clearfix" style={{ 
      display: 'flex', 
      flexDirection: 'row', 
      gap: '40px', 
      alignItems: 'flex-start',
      minHeight: '600px',
      position: 'relative'
    }}>
      {/* Left Column: Info & Specs */}
      <div style={{ flex: '1', minWidth: '300px', zIndex: 2 }}>
        
        {/* Trainer Card */}
        <div className="info-card" style={{ marginBottom: '32px' }}>
          <div className="info-card-header">
            <span className="badge">PROFILE</span>
            <h4 style={{ fontSize: '24px' }}>TRAINER CARD</h4>
          </div>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'min-content 1fr', 
            columnGap: '16px', 
            rowGap: '8px', 
            marginBottom: '20px',
            fontFamily: 'var(--font-mono)',
            fontSize: '14px'
          }}>
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold' }}>NAME</div>
             <div style={{ fontWeight: 'bold' }}>LASS</div>
             
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold' }}>GOAL</div>
             <div>POKEMON MASTER</div>
             
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold' }}>STYLE</div>
             <div>CUTE & STRONG</div>
             
             <div style={{ color: 'var(--text-secondary)', fontWeight: 'bold' }}>NATURE</div>
             <div>BUBBLY / ENERGETIC</div>
          </div>

          <p style={{ lineHeight: '1.6', color: 'var(--text-primary)' }}>
            Lass is an autonomous AI agent running a custom LLM loop. She experiences the world 
            frame-by-frame, managing her own memory, strategy, and team. She loves interacting 
            with chat and takes immense pride in her Pokemon.
          </p>
        </div>

        {/* Technical Specs */}
        <div className="info-card">
          <div className="info-card-header">
            <span className="badge" style={{ background: 'var(--tech-blue, #4a9eff)' }}>SYSTEM</span>
            <h4 style={{ fontSize: '24px' }}>TECHNICAL SPECS</h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* Spec Item: Brain */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px',
              borderBottom: '1px solid rgba(0,0,0,0.05)',
              paddingBottom: '12px'
            }}>
              <div style={{ fontSize: '24px' }}>🧠</div>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '1px' }}>AGENT BRAIN</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px' }}>GLM4.6</div>
              </div>
            </div>

            {/* Spec Item: Vision */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px',
              borderBottom: '1px solid rgba(0,0,0,0.05)',
              paddingBottom: '12px'
            }}>
              <div style={{ fontSize: '24px' }}>👁️</div>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '1px' }}>VISION MODEL</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px' }}>GLM4.6V</div>
              </div>
            </div>

            {/* Spec Item: Voice */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px'
            }}>
              <div style={{ fontSize: '24px' }}>🔊</div>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', letterSpacing: '1px' }}>VOICE SYNTHESIS</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px' }}>CHATTERBOX</div>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* Right Column: Hero Image */}
      <div style={{ 
        flex: '1', 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'flex-end',
        position: 'relative',
        minWidth: '300px'
      }}>
        <img 
          src="/lass/lass-hello.png" 
          alt="Lass" 
          style={{
            width: '100%',
            maxWidth: '500px',
            height: 'auto',
            objectFit: 'contain',
            imageRendering: 'pixelated',
            filter: 'drop-shadow(0 15px 30px rgba(0,0,0,0.25))',
            transform: 'scale(1.1) translateY(20px)', /* Slight overlap/pop */
            transformOrigin: 'bottom center'
          }}
        />
        
        {/* Decorative Element behind */}
        <div style={{
          position: 'absolute',
          bottom: '10%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '80%',
          height: '40%',
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 70%)',
          zIndex: -1,
          pointerEvents: 'none'
        }} />
      </div>
      
    </div>
  )
}
