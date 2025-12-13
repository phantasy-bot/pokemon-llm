export function Memory() {
  return (
    <div className="section">
      <h2 className="section-title">Pokemon Red Memory Map</h2>
      
      <p>
        The agent reads game state directly from RAM addresses. Here's the complete 
        documentation of all memory locations currently monitored:
      </p>

      <h3 className="section-title">Player State</h3>
      
      <table>
        <thead>
          <tr>
            <th>Address</th>
            <th>Size</th>
            <th>Description</th>
            <th>Used In</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>0xD35E</code></td>
            <td>1</td>
            <td>Current map ID</td>
            <td><code>get_location()</code></td>
          </tr>
          <tr>
            <td><code>0xD361</code></td>
            <td>1</td>
            <td>Player Y position (tile)</td>
            <td><code>get_location()</code></td>
          </tr>
          <tr>
            <td><code>0xD362</code></td>
            <td>1</td>
            <td>Player X position (tile)</td>
            <td><code>get_location()</code></td>
          </tr>
          <tr>
            <td><code>0xD369</code></td>
            <td>1</td>
            <td>Map width (blocks)</td>
            <td><code>get_location()</code></td>
          </tr>
          <tr>
            <td><code>0xC109</code></td>
            <td>1</td>
            <td>Player facing direction</td>
            <td><code>get_facing()</code></td>
          </tr>
          <tr>
            <td><code>0xD356</code></td>
            <td>1</td>
            <td>Badge flags (8 bits)</td>
            <td><code>get_badges_text()</code></td>
          </tr>
          <tr>
            <td><code>0xD347</code></td>
            <td>3</td>
            <td>Money (BCD encoded)</td>
            <td><code>get_money()</code></td>
          </tr>
          <tr>
            <td><code>0xD31D</code></td>
            <td>1</td>
            <td>Inventory count</td>
            <td><code>get_inventory()</code></td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Battle State</h3>
      
      <table>
        <thead>
          <tr>
            <th>Address</th>
            <th>Size</th>
            <th>Description</th>
            <th>Used In</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>0xD057</code></td>
            <td>1</td>
            <td>In battle flag</td>
            <td><code>get_battle_state()</code></td>
          </tr>
          <tr>
            <td><code>0xD05A</code></td>
            <td>1</td>
            <td>Battle type</td>
            <td><code>get_battle_state()</code></td>
          </tr>
          <tr>
            <td><code>0xCCD5</code></td>
            <td>1</td>
            <td>Turn count</td>
            <td><code>get_battle_state()</code></td>
          </tr>
          <tr>
            <td><code>0xCFE5</code></td>
            <td>1</td>
            <td>Enemy Species ID</td>
            <td><code>get_enemy_pokemon()</code></td>
          </tr>
          <tr>
            <td><code>0xCFE6</code></td>
            <td>2</td>
            <td>Enemy Current HP</td>
            <td><code>get_enemy_pokemon()</code></td>
          </tr>
          <tr>
            <td><code>0xCFE8</code></td>
            <td>1</td>
            <td>Enemy Level</td>
            <td><code>get_enemy_pokemon()</code></td>
          </tr>
          <tr>
            <td><code>0xD014</code></td>
            <td>1</td>
            <td>Player Active Party Index</td>
            <td><code>get_active_battle_pokemon()</code></td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Party Data</h3>
      
      <table>
        <thead>
          <tr>
            <th>Address</th>
            <th>Size</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>0xD163</code></td>
            <td>8</td>
            <td>Party count + species IDs</td>
          </tr>
          <tr>
            <td><code>0xD16B+</code></td>
            <td>44×6</td>
            <td>Pokemon data (HP, level, moves, etc.)</td>
          </tr>
          <tr>
            <td><code>0xD2B5+</code></td>
            <td>10×6</td>
            <td>Pokemon nicknames</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Battle Type Values</h3>
      
      <table>
        <thead>
          <tr>
            <th>Value</th>
            <th>Meaning</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>0xF0</code></td>
            <td>Wild battle</td>
          </tr>
          <tr>
            <td><code>0xED</code></td>
            <td>Trainer battle</td>
          </tr>
          <tr>
            <td><code>0xEA</code></td>
            <td>Gym leader battle</td>
          </tr>
          <tr>
            <td><code>0xF3</code></td>
            <td>Final battle</td>
          </tr>
          <tr>
            <td><code>0xF6</code></td>
            <td>Defeated trainer</td>
          </tr>
          <tr>
            <td><code>0xF9</code></td>
            <td>Defeated wild Pokemon</td>
          </tr>
        </tbody>
      </table>

      <h3 className="section-title">Text Encoding</h3>
      
      <p>Pokemon Red uses custom tile indices for text:</p>
      
      <table>
        <thead>
          <tr>
            <th>Range</th>
            <th>Characters</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>0x50</code></td>
            <td>String terminator</td>
          </tr>
          <tr>
            <td><code>0x7F</code></td>
            <td>Space</td>
          </tr>
          <tr>
            <td><code>0x80-0x99</code></td>
            <td>A-Z (uppercase)</td>
          </tr>
          <tr>
            <td><code>0xA0-0xB9</code></td>
            <td>a-z (lowercase)</td>
          </tr>
          <tr>
            <td><code>0xF6-0xFF</code></td>
            <td>0-9 (numbers)</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}
