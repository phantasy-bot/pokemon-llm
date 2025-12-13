interface NavItem {
  id: string
  label: string
  icon: string
}

interface SidebarProps {
  navItems: NavItem[]
  activeSection: string
  onNavigate: (id: string) => void
}

// SVG Icons as components
const XIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
  </svg>
)

const TwitchIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z"/>
  </svg>
)

const GitHubIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
  </svg>
)

const ExternalLinkIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M18.25 15.5a.75.75 0 00.75-.75V4.75a.75.75 0 00-.75-.75H8.25a.75.75 0 000 1.5h8.19l-7.22 7.22a.75.75 0 001.06 1.06l7.22-7.22v8.19a.75.75 0 00.75.75z" />
    <path d="M10 5a.75.75 0 000 1.5H6.5a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-3.5a.75.75 0 00-1.5 0v3.5a.5.5 0 01-.5.5h-10a.5.5 0 01-.5-.5v-10a.5.5 0 01.5-.5H10z" />
  </svg>
)

import { useNavigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'

// ... existing imports

export function Sidebar({ navItems, activeSection, onNavigate }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [sponsorIndex, setSponsorIndex] = useState(0)
  const [isSwitching, setIsSwitching] = useState(false)

  const sponsors = [
    { image: '/sponsors/mystery-gift.png', link: 'https://mysterygift.fun', alt: 'Mystery Gift' },
    { image: '/sponsors/phantasy.png', link: 'https://phantasy.bot', alt: 'Phantasy Bot' }
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setIsSwitching(true)
      setTimeout(() => {
        setSponsorIndex((prev) => (prev + 1) % sponsors.length)
        setTimeout(() => setIsSwitching(false), 200)
      }, 200)
    }, 30000) // 30 seconds
    return () => clearInterval(timer)
  }, [])

  const handleHeaderClick = () => {
    navigate('/')
  }

  const currentSponsor = sponsors[sponsorIndex]

  // Only show livestream link on non-homepage routes (specifically lass pages)
  const showLivestream = location.pathname !== '/'

  return (
    <aside className="sidebar">
      <div className="sidebar-header" onClick={handleHeaderClick} style={{ cursor: 'pointer' }}>
        <div className="brand-icon">
          <img src="/lass/lass-hello.png" alt="Lass" />
        </div>
        <span className="brand-name">LLM LETS PLAY</span>
      </div>
      
      <nav className="nav-links">
        {navItems.map(item => (
          <div
            key={item.id}
            className={`nav-item ${activeSection === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
        
        {showLivestream && (
          <a 
            href="https://twitch.tv/lassplayspokemon" 
            target="_blank" 
            rel="noopener noreferrer"
            className="nav-item"
            style={{ textDecoration: 'none' }} 
          >
            {/* Invisible icon for alignment with other items */}
            <span className="nav-icon" style={{ visibility: 'hidden' }}>📺</span>
            <span>Livestream</span>
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
              <ExternalLinkIcon />
            </div>
          </a>
        )}
      </nav>
      
      <div className="sidebar-sponsor" style={{ padding: '0 16px', marginBottom: '24px', marginTop: 'auto', textAlign: 'center' }}>
        <a 
          href={currentSponsor.link} 
          target="_blank" 
          rel="noopener noreferrer"
          className="crt-container"
          style={{ 
            display: 'inline-block', 
            position: 'relative',
            padding: '8px 7px 8px 9px', /* Shift right 1px */
            background: '#1a1a1a', 
            boxShadow: '8px 8px 0 rgba(0,0,0,0.2)',
            textDecoration: 'none'
          }}
        >
           <img 
             src={currentSponsor.image} 
             alt={currentSponsor.alt} 
             style={{ 
               width: '110px',
               maxWidth: '100%', 
               height: 'auto', 
               borderRadius: '0', 
               display: 'block'
             }}
           />
           
           {isSwitching && (
             <div style={{ position: 'absolute', inset: 0, background: '#111', zIndex: 20, boxSizing: 'border-box' }}>
               <div className="crt-static-overlay" style={{ mixBlendMode: 'normal', opacity: 0.5 }} />
             </div>
           )}
           
           <div className="badge" style={{ 
             position: 'absolute', 
             top: '2px', 
             right: '4px', 
             zIndex: 30,
             fontSize: '9px',
             fontWeight: 'bold',
             padding: '0',
             background: 'transparent', 
             color: '#666',
             borderRadius: '0', 
             pointerEvents: 'none',
             textAlign: 'right',
             letterSpacing: '0.5px'
           }}>
             SPONSOR
           </div>
        </a>
      </div>
      
      <div className="sidebar-footer">
        <div className="social-links">
          <a href="https://x.com/llmletsplay" target="_blank" rel="noopener noreferrer" className="social-link" title="X (Twitter)">
            <XIcon />
          </a>
          <a href="https://twitch.tv/llmletsplay" target="_blank" rel="noopener noreferrer" className="social-link" title="Twitch">
            <TwitchIcon />
          </a>
          <a href="https://github.com/area/pokemon-llm" target="_blank" rel="noopener noreferrer" className="social-link" title="GitHub">
            <GitHubIcon />
          </a>
        </div>
        <div className="copyright">
          © 2025 LLM Lets Play
        </div>
      </div>
    </aside>
  )
}
