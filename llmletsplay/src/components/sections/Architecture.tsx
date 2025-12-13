export function Architecture() {
  return (
    <div className="section clearfix">
      <img 
        src="/lass/lass-glasses-thinking.png" 
        alt="Lass thinking" 
        className="lass-image lass-float-right"
      />
      
      <h2 className="section-title">System Architecture</h2>
      
      <p>
        The Pokemon LLM harness is a multi-layered system connecting a Game Boy 
        emulator to modern AI models. Here's how the pieces fit together:
      </p>

      <div className="diagram">
        <pre>{`
┌──────────────────────────────────────────────────────────────────┐
│                        Pokemon LLM Agent                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐
│  │   mGBA      │───▶│  Lua Script │───▶│   Python    │───▶│  React UI  │
│  │  Emulator   │◀───│  (Socket)   │◀───│   Agent     │◀───│   (WS)     │
│  └─────────────┘    └─────────────┘    └─────────────┘    └────────────┘
│        │                  │                  │                  │
│        ▼                  ▼                  ▼                  ▼
│   ROM Execution      RAM Reading        LLM Analysis      Visualization
│   Button Input       Screenshots        Memory Store       Game Feed
│                      Minimap Gen         TTS Audio        Analysis Log
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
        `}</pre>
      </div>

      <h3 className="section-title">Data Flow</h3>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">1</span>
          <h4>Game State Collection</h4>
        </div>
        <p>
          <code>mGBA</code> → <code>socketserver.lua</code> → <code>socket_utils.py</code> → <code>state.py</code>
        </p>
        <p>The Lua script reads RAM addresses and captures screenshots, sending them to Python via socket.</p>
      </div>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">2</span>
          <h4>LLM Processing</h4>
        </div>
        <p>
          <code>Game State</code> → <code>Vision Analysis</code> → <code>System Prompt</code> → <code>LLM API</code>
        </p>
        <p>Vision model describes the screen, then main LLM analyzes state and decides actions.</p>
      </div>

      <div className="info-card">
        <div className="info-card-header">
          <span className="badge">3</span>
          <h4>Action Execution</h4>
        </div>
        <p>
          <code>Action String</code> → <code>Button Commands</code> → <code>Lua Script</code> → <code>Game Input</code>
        </p>
        <p>Actions like <code>R;R;R;A;</code> are parsed and sent as individual button presses.</p>
      </div>

      <h3 className="section-title">Core Modules</h3>

      <table>
        <thead>
          <tr>
            <th>Module</th>
            <th>Responsibility</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>run.py</code></td>
            <td>Main entry point, async orchestration</td>
          </tr>
          <tr>
            <td><code>core/llmdriver.py</code></td>
            <td>LLM interaction loop, action execution</td>
          </tr>
          <tr>
            <td><code>core/prompts.py</code></td>
            <td>System prompts, 12-section format</td>
          </tr>
          <tr>
            <td><code>core/battle_strategy.py</code></td>
            <td>Battle decision logic, type effectiveness</td>
          </tr>
          <tr>
            <td><code>pyAIAgent/game/state.py</code></td>
            <td>RAM reading, game state parsing</td>
          </tr>
          <tr>
            <td><code>trackers/memory_storage.py</code></td>
            <td>Persistent memory, quest tracking</td>
          </tr>
          <tr>
            <td><code>services/comfyui_tts_service.py</code></td>
            <td>Text-to-speech generation</td>
          </tr>
          <tr>
            <td><code>services/websocket_service.py</code></td>
            <td>Real-time UI updates</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Communication Protocols</h3>

      <h4 style={{ marginTop: '16px', marginBottom: '8px' }}>Socket Commands (Python ↔ mGBA)</h4>
      
      <table>
        <thead>
          <tr>
            <th>Command</th>
            <th>Direction</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>SCREENSHOT</code></td>
            <td>Python → Lua</td>
            <td>Capture current frame</td>
          </tr>
          <tr>
            <td><code>MAP</code></td>
            <td>Python → Lua</td>
            <td>Get minimap data</td>
          </tr>
          <tr>
            <td><code>LOCATION</code></td>
            <td>Python → Lua</td>
            <td>Get player position</td>
          </tr>
          <tr>
            <td><code>PARTY</code></td>
            <td>Python → Lua</td>
            <td>Get party data</td>
          </tr>
          <tr>
            <td><code>BUTTON:{`{key}`}</code></td>
            <td>Python → Lua</td>
            <td>Send button press</td>
          </tr>
          <tr>
            <td><code>SAVESTATE</code></td>
            <td>Python → Lua</td>
            <td>Save game state</td>
          </tr>
          <tr>
            <td><code>LOADSTATE</code></td>
            <td>Python → Lua</td>
            <td>Load game state</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
