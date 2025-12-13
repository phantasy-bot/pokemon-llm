import { PixelLightning, PixelHeart, PixelSettings, PixelStar, PixelEye, PixelTarget } from '../icons/PixelIcons'
import { LassSubpageLayout } from '../LassSubpageLayout'

export function About() {
  return (
    <LassSubpageLayout>
      <div className="section">
        <div className="about-text-content">
          <p>
            <strong>LLM Lets Play</strong> is an experimental project that uses large language models 
            to play Pokemon Red completely autonomously. No human input required — just 
            pure AI decision-making, one button press at a time.
          </p>
          
          <div className="info-card">
            <div className="info-card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <PixelLightning size={20} color="var(--accent-primary)" />
              <span className="badge">LIVE</span>
              <h4>The Harness</h4>
            </div>
            <p>
              Our harness connects an LLM brain directly to the mGBA emulator via Lua scripting. 
              The AI "sees" the game through screenshots, reads game state from RAM, and 
              sends button presses back to play the game.
            </p>
          </div>
        </div>

        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PixelSettings size={20} color="var(--accent-primary)" />
          How It Works
        </h3>
        
        <ol>
          <li><PixelEye size={14} style={{ marginRight: '6px' }} /><span className="highlight">Screenshot</span> — Capture the current game frame</li>
          <li><PixelEye size={14} style={{ marginRight: '6px' }} /><span className="highlight">Vision Analysis</span> — AI describes what it sees</li>
          <li><PixelStar size={14} style={{ marginRight: '6px' }} /><span className="highlight">LLM Decision</span> — Model analyzes state and chooses action</li>
          <li><PixelTarget size={14} style={{ marginRight: '6px' }} /><span className="highlight">Button Press</span> — Send input to emulator</li>
          <li><PixelLightning size={14} style={{ marginRight: '6px' }} /><span className="highlight">Repeat</span> — Every 25-75 seconds</li>
        </ol>

        <div className="info-card">
          <div className="info-card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <PixelHeart size={20} color="var(--accent-primary)" />
            <h4>Meet Lass</h4>
          </div>
          <p>
            Lass is our AI trainer persona — a friendly, determined character who provides 
            commentary during the stream. She's learning as she goes, making mistakes, 
            celebrating victories, and slowly mastering the world of Pokemon!
          </p>
        </div>

        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PixelStar size={20} color="var(--accent-primary)" />
          Key Features
        </h3>
        
        <table>
          <thead>
            <tr>
              <th>Feature</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Vision Understanding</td>
              <td>AI interprets game visuals in real-time</td>
            </tr>
            <tr>
              <td>Memory System</td>
              <td>Persistent memory for navigation and story events</td>
            </tr>
            <tr>
              <td>Text-to-Speech</td>
              <td>Live commentary with character personality</td>
            </tr>
            <tr>
              <td>Minimap Navigation</td>
              <td>Tile-based pathfinding from RAM data</td>
            </tr>
            <tr>
              <td>Battle Strategy</td>
              <td>Type effectiveness and move selection logic</td>
            </tr>
          </tbody>
        </table>
      </div>
    </LassSubpageLayout>
  )
}
