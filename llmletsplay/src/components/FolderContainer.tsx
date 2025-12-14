import type { ReactNode, CSSProperties } from 'react'
import { useState, useEffect } from 'react'
import { Icon } from '@iconify/react'

interface FolderContainerProps {
  children: ReactNode
  title: string
  titleStyle?: CSSProperties
  navItems?: Array<{
    id: string
    label: string
    icon: ReactNode
    isSubItem?: boolean
    isExternal?: boolean
    href?: string
    hasDivider?: boolean
  }>
  activeSection?: string
  onNavigate?: (id: string) => void
}

export function FolderContainer({ children, title, titleStyle, navItems, activeSection, onNavigate }: FolderContainerProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Close mobile menu if window is resized larger than mobile breakpoint
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setMobileMenuOpen(false)
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="folder-container">
      {/* Title in the red bar */}
      <div className="folder-title" style={titleStyle}>{title.toUpperCase()}</div>
      
      {/* Corner cutout SVG */}
      <div className="corner-container">
        <svg viewBox="0 0 220 48" className="corner-svg" preserveAspectRatio="none">
          {/* Mask path - fills the corner with dark background */}
          <path 
            d="M0,0 c8,0 14,6 14,14 v18 c0,8 6,14 14,14 H210 Q220,46 220,48 L220,0 Z" 
            fill="var(--bg-dark)" 
            stroke="none"
          />
          {/* Border path - REMOVED GRAY BORDER */}
          <path 
            d="M0,0 c8,0 14,6 14,14 v18 c0,8 6,14 14,14 H210" 
            fill="none" 
            stroke="none" 
            strokeWidth="0"
            transform="translate(0, 0.5)"
          />
          {/* Corner tip - REMOVED GRAY BORDER */}
          <path 
            d="M210,46 Q220,46 220,48" 
            fill="none" 
            stroke="none" 
            strokeWidth="0"
            transform="translate(-0.5, 0)"
          />
        </svg>
      </div>
      
      {/* Stats in the cutout area */}
      <div className="folder-stats">
        <div className="stat-item">
          <span className="stat-count">001</span>
          <span className="stat-label">Run</span>
        </div>
        <div className="stats-separator" />
        <div className="stat-item">
          <span className="stat-count">0.01</span>
          <span className="stat-label">Version</span>
        </div>
        
        {/* Mobile Menu Toggle - hidden on desktop */}
        {navItems && onNavigate && (
          <button 
            className="menu-toggle"
            onClick={() => setMobileMenuOpen(true)}
            style={{
              display: 'none', // Hidden by default, shown via CSS on mobile
              alignItems: 'center',
              justifyContent: 'center',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              opacity: 0.5,
              transition: 'opacity 0.2s ease'
            }}
            title="Menu"
          >
            <Icon icon="streamline-pixel:interface-essential-navigation-menu-1" width={20} height={20} />
          </button>
        )}
      </div>
      
      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && navItems && onNavigate && (
        <div 
          className="mobile-menu-overlay"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'var(--bg-dark)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            padding: '24px'
          }}
        >
          <button 
            onClick={() => setMobileMenuOpen(false)}
            style={{
              alignSelf: 'flex-end',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              marginBottom: '24px'
            }}
          >
            <Icon icon="streamline-pixel:interface-essential-delete-1" width={24} height={24} />
          </button>
          
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {navItems.map(item => {
              const isActive = activeSection === item.id
              
              if (item.isExternal && item.href) {
                return (
                  <a
                    key={item.id}
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => setMobileMenuOpen(false)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '16px',
                      paddingLeft: item.isSubItem ? '32px' : '16px', // Applied logic here
                      textDecoration: 'none',
                      color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '18px',
                      fontWeight: 700,
                      borderBottom: item.hasDivider ? '1px solid var(--border-color)' : 'none',
                      paddingBottom: item.hasDivider ? '24px' : '16px',
                      marginBottom: item.hasDivider ? '8px' : '0'
                    }}
                  >
                    <span>{item.icon}</span>
                    <span>{item.label}</span>
                  </a>
                )
              }
              
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id)
                    setMobileMenuOpen(false)
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '16px',
                    paddingLeft: item.isSubItem ? '32px' : '16px',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '18px',
                    fontWeight: 700,
                    textAlign: 'left',
                    borderBottom: item.hasDivider ? '1px solid var(--border-color)' : 'none',
                    paddingBottom: item.hasDivider ? '24px' : '16px',
                    marginBottom: item.hasDivider ? '8px' : '0'
                  }}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              )
            })}
          </nav>
        </div>
      )}
      
      {/* Main Content Area */}
      <div className="folder-content" style={{
        marginTop: '60px',
        padding: '48px 0 0 48px',
        maxWidth: '100%',
        minHeight: 'calc(100% - 60px)',
        position: 'relative',
        zIndex: 5
      }}>
        {children}
      </div>
    </div>
  )
}
