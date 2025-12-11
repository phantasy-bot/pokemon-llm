# LLM Prompts Documentation

This document describes the prompt system used by the Pokemon LLM agent.

## 12-Section Analysis Format

All screen types use a standardized 12-section format for consistent output:

| #   | Section               | Purpose             | Screen Variations                              |
| --- | --------------------- | ------------------- | ---------------------------------------------- |
| 1   | STRATEGY              | Current approach    | Navigation, Attack, Read, etc.                 |
| 2   | TARGET                | Destination/goal    | Tile coords, enemy, conversation               |
| 3   | OBSTACLE              | What's blocking     | Walls, type disadvantage, choices              |
| 4   | STUCK CHECK           | Movement check      | Position compare, battle progress              |
| 5   | VISION                | Visual observations | What's visible on screen                       |
| 6   | STATE                 | Game state facts    | Map, position, HP, team                        |
| 7   | MINIMAP/MOVES/CONTEXT | Screen-specific     | Grid analysis OR move list OR dialogue context |
| 8   | ACTION                | Button presses      | `R;R;R;A;` format                              |
| 9   | REASONING             | Path explanation    | Why this action                                |
| 10  | ALTERNATIVES          | Backup plan         | If blocked/fails                               |
| 11  | COMMENTARY            | Stream personality  | 1-2 sentences for TTS                          |
| 12  | MEMORY_WRITE          | Events to save      | Story events, choices                          |

## Screen-Specific Prompts

### OVERWORLD_PROMPT

Used for exploration and navigation:

```
**7. MINIMAP**: Grid analysis from minimap_data
   - Blocked directions (❌): [list]
   - Walkable directions (✓): [list]
   - Exit tiles: [list with World coords]

**8. ACTION**: Your move chain (2-5 moves)
   - Format: R;R;R;R; (use semicolons)
   - Near exits: use only 2-3 moves!
```

### BATTLE_PROMPT

Used during Pokemon battles:

```
**7. MOVES**: Available move analysis
   - List your moves with PP remaining
   - Note type effectiveness vs enemy
   - Highlight best option

**8. ACTION**: Your button presses
   - Navigate to correct menu option
   - Format: D;R;A; (down, right, confirm)
```

### DIALOGUE_PROMPT

Used when text is displayed:

```
**7. CONTEXT**: Why is this dialogue important?
   - Quest progress? Item receive? Story beat?
   - Reference your memory

**8. ACTION**: Your button press(es)
   - A; to advance text
   - B;B;B;B; to escape repetitive dialogue
```

## Action Format

Actions are semicolon-separated button sequences:

| Button | Meaning        | Examples                   |
| ------ | -------------- | -------------------------- |
| `U`    | Up/North       | `U;U;U;` = move up 3 tiles |
| `D`    | Down/South     | `D;A;` = down then confirm |
| `L`    | Left/West      | `L;L;` = move left 2 tiles |
| `R`    | Right/East     | `R;R;R;R;` = move right 4  |
| `A`    | Confirm/Select | `A;` = single confirm      |
| `B`    | Cancel/Back    | `B;B;B;B;` = spam cancel   |
| `S`    | Start menu     | `S;` = open menu           |

## Data Trust Hierarchy

The prompt explicitly tells the LLM to trust data sources in this order:

1. **game_state** = ABSOLUTE TRUTH (map_name, position from RAM)
2. **minimap** = Reliable (tile analysis)
3. **memory_context** = Reliable (but exit coords are approximate ±2 tiles)
4. **vision** = UNRELIABLE (hallucination-prone)

## Commentary Rules

Section 11 (COMMENTARY) is extracted for TTS. Rules:

- 1-2 fun sentences only
- NO button names (U, D, L, R, A, B)
- React to what's happening in-game
- Reference player history when relevant
- Speak as "Lass" character personality

## Memory Write Format

Section 12 (MEMORY_WRITE) is parsed for persistence:

```
12. **MEMORY_WRITE**: Chose Charmander as my starter!
```

Valid examples:

- "Got Oak's Parcel from the shopkeeper"
- "Beat Brock, earned Boulder Badge!"
- "Named my rival GARY"
- "None" (if nothing important)

Parsed by: `trackers/memory_storage.py` → `_extract_narrative_memories()`

## Prompt File Location

All prompts are defined in: [core/prompts.py](../core/prompts.py)

Key functions:

- `get_base_prompt()` - Core system prompt
- `get_screen_specific_prompt(screen_type)` - Returns appropriate screen prompt
- `build_system_prompt(...)` - Combines base + screen + hints

## Adding a New Screen Type

1. Create `NEW_SCREEN_PROMPT` constant in `prompts.py`
2. Follow 12-section format (customize section 7)
3. Add to `get_screen_specific_prompt()` function
4. Update vision analysis to detect new screen type
5. Test with various game scenarios
