interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  isSubItem?: boolean
  isExternal?: boolean
  href?: string
}

interface SidebarProps {
  navItems: NavItem[]
  activeSection: string
  onNavigate: (id: string) => void
}

import { useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { TwitterCircle, TwitchLogo, InstagramCircle, PixelExternalLink } from './icons/PixelIcons'

export function Sidebar({ navItems, activeSection, onNavigate }: SidebarProps) {
  const navigate = useNavigate()
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
    }, 45000) // 45 seconds
    return () => clearInterval(timer)
  }, [])

  const handleHeaderClick = () => {
    navigate('/')
  }

  const currentSponsor = sponsors[sponsorIndex]

  return (
    <aside className="sidebar">
      <div className="sidebar-header" onClick={handleHeaderClick} style={{ cursor: 'pointer' }}>
        <div className="brand-icon">
          <img src="/lass/lass-hello.png" alt="Lass" />
        </div>
        <span className="brand-name">LLM LETS PLAY</span>
      </div>
      
      <nav className="nav-links">
        {navItems.map(item => {
          const className = `nav-item ${activeSection === item.id ? 'active' : ''} ${item.isSubItem ? 'nav-item--sub' : ''}`
          
          if (item.isExternal && item.href) {
            return (
              <a
                key={item.id}
                href={item.href}
                target="_blank"
                rel="noopener noreferrer"
                className={className}
                style={{ textDecoration: 'none' }}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
                  <PixelExternalLink size={14} />
                </div>
              </a>
            )
          }
          
          return (
            <div
              key={item.id}
              className={className}
              onClick={() => onNavigate(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </div>
          )
        })}
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
            padding: '8px 7px 8px 9px',
            background: '#000', /* Revert to plain black as requested */
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
             right: '3px', /* Shifted 1px right (was 4px) */
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
            <TwitterCircle size={20} />
          </a>
          <a href="https://twitch.tv/llmletsplay" target="_blank" rel="noopener noreferrer" className="social-link" title="Twitch">
            <TwitchLogo size={20} />
          </a>
          <a href="https://instagram.com/llmletsplay" target="_blank" rel="noopener noreferrer" className="social-link" title="Instagram">
            <InstagramCircle size={20} />
          </a>
        </div>
        <div className="copyright">
          © 2025 LLM Lets Play
        </div>
      </div>
    </aside>
  )
}
