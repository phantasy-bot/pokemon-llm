# Pokemon Red Memory Map

Documentation of all RAM addresses currently read by the agent.

## Currently Used Memory Addresses

### Player State

| Address  | Size | Description              | Used In             |
| -------- | ---- | ------------------------ | ------------------- |
| `0xD35E` | 1    | Current map ID           | `get_location()`    |
| `0xD361` | 1    | Player Y position (tile) | `get_location()`    |
| `0xD362` | 1    | Player X position (tile) | `get_location()`    |
| `0xD369` | 1    | Map width (blocks)       | `get_location()`    |
| `0xC109` | 1    | Player facing direction  | `get_facing()`      |
| `0xD356` | 1    | Badge flags (8 bits)     | `get_badges_text()` |

### Party Data

| Address   | Size | Description                           | Used In            |
| --------- | ---- | ------------------------------------- | ------------------ |
| `0xD163`  | 8    | Party count + species IDs             | `get_party_text()` |
| `0xD16B+` | 44×6 | Pokemon data (HP, level, moves, etc.) | `get_party_text()` |
| `0xD2B5+` | 10×6 | Pokemon nicknames                     | `get_party_text()` |

### Sprite/NPC Data

| Address       | Size | Description                          | Used In         |
| ------------- | ---- | ------------------------------------ | --------------- |
| `0xC100-C1FF` | 256  | Sprite table (16 sprites × 16 bytes) | `get_sprites()` |
| `0xC1x0`      | 1    | Picture ID (0 = disabled)            | `get_sprites()` |
| `0xC1x4`      | 1    | Y screen position                    | `get_sprites()` |
| `0xC1x6`      | 1    | X screen position                    | `get_sprites()` |

### Text/Dialog State

| Address       | Size | Description                      | Used In             |
| ------------- | ---- | -------------------------------- | ------------------- |
| `0xD355`      | 1    | Text speed setting               | `get_text_state()`  |
| `0xD358`      | 1    | Text printing flags              | `get_text_state()`  |
| `0xC3A0-C507` | 360  | Tile screen buffer (dialog text) | `get_dialog_text()` |

### Battle State

| Address  | Size | Description    | Used In              |
| -------- | ---- | -------------- | -------------------- |
| `0xD057` | 1    | In battle flag | `get_battle_state()` |
| `0xD05A` | 1    | Battle type    | `get_battle_state()` |
| `0xCCD5` | 1    | Turn count     | `get_battle_state()` |
| `0xCCDB` | 1    | Move menu type | `get_battle_state()` |

### Menu State

| Address  | Size | Description              | Used In            |
| -------- | ---- | ------------------------ | ------------------ |
| `0xCC26` | 1    | Selected menu item       | `get_menu_state()` |
| `0xCC28` | 1    | Last menu item ID        | `get_menu_state()` |
| `0xCC2A` | 1    | Previously selected item | `get_menu_state()` |

---

## Text Encoding

Pokemon Red uses custom tile indices for text:

| Range       | Characters        |
| ----------- | ----------------- |
| `0x50`      | String terminator |
| `0x7F`      | Space             |
| `0x80-0x99` | A-Z (uppercase)   |
| `0xA0-0xB9` | a-z (lowercase)   |
| `0xF6-0xFF` | 0-9 (numbers)     |
| `0xE6`      | ?                 |
| `0xE7`      | !                 |
| `0xE8`      | .                 |

See `decode_pokemon_text()` in `pyAIAgent/game/data.py` for full mapping.

---

## Battle Type Values

| Value  | Meaning               |
| ------ | --------------------- |
| `0xF0` | Wild battle           |
| `0xED` | Trainer battle        |
| `0xEA` | Gym leader battle     |
| `0xF3` | Final battle          |
| `0xF6` | Defeated trainer      |
| `0xF9` | Defeated wild Pokemon |
| `0xFC` | Defeated champion/gym |

---

## Sources

- [DataCrystal RAM Map](https://datacrystal.romhacking.net/wiki/Pok%C3%A9mon_Red/Blue:RAM_map)
- [Pokemon Red Disassembly](https://github.com/pret/pokered)
