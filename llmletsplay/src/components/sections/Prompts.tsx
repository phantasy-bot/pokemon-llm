export function Prompts() {
  return (
    <div className="section clearfix">
      <div className="about-intro">
        <div className="about-text-content">
          <p>
            The agent uses a standardized <strong>12-section format</strong> for all screen types, 
            ensuring consistent and parseable output.
          </p>
          
          <div className="info-card">
            <div className="info-card-header">
              <span className="badge">STRATEGY</span>
              <h4>Prompt Focus</h4>
            </div>
            <p>
              Section 7 becomes <strong>MINIMAP</strong>: Grid analysis with blocked/walkable directions and exit tiles.
            </p>
            <p style={{ marginTop: '8px', fontStyle: 'italic' }}>
              Action limited to 1-5 moves, near exits use only 1-3 moves.
            </p>
          </div>
        </div>
        <img 
          src="/lass/lass-default.png" 
          alt="Lass" 
          className="lass-intro-image"
        />
      </div>

      <h3 className="section-title">12-Section Analysis Format</h3>
      
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Section</th>
            <th>Purpose</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td><strong>STRATEGY</strong></td>
            <td>Current approach (Navigate, Attack, Read)</td>
          </tr>
          <tr>
            <td>2</td>
            <td><strong>TARGET</strong></td>
            <td>Destination with coordinates or goal</td>
          </tr>
          <tr>
            <td>3</td>
            <td><strong>OBSTACLE</strong></td>
            <td>What's blocking progress</td>
          </tr>
          <tr>
            <td>4</td>
            <td><strong>STUCK CHECK</strong></td>
            <td>Movement verification</td>
          </tr>
          <tr>
            <td>5</td>
            <td><strong>VISION</strong></td>
            <td>Visual observations from screen</td>
          </tr>
          <tr>
            <td>6</td>
            <td><strong>STATE</strong></td>
            <td>Game state facts (map, position, HP)</td>
          </tr>
          <tr>
            <td>7</td>
            <td><strong>MINIMAP/MOVES</strong></td>
            <td>Grid analysis OR battle moves</td>
          </tr>
          <tr>
            <td>8</td>
            <td><strong>ACTION</strong></td>
            <td>Button presses (R;R;R;A;)</td>
          </tr>
          <tr>
            <td>9</td>
            <td><strong>REASONING</strong></td>
            <td>Path explanation</td>
          </tr>
          <tr>
            <td>10</td>
            <td><strong>ALTERNATIVES</strong></td>
            <td>Backup plan if blocked</td>
          </tr>
          <tr>
            <td>11</td>
            <td><strong>COMMENTARY</strong></td>
            <td>Stream personality (extracted for TTS)</td>
          </tr>
          <tr>
            <td>12</td>
            <td><strong>MEMORY_WRITE</strong></td>
            <td>Events to save to memory</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Action Format</h3>
      
      <p>Actions are semicolon-separated button sequences:</p>
      
      <table>
        <thead>
          <tr>
            <th>Button</th>
            <th>Meaning</th>
            <th>Examples</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>U</code></td>
            <td>Up/North</td>
            <td><code>U;U;U;</code> = move up 3 tiles</td>
          </tr>
          <tr>
            <td><code>D</code></td>
            <td>Down/South</td>
            <td><code>D;A;</code> = down then confirm</td>
          </tr>
          <tr>
            <td><code>L</code></td>
            <td>Left/West</td>
            <td><code>L;L;</code> = move left 2 tiles</td>
          </tr>
          <tr>
            <td><code>R</code></td>
            <td>Right/East</td>
            <td><code>R;R;R;R;</code> = move right 4</td>
          </tr>
          <tr>
            <td><code>A</code></td>
            <td>Confirm/Select</td>
            <td><code>A;</code> = single confirm</td>
          </tr>
          <tr>
            <td><code>B</code></td>
            <td>Cancel/Back</td>
            <td><code>B;B;B;B;</code> = spam cancel</td>
          </tr>
          <tr>
            <td><code>S</code></td>
            <td>Start menu</td>
            <td><code>S;</code> = open menu</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Data Trust Hierarchy</h3>
      
      <div className="info-card">
        <p>The LLM is explicitly told to trust data sources in this order:</p>
        <ol>
          <li><strong>game_state</strong> = ABSOLUTE TRUTH (map_name, position from RAM)</li>
          <li><strong>minimap</strong> = Reliable (tile analysis)</li>
          <li><strong>memory_context</strong> = Reliable (but exit coords are approximate)</li>
          <li><strong>vision</strong> = UNRELIABLE (hallucination-prone)</li>
        </ol>
      </div>

      <h3 className="section-title">Screen-Specific Variations</h3>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">OVERWORLD</span>
          <h4>Navigation Prompt</h4>
        </div>
        <p>Section 7 becomes <strong>MINIMAP</strong>: Grid analysis with blocked/walkable directions and exit tiles.</p>
        <p>Action limited to 1-5 moves, near exits use only 1-3 moves.</p>
      </div>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">BATTLE</span>
          <h4>Combat Prompt</h4>
        </div>
        <p>Section 7 becomes <strong>MOVES</strong>: Available moves with PP, type effectiveness analysis.</p>
        <p>Actions navigate battle menus: <code>U;D;L;R;A;B;</code> to select moves or switch pokemon.</p>
      </div>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">DIALOGUE</span>
          <h4>Text Prompt</h4>
        </div>
        <p>Section 7 becomes <strong>CONTEXT</strong>: Why is this dialogue important?</p>
        <p><code>A;</code> to advance, <code>B;B;B;B;</code> to escape repetitive text.</p>
      </div>

      <h3 className="section-title">Commentary Rules</h3>
      
      <p>Section 11 (COMMENTARY) is extracted for TTS with these rules:</p>
      
      <ul>
        <li>1-2 fun sentences only</li>
        <li>NO button names (U, D, L, R, A, B)</li>
        <li>React to what's happening in-game</li>
        <li>Reference player history when relevant</li>
        <li>Speak as "Lass" character personality</li>
      </ul>

      <h3 className="section-title">Memory Write Examples</h3>
      
      <pre style={{ background: 'var(--dark)', padding: '16px', borderRadius: '4px' }}>{`12. **MEMORY_WRITE**: Chose Charmander as my starter!
12. **MEMORY_WRITE**: Got Oak's Parcel from the shopkeeper
12. **MEMORY_WRITE**: Beat Brock, earned Boulder Badge!
12. **MEMORY_WRITE**: Named my rival GARY
12. **MEMORY_WRITE**: None`}</pre>
    </div>
  )
}
