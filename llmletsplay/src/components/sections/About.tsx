export function About() {
  return (
    <div className="section clearfix">
      <img 
        src="/lass/lass-victory.png" 
        alt="Lass celebrating" 
        className="lass-image lass-float-right"
      />
      
      <h2 className="section-title">Welcome, Trainer!</h2>
      
      <p>
        <strong>LLM Lets Play</strong> is an experimental project that uses large language models 
        to play Pokemon Red completely autonomously. No human input required — just 
        pure AI decision-making, one button press at a time.
      </p>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">LIVE</span>
          <h4>The Harness</h4>
        </div>
        <p>
          Our harness connects an LLM brain directly to the mGBA emulator via Lua scripting. 
          The AI "sees" the game through screenshots, reads game state from RAM, and 
          sends button presses back to play the game.
        </p>
      </div>

      <h3 className="section-title">How It Works</h3>
      
      <ol>
        <li><span className="highlight">Screenshot</span> — Capture the current game frame</li>
        <li><span className="highlight">Vision Analysis</span> — AI describes what it sees</li>
        <li><span className="highlight">LLM Decision</span> — Model analyzes state and chooses action</li>
        <li><span className="highlight">Button Press</span> — Send input to emulator</li>
        <li><span className="highlight">Repeat</span> — Every 25-75 seconds</li>
      </ol>

      <div className="info-card">
        <div className="info-card-header">
          <h4>Meet Lass</h4>
        </div>
        <p>
          Lass is our AI trainer persona — a friendly, determined character who provides 
          commentary during the stream. She's learning as she goes, making mistakes, 
          celebrating victories, and slowly mastering the world of Pokemon!
        </p>
      </div>

      <h3 className="section-title">Key Features</h3>
      
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
  )
}
