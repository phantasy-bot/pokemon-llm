
import React from 'react'

export function Persona() {
  return (
    <div className="section clearfix">
      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">PROFILE</span>
          <h4>Trainer Card</h4>
        </div>
        <div style={{ marginBottom: '16px' }}>
          <p><strong>Name:</strong> Lass</p>
          <p><strong>Goal:</strong> Pokemon Master</p>
          <p><strong>Personality:</strong> Bubbly, energetic, determined!</p>
          <p><strong>Strategy:</strong> Cute & strong Pokemon only!</p>
        </div>
        <p>
          Lass is an AI agent running a custom LLM loop. She experiences the game frame-by-frame,
          reads memory to understand her stats, and makes decisions based on her persona.
          She loves interacting with chat (when the feature is enabled) and takes pride in her team.
        </p>
      </div>

       {/* Large Hero Image for Persona Page */}
       <img 
          src="/lass/lass-hello.png" 
          alt="Lass" 
          style={{
            position: 'fixed',
            bottom: '-20px',
            left: 'calc(50% + 140px)', /* Centered relative to view, offset for sidebar (280px) */
            /* Or just center of viewport if overlaying? */
            /* "huge fixed to bottom-center image there too" */
            /* If sidebar is visible, "center" usually means center of content area. */
            /* Content area starts at 280px. Width is calc(100% - 280px). */
            /* Center of content is 280 + (100% - 280)/2 = 280 + 50% - 140 = 50% + 140px. */
            /* Adjust slightly for visual balance. */
            transform: 'translateX(-50%)',
            height: '70vh', 
            maxHeight: '650px',
            objectFit: 'contain',
            imageRendering: 'pixelated',
            zIndex: 1,
            pointerEvents: 'none',
            filter: 'drop-shadow(0 10px 20px rgba(0,0,0,0.15))'
          }}
        />
    </div>
  )
}
