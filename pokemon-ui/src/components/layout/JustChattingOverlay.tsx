/**
 * JustChattingOverlay - OBS overlay for "Just Chatting" streams
 * 
 * Uses EXACT same animation structure as llmletsplay ComingSoon page
 * Only difference: trail ghosts use different frame images
 * - Trails 1-3: lass-0 (early in path)
 * - Trails 4-5: lass-1 (middle of path)
 * - Trails 6-8: lass-2 (near center)
 * - Main character: lass-2 (slides in and lands at center)
 */
import './JustChattingOverlay.css';

// Character frames
const FRAME_0 = '/lass/lass-0.png';
const FRAME_1 = '/lass/lass-1.png';
const FRAME_2 = '/lass/lass-2.png';

// Holographic character - exact same structure as ComingSoon.tsx
function HolographicCharacter() {
  return (
    <div className="holographic-afterimage">
      {/* Trail ghosts - appear along path during entrance, then fade */}
      {/* Trails 1-3 use FRAME 0 */}
      <img src={FRAME_0} alt="" className="trail-ghost trail-1" aria-hidden="true" />
      <img src={FRAME_0} alt="" className="trail-ghost trail-2" aria-hidden="true" />
      <img src={FRAME_0} alt="" className="trail-ghost trail-3" aria-hidden="true" />
      
      {/* Trails 4-5 use FRAME 1 */}
      <img src={FRAME_1} alt="" className="trail-ghost trail-4" aria-hidden="true" />
      <img src={FRAME_1} alt="" className="trail-ghost trail-5" aria-hidden="true" />
      
      {/* Trails 6-8 use FRAME 2 */}
      <img src={FRAME_2} alt="" className="trail-ghost trail-6" aria-hidden="true" />
      <img src={FRAME_2} alt="" className="trail-ghost trail-7" aria-hidden="true" />
      <img src={FRAME_2} alt="" className="trail-ghost trail-8" aria-hidden="true" />
      
      {/* Stationary ghosts - fade in after entrance, stay permanently */}
      <img src={FRAME_2} alt="" className="ghost-layer ghost-1" aria-hidden="true" />
      <img src={FRAME_2} alt="" className="ghost-layer ghost-2" aria-hidden="true" />
      <img src={FRAME_2} alt="" className="ghost-layer ghost-3" aria-hidden="true" />
      
      {/* Main character - solid, on top, slides in from left */}
      <img 
        src={FRAME_2} 
        alt="Lass" 
        className="main-character"
      />
    </div>
  );
}

// Flower background
function FlowerBackground() {
  const rows = [];
  const rowCount = 14;
  const flowersPerRow = 40;
  
  for (let row = 0; row < rowCount; row++) {
    const flowers = [];
    for (let i = 0; i < flowersPerRow; i++) {
      flowers.push(
        <span key={i} className="flower-icon flower-spin-cw">✿</span>
      );
    }
    
    rows.push(
      <div 
        key={row} 
        className="flower-row"
        style={{ animationDelay: `${row * -1.5}s` }}
      >
        {flowers}
        {flowers}
        {flowers}
      </div>
    );
  }
  
  return <div className="flower-background">{rows}</div>;
}

// Stream info
function StreamInfo() {
  return (
    <div className="stream-info">
      <div className="stream-title">
        <span className="title-text">JUST CHATTING</span>
      </div>
      <div className="stream-subtitle">with Lass</div>
    </div>
  );
}

// Branding
function BrandingSection() {
  return (
    <div className="branding-section">
      <div className="branding-item">
        <img src="/sponsors/mystery-gift.png" alt="Mystery Gift" className="brand-icon" />
        <span className="brand-text">mysterygift.fun</span>
      </div>
      <div className="branding-divider">✿</div>
      <div className="branding-item">
        <img src="/sponsors/phantasy.png" alt="Phantasy" className="brand-icon" />
        <span className="brand-text">phantasy.bot</span>
      </div>
    </div>
  );
}

export function JustChattingOverlay() {
  return (
    <div className="just-chatting-overlay">
      <div className="background-layer">
        <FlowerBackground />
      </div>
      
      <div className="content-layer page-shake-container">
        <StreamInfo />
        <BrandingSection />
      </div>
      
      <div className="character-container">
        <HolographicCharacter />
      </div>
    </div>
  );
}
