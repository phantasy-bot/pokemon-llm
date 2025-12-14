import { FolderContainer } from './FolderContainer'
import { useNavigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { LassSubpageLayout } from './LassSubpageLayout'
import { PixelHome2 } from './icons/PixelIcons'
import { Icon } from '@iconify/react'
import { TypewriterText } from './shared/TypewriterText'

const navItems = [
  { id: 'home', label: 'Home', icon: <PixelHome2 size={18} /> },
  { id: 'lass', label: 'Lass Plays Pokemon', icon: <Icon icon="streamline-pixel:photography-focus-flower" width={18} height={18} /> }, 
]

export function LandingPage() {
  const navigate = useNavigate()

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
      <main className="main-wrapper homepage" style={{ position: 'relative', overflow: 'hidden' }}>
        <FolderContainer title="LLM LET'S PLAY" titleStyle={{ fontSize: '64px', letterSpacing: '8px' }}>
          <LassSubpageLayout hideCharacter={true}>
            <div className="coming-soon-wrapper">
              {/* Group Container - Anchors Character and Bubble together */}
              <div className="coming-soon-group">
                {/* Character Image with Holographic Afterimage - Using lass-glasses for homepage */}
                <div className="holographic-afterimage">
                  {/* Trail ghosts - appear along path during entrance, then fade */}
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-1" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-2" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-3" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-4" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-5" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-6" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-7" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="trail-ghost trail-8" aria-hidden="true" />
                  
                  {/* Stationary ghosts - fade in after entrance, stay permanently */}
                  <img src="/lass/lass-glasses.png" alt="" className="ghost-layer ghost-1" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="ghost-layer ghost-2" aria-hidden="true" />
                  <img src="/lass/lass-glasses.png" alt="" className="ghost-layer ghost-3" aria-hidden="true" />
                  
                  {/* Main character - solid, on top */}
                  <img 
                    src="/lass/lass-glasses.png" 
                    alt="Coming Soon" 
                    className="main-character coming-soon-character"
                  />
                </div>

                {/* Speech Bubble - Relative to Group */}
                <div className="coming-soon-bubble">
                  <h2 className="coming-soon-title">
                    <TypewriterText 
                      text="Lass wants to meet you!" 
                      speed={50} 
                      startDelay={4500} // Start after bubble fades in (4s delay + 0.5s fade)
                    />
                  </h2>
                  <div className="coming-soon-text">
                    <TypewriterText 
                      text="Join me on my Pokémon journey ♡." 
                      speed={30} 
                      startDelay={5500} // Start after title finishes
                    />
                  </div>
                  
                  {/* Desktop Tail */}
                  <svg className="coming-soon-tail-desktop" viewBox="0 0 50 35">
                    <polygon 
                      points="0,0 50,0 48,33"
                      fill="var(--cream)"
                      stroke="var(--accent-primary)"
                      strokeWidth="2"
                    />
                    <rect x="0" y="-2" width="50" height="5" fill="var(--cream)" />
                  </svg>

                  {/* Tablet Tail */}
                  <svg className="coming-soon-tail-tablet" viewBox="0 0 50 35">
                    <polygon 
                      points="0,0 50,0 2,33"
                      fill="var(--cream)"
                      stroke="var(--accent-primary)"
                      strokeWidth="2"
                    />
                    <rect x="0" y="-2" width="50" height="5" fill="var(--cream)" />
                  </svg>

                  {/* Mobile Tail */}
                  <svg className="coming-soon-tail-mobile" viewBox="0 0 40 30">
                    <polygon 
                      points="0,0 40,0 20,28"
                      fill="var(--cream)"
                      stroke="var(--accent-primary)"
                      strokeWidth="2"
                    />
                    <rect x="0" y="-2" width="40" height="5" fill="var(--cream)" />
                  </svg>
                </div>
              </div>
            </div>
          </LassSubpageLayout>
        </FolderContainer>
      </main>
    </div>
  )
}
