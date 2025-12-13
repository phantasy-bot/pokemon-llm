import type { ReactNode } from 'react'

interface FolderContainerProps {
  children: ReactNode
  title: string
}

export function FolderContainer({ children, title }: FolderContainerProps) {
  return (
    <div className="folder-container">
      {/* Title in the red bar */}
      <div className="folder-title">{title.toUpperCase()}</div>
      
      {/* Corner cutout SVG */}
      <div className="corner-container">
        <svg viewBox="0 0 220 48" className="corner-svg" preserveAspectRatio="none">
          {/* Mask path - fills the corner with dark background */}
          <path 
            d="M0,0 c8,0 14,6 14,14 v18 c0,8 6,14 14,14 H210 Q220,46 220,48 L220,0 Z" 
            fill="var(--bg-dark)" 
            stroke="none"
          />
          {/* Border path - the curved line */}
          <path 
            d="M0,0 c8,0 14,6 14,14 v18 c0,8 6,14 14,14 H210" 
            fill="none" 
            stroke="var(--border-color)" 
            strokeWidth="1"
            transform="translate(0, 0.5)"
          />
          {/* Corner tip */}
          <path 
            d="M210,46 Q220,46 220,48" 
            fill="none" 
            stroke="var(--border-color)" 
            strokeWidth="1"
            transform="translate(-0.5, 0)"
          />
        </svg>
      </div>
      
      {/* Lass icon in the cutout space */}
      <div className="folder-lass">
        <img src="/lass/lass-default.png" alt="Lass" />
      </div>
      
      {/* Stats in the cutout area */}
      <div className="folder-stats">
        <div className="stat-item">
          <span className="stat-count">5</span>
          <span className="stat-label">Sections</span>
        </div>
        <div className="stats-separator" />
        <div className="stat-item">
          <span className="stat-count">∞</span>
          <span className="stat-label">Cycles</span>
        </div>
      </div>
      
      {/* Content */}
      <div className="folder-content">
        {children}
      </div>
    </div>
  )
}
