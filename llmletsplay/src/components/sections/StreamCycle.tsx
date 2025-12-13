export function StreamCycle() {
  return (
    <div className="section clearfix">
      <img 
        src="/lass/lass-default.png" 
        alt="Lass" 
        className="lass-image lass-float-right"
      />
      
      <h2 className="section-title">Stream Cycle: Flow & Timing</h2>
      
      <p>
        Each cycle of the agent takes <strong>25-75 seconds</strong> depending on LLM speed 
        and network conditions. Here's exactly what happens:
      </p>

      <div className="diagram">
        <pre>{`
   ┌─────────────────┐
   │  Data Gathering │ ~0.3-0.5s
   │   (Game State)  │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ Vision Analysis │ ~5-15s
   │   (Screenshot)  │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │  LLM Analysis   │ ~5-25s
   │  (12-Section)   │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ TTS Commentary  │ ~5-20s
   │  (Audio Play)   │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │    Execution    │ ~4s
   │ (Button Press)  │
   └────────┬────────┘
            │
            └──────────────▶ REPEAT
        `}</pre>
      </div>

      <h3 className="section-title">Detailed Timing Breakdown</h3>
      
      <table>
        <thead>
          <tr>
            <th>Component</th>
            <th>Operation</th>
            <th>Time</th>
            <th>Timeout</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>mGBA</td>
            <td><code>prep_llm()</code> game state</td>
            <td>0.3-0.5s</td>
            <td>30s</td>
          </tr>
          <tr>
            <td>Vision</td>
            <td>MCP analyze_image</td>
            <td>5-15s</td>
            <td>Retries forever</td>
          </tr>
          <tr>
            <td>LLM</td>
            <td>Z.AI chat/completions</td>
            <td>5-25s</td>
            <td>40s (+3 retries)</td>
          </tr>
          <tr>
            <td>TTS Synth</td>
            <td>ComfyUI generation</td>
            <td>5-15s</td>
            <td>10s</td>
          </tr>
          <tr>
            <td>TTS Play</td>
            <td>Audio playback</td>
            <td>4-20s</td>
            <td>None</td>
          </tr>
          <tr>
            <td>Action</td>
            <td>Post-action delay</td>
            <td>4s fixed</td>
            <td>None</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">TTS Queue System</h3>
      
      <div className="info-card">
        <p><code>MAX_QUEUE_SIZE = 2</code> (1 commentary + 1 chat response max)</p>
        <ul>
          <li><strong>PRIORITY_COMMENTARY = 100</strong> — highest, plays immediately</li>
          <li><strong>PRIORITY_CHAT_RESPONSE = 50</strong> — queued, non-blocking</li>
        </ul>
        <p style={{ marginTop: '8px' }}>
          If queue is full, chat responses show in UI but skip TTS. 
          Twitch chat always gets the text response.
        </p>
      </div>

      <h3 className="section-title">Cycle Metrics Broadcast</h3>
      
      <p>Every cycle broadcasts timing metrics to the UI:</p>
      
      <pre style={{ background: 'var(--dark)', padding: '16px', borderRadius: '4px', marginTop: '8px' }}>{`{
  "cycleTiming": "40.2s | wait 2.0s",
  "currentCycleTime": 40.2,
  "prevCycleTime": 35.1,
  "avgCycleTime": 37.5,
  "cycleMetrics": {
    "mGBA": 0.4,
    "vision": 8.3,
    "diff": 0,
    "llm": 15.2,
    "total": 40.2
  }
}`}</pre>

      <h3 className="section-title">Cycle Steps with UI Updates</h3>
      
      <table>
        <thead>
          <tr>
            <th>Step</th>
            <th>What Happens</th>
            <th>UI Animation</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1</td>
            <td><code>prep_llm()</code> gathers state</td>
            <td>None</td>
          </tr>
          <tr>
            <td>2</td>
            <td>Screenshot captured</td>
            <td>Image appears</td>
          </tr>
          <tr>
            <td>3</td>
            <td>Vision API called</td>
            <td>Waiting dots animate</td>
          </tr>
          <tr>
            <td>4</td>
            <td>Vision result received</td>
            <td>Typewriter animation</td>
          </tr>
          <tr>
            <td>5</td>
            <td>Main LLM called</td>
            <td>Status: THINKING</td>
          </tr>
          <tr>
            <td>6</td>
            <td>LLM result received</td>
            <td>Typewriter animation</td>
          </tr>
          <tr>
            <td>7</td>
            <td>TTS synthesis + playback</td>
            <td>Commentary synced to audio</td>
          </tr>
          <tr>
            <td>8</td>
            <td>Actions sent to mGBA</td>
            <td>Button list updates + flash</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Retry Logic</h3>
      
      <table>
        <thead>
          <tr>
            <th>Service</th>
            <th>Retries</th>
            <th>Backoff</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Z.AI LLM</td>
            <td>3</td>
            <td>0.5s → 1s → 2s</td>
          </tr>
          <tr>
            <td>Vision MCP</td>
            <td>Infinite</td>
            <td>Restarts server</td>
          </tr>
          <tr>
            <td>mGBA Socket</td>
            <td>N/A</td>
            <td>35s timeout</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
