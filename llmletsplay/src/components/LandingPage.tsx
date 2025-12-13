const navItems = [
  { id: 'home', label: 'Home', icon: '🏠' },
  { id: 'lass', label: 'Lass Plays Pokemon', icon: '🎮' }, 
]

export function LandingPage() {
  const [copied, setCopied] = useState(false)
  const tokenAddress = "0x0000000000000000000000000000000000000000" // Placeholder
  const navigate = useNavigate()

  const handleCopy = () => {
    navigator.clipboard.writeText(tokenAddress)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleNavigate = (id: string) => {
    if (id === 'home') navigate('/')
    if (id === 'lass') navigate('/lass')
  }

  return (
    <div className="app-container">
      <Sidebar
        navItems={navItems}
        activeSection="home"
        onNavigate={handleNavigate}
      />
      <main className="main-wrapper" style={{ position: 'relative', overflow: 'hidden' }}>
        <FolderContainer title="WELCOME TO LLM LETS PLAY">
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
            
            {/* Tagline */}
            <h1 style={{ 
              fontSize: '32px', 
              color: 'var(--text-primary)',
              maxWidth: '800px',
              margin: '0 0 24px 0',
              textShadow: '3px 3px 0 var(--cream)',
              letterSpacing: '1px',
              fontFamily: 'var(--font-display)'
            }}>
              AN AI AGENT PLAYING POKEMON ON TWITCH
            </h1>

            {/* Token Address Section */}
            <div className="token-section" style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: 'var(--cream)',
              padding: '12px 24px',
              borderRadius: '16px',
              border: '3px solid var(--accent-primary)',
              boxShadow: '6px 6px 0 rgba(0,0,0,0.1)',
              maxWidth: '90%',
              flexWrap: 'wrap',
              justifyContent: 'center',
              marginBottom: '40px'
            }}>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '14px',
                color: 'var(--text-secondary)',
                fontWeight: 'bold'
              }}>
                CA:
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '18px',
                color: 'var(--text-primary)',
                wordBreak: 'break-all'
              }}>
                {tokenAddress}
              </span>
              <button 
                onClick={handleCopy}
                style={{
                  background: 'var(--accent-primary)',
                  color: 'white',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontFamily: 'var(--font-display)',
                  fontSize: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  transform: copied ? 'scale(0.95)' : 'scale(1)',
                  boxShadow: '0 2px 0 rgba(0,0,0,0.2)'
                }}
              >
                {copied ? 'COPIED!' : 'COPY'}
              </button>
            </div>

            {/* Main Links Grid */}
            <div className="landing-links" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '20px',
              width: '100%',
              maxWidth: '600px',
              marginBottom: 'auto'
            }}>
              <Link to="/lass" className="landing-button primary">
                READ DOCS
              </Link>
              <a href="https://twitch.tv/llmletsplay" target="_blank" rel="noreferrer" className="landing-button twitch">
                WATCH STREAM
              </a>
              <a href="https://x.com/llmletsplay" target="_blank" rel="noreferrer" className="landing-button">
                TWITTER / X
              </a>
              <a href="https://github.com/area/pokemon-llm" target="_blank" rel="noreferrer" className="landing-button">
                GITHUB
              </a>
            </div>
          </div>

          {/* Large Fixed Character Image */}
          <img 
              src="/lass/lass-hello.png" 
              alt="Lass" 
              style={{
                position: 'fixed',
                bottom: '-20px',
                left: '55%', /* Slightly off-center to balance sidebar? Or 50%? Sidebar is fixed left. App container usually has padding left. */
                /* Assuming main-wrapper compensates. I'll use 50% of viewport relative to main-wrapper if possible? */
                /* position: fixed is viewport relative. Sidebar is ~280px. */
                /* I'll centering using `left: calc(50% + 140px)` where 140 is half sidebar width? Sidebar is 280px. */
                /* Let's try `left: 50%` with transform. */
                transform: 'translateX(-40%)', /* Nudge left slightly to not be blocked by sidebar visually? */
                height: '65vh',
                maxHeight: '600px',
                objectFit: 'contain',
                imageRendering: 'pixelated',
                zIndex: 1,
                pointerEvents: 'none',
                filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.15))'
              }}
            />
        </FolderContainer>
      </main>
    </div>
  )
}
