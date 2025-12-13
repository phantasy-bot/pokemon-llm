import { useState } from 'react'
import { FolderContainer } from './FolderContainer'
import { Link } from 'react-router-dom'

export function LandingPage() {
  const [copied, setCopied] = useState(false)
  const tokenAddress = "0x0000000000000000000000000000000000000000" // Placeholder

  const handleCopy = () => {
    navigator.clipboard.writeText(tokenAddress)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="app-container">
      <main className="main-wrapper" style={{ paddingLeft: '14px' }}> {/* Add padding to match right side since no sidebar */}
        <FolderContainer title="WELCOME TO LLM LETS PLAY">
          <div className="landing-content" style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            gap: '24px',
            textAlign: 'center'
          }}>
            {/* Large Character Image */}
            <div className="landing-hero" style={{
              position: 'relative',
              width: '280px',
              height: '280px',
              marginTop: '20px'
            }}>
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '320px', // Larger bg circle
                height: '320px',
                background: 'var(--cream)',
                borderRadius: '50%',
                zIndex: 0
              }} />
              <img 
                src="/lass/lass-hello.png" 
                alt="Lass" 
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  imageRendering: 'pixelated',
                  position: 'relative',
                  zIndex: 1,
                  filter: 'drop-shadow(0 4px 0 rgba(0,0,0,0.1))'
                }}
              />
            </div>

            {/* Tagline */}
            <h1 style={{ 
              fontSize: '24px', 
              color: 'var(--text-primary)',
              maxWidth: '600px',
              margin: '0',
              textShadow: '2px 2px 0 var(--cream)'
            }}>
              AN AI AGENT PLAYING POKEMON ON TWITCH
            </h1>

            {/* Token Address Section */}
            <div className="token-section" style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: 'var(--cream)',
              padding: '12px 20px',
              borderRadius: '12px',
              border: '2px solid var(--accent-primary)',
              boxShadow: '4px 4px 0 rgba(0,0,0,0.1)',
              maxWidth: '90%',
              flexWrap: 'wrap',
              justifyContent: 'center'
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
                fontSize: '16px',
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
                  borderRadius: '6px',
                  fontFamily: 'var(--font-display)',
                  fontSize: '10px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  transform: copied ? 'scale(0.95)' : 'scale(1)',
                }}
              >
                {copied ? 'COPIED!' : 'COPY'}
              </button>
            </div>

            {/* Main Links Grid */}
            <div className="landing-links" style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '16px',
              marginTop: '12px',
              width: '100%',
              maxWidth: '500px'
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
        </FolderContainer>
      </main>
    </div>
  )
}
