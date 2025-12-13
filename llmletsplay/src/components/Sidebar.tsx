interface NavItem {
  id: string
  label: string
  icon: React.ReactNode
  isSubItem?: boolean
  isExternal?: boolean
  href?: string
  hasDivider?: boolean
}

interface SidebarProps {
  navItems: NavItem[]
  activeSection: string
  onNavigate: (id: string) => void
}

import { useState, useEffect } from 'react'
import { TwitterCircle, TwitchLogo, InstagramCircle, PixelExternalLink } from './icons/PixelIcons'
import { Icon } from '@iconify/react'

export function Sidebar({ navItems, activeSection, onNavigate }: SidebarProps) {
  const [sponsorIndex, setSponsorIndex] = useState(0)
  const [isSwitching, setIsSwitching] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(() => {
    // Initialize from localStorage
    const saved = localStorage.getItem('sidebar-collapsed')
    return saved === 'true'
  })

  // Persist collapsed state to localStorage
  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', String(isCollapsed))
  }, [isCollapsed])

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

  const currentSponsor = sponsors[sponsorIndex]

  return (
    <aside className={`sidebar ${isCollapsed ? 'sidebar--collapsed' : ''}`}>
      {/* Collapse Toggle Button - positioned at sidebar/folder border, near bottom */}
      <button 
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="sidebar-toggle"
        style={{
          position: 'absolute',
          bottom: '100px',
          right: '-12px',
          background: 'var(--bg-dark)',
          border: '1px solid var(--border-color)',
          borderRadius: '50%',
          padding: '4px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          width: '24px',
          height: '24px'
        }}
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <Icon 
          icon={isCollapsed ? "streamline-pixel:interface-essential-navigation-right-circle-1" : "streamline-pixel:interface-essential-navigation-left-circle-1"} 
          width={16} 
          height={16} 
        />
      </button>

      <nav className="nav-links" style={{ paddingTop: '24px' }}>
        {navItems.map(item => {
          // In collapsed state, don't apply sub-item indent
          const className = `nav-item ${activeSection === item.id ? 'active' : ''} ${!isCollapsed && item.isSubItem ? 'nav-item--sub' : ''}`
          
          const navElement = item.isExternal && item.href ? (
            <a
              key={item.id}
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
              className={className}
              style={{ textDecoration: 'none' }}
            >
              <span className="nav-icon">{item.icon}</span>
              {!isCollapsed && <span>{item.label}</span>}
              {!isCollapsed && (
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
                  <PixelExternalLink size={14} />
                </div>
              )}
            </a>
          ) : (
            <button 
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={className}
              title={isCollapsed ? item.label : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              {!isCollapsed && <span>{item.label}</span>}
            </button>
          )

          // Add divider after item if it has hasDivider flag
          if (item.hasDivider) {
            return (
              <div key={item.id}>
                {navElement}
                <div style={{
                  height: '1px',
                  background: 'var(--border-color)',
                  margin: '8px 12px'
                }} />
              </div>
            )
          }

          return navElement
        })}
      </nav>
      
      <div className="sidebar-sponsor" style={{ 
        padding: isCollapsed ? '0 4px' : '0 16px', 
        marginBottom: '8px', 
        marginTop: 'auto', 
        textAlign: 'center' 
      }}>
        <a 
          href={currentSponsor.link} 
          target="_blank" 
          rel="noopener noreferrer"
          className="crt-container"
          style={{ 
            display: 'inline-block', 
            position: 'relative',
            padding: isCollapsed ? '3px' : '8px 7px 8px 9px',
            background: '#000',
            boxShadow: isCollapsed ? '3px 3px 0 rgba(0,0,0,0.2)' : '8px 8px 0 rgba(0,0,0,0.2)',
            textDecoration: 'none'
          }}
        >
           <img 
             src={currentSponsor.image} 
             alt={currentSponsor.alt} 
             style={{ 
               width: isCollapsed ? '40px' : '110px',
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
           
           {!isCollapsed && (
             <div className="badge sponsor-text" style={{ 
               position: 'absolute', 
               top: '2px', 
               right: '3px',
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
           )}
        </a>
      </div>
      
      {!isCollapsed && (
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
      )}
    </aside>
  )
}
