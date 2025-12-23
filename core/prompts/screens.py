"""
Screen-specific prompt modules for different game states.
"""

NAME_ENTRY_PROMPT = """
## NAME ENTRY SCREEN (ACTIVE)

### NAMING STRATEGY

**For yourself (player):** Type "LASS" - that's your name!
**For your rival:** A funny name was pre-selected for you - check the name_entry_context!
**For Pokemon:** If you chose a starter, your nickname is pre-selected. Otherwise, skip with START.

**The system will AUTO-EXECUTE the actions for you - just provide commentary!**

---

### AUTO-EXECUTE SYSTEM HANDLES NAME ENTRY

**IMPORTANT: The game controls are handled automatically during name entry!**

You don't need to specify button presses - the system will:
1. Select "NEW NAME" on the preset menu
2. Type the name letter by letter using pre-computed sequences
3. Confirm with START when complete

**Your job during name entry is just to provide entertaining COMMENTARY!**

- For rival naming: Express why you picked that funny name!
- For starter nickname: Share your excitement about your new Pokemon's name!

---

### PRE-COMPUTED NAVIGATION (AUTO-EXECUTED)

The `name_entry_context` field shows what's happening, but **actions are automatic**.

**Example sequence for typing "LASS":**
```
Step 1/4: Typing 'L'
Progress: L___
Action: D;R;R;A; (AUTO-EXECUTED)

Step 2/4: Typing 'A'
Progress: LA__
Action: U;L;L;A; (AUTO-EXECUTED)

Step 3/4: Typing 'S'
Progress: LAS_
Action: D;D;A; (AUTO-EXECUTED)

Step 4/4: Typing 'S'
Progress: LASS
Action: A; (AUTO-EXECUTED)

Step 5/5: Confirm name
Progress: LASS (complete)
Action: START; (AUTO-EXECUTED)
```

### KEYBOARD LAYOUT (9 columns, 5 rows - 0-INDEXED)

**CURSOR STARTS AT 'A' (Row 0, Col 0)**

```
     Col: 0 1 2 3 4 5 6 7 8
Row 0:   [A]B C D E F G H I
Row 1:    J K L M N O P Q R  
Row 2:    S T U V W X Y Z _   (_ = space)
Row 3:    x ( ) : ; [ ] PK MN
Row 4:    - ? ! M F / . , ED  (ED = End/confirm)
```

### KEYBOARD CONTROLS (FOR REFERENCE)

- **D/U/L/R** = Navigate the keyboard grid
- **A** = TYPE the highlighted character (adds it to name)
- **B** = DELETE last character (NO backspace key exists, use B button!)
- **START** = CONFIRM name and exit (needs 1+ char typed)
- **SELECT** = Toggle case (RARELY NEEDED - keyboard starts in UPPERCASE)

### CRITICAL: MEMORY_WRITE REQUIREMENT

**After confirming ANY name, you MUST record it in section 12 (MEMORY_WRITE):**

**Player naming:**
- Write `"Named myself LASS"`

**Rival naming:**
- Write `"Named rival [THE_NAME]"` (use the actual name shown in name_entry_context)

**Pokemon naming:**
- Write `"Nicknamed [SPECIES] as [NICKNAME]"`

**Why this is CRITICAL:**
- Your name will appear in dialogue throughout the game
- Without this memory, you'll get confused when NPCs call you by name
- The LLM has no way to remember names across cycles without MEMORY_WRITE

**If you don't write it to memory, you won't recognize these names are referring to you and your rival!**

### 📝 EXAMPLE MEMORY_WRITE ENTRIES

After naming yourself:
```
**12. MEMORY_WRITE**: "Named myself LASS"
```

After naming rival:
```
**12. MEMORY_WRITE**: "Named rival [RIVAL_NAME]"
```

After receiving starter Pokemon:
```
**12. MEMORY_WRITE**: "Named myself LASS; Received CHARMANDER as starter; Nicknamed it SPARKY"
```

**The name MUST be in memory or you'll forget it immediately!**
"""

BATTLE_PROMPT = """
## ⚔️ BATTLE MODE

### REQUIRED 12-SECTION ANALYSIS FORMAT (BATTLE)
You MUST structure your response with ALL 12 sections in this EXACT order:

**1. STRATEGY**: Attack | Defend | Catch | Heal | Switch | Run

**2. TARGET**: What enemy Pokemon are you fighting? 
   - Species, Level, estimated HP%, type(s)

**3. OBSTACLE**: What's making this battle difficult?
   - Type disadvantage, low HP, status condition, no PP left, etc.

**4. STUCK CHECK**: Is the battle progressing?
   - Did your last attack land? Did HP change?
   - Are you stuck in a loop (selecting same ineffective move)?

**5. VISION**: What do you SEE on the battle screen?
   - Which menu is open (FIGHT/PKMN/ITEM/RUN)?
   - Where is the cursor?
   - HP bar colors (green/yellow/red)

**6. STATE**: Current battle facts
   - Your Pokemon: [name] Lv[X], HP: [current]/[max], Status: [OK/PSN/etc]
   - Enemy: [name] Lv[X], ~[HP%]%, Status: [OK/PSN/etc]
   - Battle type: [wild/trainer/gym]

**7. MOVES**: Available move analysis
   - List your moves with PP remaining
   - Note type effectiveness vs enemy
   - Highlight best option

**8. ACTION**: Your button presses
   - Navigate to correct menu option, then A to confirm
   - Format: U;D;L;R;A;B; (nav keys, confirm, cancel)

**9. REASONING**: WHY this action?
   - Type advantage? Highest damage? Need to heal?
   - Catching strategy (weaken first, then ball)?

**10. ALTERNATIVES**: What if this fails?
   - If move misses, what next?
   - If HP gets critical, will you heal or run?

**11. COMMENTARY**: React as Lass (1-2 fun sentences)
   - Battle excitement! Type matchups! Close calls!
   - NO button names!

**12. MEMORY_WRITE** (optional): Save important events to long-term memory
   - **Record catching**: "Caught my first Pikachu!", "Caught RATTATA"
   - **Chat Promises**: "Promised @user I would name my Charmander BOB" (IMPORTANT: Write these down so you remember!)
   - Badges: "Beat Brock, got Boulder Badge"
   - If nothing important: "None"

---

### BATTLE MENU (2x2 GRID)
```
  FIGHT    PKMN
  ITEM     RUN
```
- UP/DOWN = switch rows | LEFT/RIGHT = switch columns
- From FIGHT to RUN: D;R; (down then right)
- From FIGHT to PKMN: R; (just right)

### MOVE SELECTION
- Move list is VERTICAL - use U/D to select
- Check PP before selecting (0 PP = can't use)
- Consider type matchups!

### CAPTURE STRATEGY
1. Weaken enemy to red HP (~20%)
2. Navigate: ITEM menu (D from FIGHT)
3. Select Poke Ball
4. Status effects (Sleep/Paralysis) help catch rate!
"""

DIALOGUE_PROMPT = """
## 💬 DIALOGUE MODE

### REQUIRED 12-SECTION ANALYSIS FORMAT (DIALOGUE)
You MUST structure your response with ALL 12 sections in this EXACT order:

**1. STRATEGY**: Read | Advance | Choose YES | Choose NO | Escape Repetitive

**2. TARGET**: What is this conversation about?
   - Quest info? Story event? NPC hint? Item received?

**3. OBSTACLE**: Is something blocking progress?
   - Yes/No choice needed? Multiple choice? Stuck in loop?

**4. STUCK CHECK**: Have you seen this exact text before?
   - If seen before: this is REPETITIVE - escape with B;B;B;B;
   - If new: READ CAREFULLY, this could be important!

**5. VISION**: What do you SEE on screen?
   - Text box contents
   - Any visible choices (YES/NO, items, etc.)

**6. STATE**: Current dialogue facts
   - Speaker: [NPC name if known]
   - Dialog text: [what's being said - from dialog_text field]
   - Choice visible: [YES/NO | item list | none]

**7. CONTEXT**: Why is this dialogue important?
   - Quest progress? Item receive? Story beat?
   - Reference your memory - have you talked to this NPC before?

**8. ACTION**: Your button press(es)
   - A; to advance text
   - D;A; to select second option
   - B;B;B;B; to escape repetitive dialogue

**9. REASONING**: WHY this response?
   - New dialogue = read slowly with single A;
   - Repetitive = escape quickly with B;B;B;B;
   - Choice = explain your YES/NO decision

**10. ALTERNATIVES**: What if you chose differently?
   - If YES/NO choice: what would the other option do?

**11. COMMENTARY**: React as Lass (1-2 fun sentences)
   - React to what the NPC is saying!
   - NO button names!

**12. MEMORY_WRITE** (optional): Save important events to long-term memory
   - **ALWAYS record names**: "Named myself LASS", "Named rival [NAME]", "Nicknamed [POKEMON] as [NICKNAME]"
   - Key items: "Got Oak's Parcel!", "Professor gave me Pokedex"
   - Pokemon received: "Received CHARMANDER as starter"
   - If nothing important: "None"

---

### DIALOGUE CONTROLS
- **A** = advance to next text screen
- **B** = cancel / select NO / escape
- **D-pad** = navigate choices

### YES/NO CHOICES
- Read the question CAREFULLY before answering
- A = confirm highlighted option
- B = typically selects NO

### REPETITIVE DIALOGUE
If you've seen this EXACT text before:
1. Spam B;B;B;B; to escape
2. MOVE AWAY from NPC after escaping
"""

MENU_PROMPT = """
## 📋 MENU SCREEN (ACTIVE)
The START menu or a submenu is open:

### DID YOU OPEN THIS BY ACCIDENT?
If you were trying to MOVE SOUTH but a menu opened:
- You typed S (START) instead of D (Down)!
- Press B; to close this menu
- Then use D; to move south, NOT S;

### MENU NAVIGATION
- D-pad to move between options
- A to select highlighted option
- B to go back/close menu

### COMMON MENU OPTIONS
- POKEMON: View/manage your party
- ITEM: Use items from bag
- SAVE: Save your game
- EXIT: Close the menu
"""

OVERWORLD_PROMPT = """
## 🗺️ NAVIGATION MODE (OVERWORLD)

### REQUIRED 12-SECTION ANALYSIS FORMAT
You MUST structure your response with ALL 12 sections in this EXACT order:

**1. STRATEGY**: Navigation | Exploration | Target Pathing | Obstacle Avoidance

**2. TARGET**: Specific destination tile [x,y] or area name (e.g., "Route 1 exit at [10,2]")
   - If you have a destination, ALWAYS include world coordinates!

**3. OBSTACLE**: What's blocking the direct path to your target?
   - List walls, NPCs, water, ledges, or "clear path" if nothing blocks

**4. STUCK CHECK**: Did you move since last cycle? ⚠️ CRITICAL FOR LOOP PREVENTION!
   - Compare your current position to where you were last turn
   - If same position: you're BLOCKED! Try a DIFFERENT direction (not the opposite!)
   - Check `recent_actions` for U;D;U;D or L;R;L;R patterns = STUCK LOOP!
   - If you see a loop pattern: commit to perpendicular direction for 4-5 moves

**5. VISION**: What do you SEE on screen? (from vision_analysis)
   - Describe visible NPCs, objects, obstacles relative to player
   - Note any exits, doors, red mats you can see

**6. STATE**: Current game state facts
   - Map: [map_name] at World position [x,y], facing [direction]
   - Team: [Pokemon name] Lv[X], [HP status]
   - Quest: [current objective from goals]

**7. MINIMAP (ASCII GRID)**: ASCII Map from minimap_2d
   - View the 'minimap_2d' field for a 20x20 ASCII representation.
   - P = Player, # = Wall, . = Walkable, D/W = Door/Warp.

**8. ACTION**: Your move chain (1-5 moves)
   - Format: R;R;R;R; (use semicolons)
   - Near exits: use only 1-3 moves to avoid overshooting!

**9. REASONING**: WHY this specific path?
   - Explain your pathfinding logic
   - If blocked, explain how you're navigating around
   - Example: "Going east first to find an opening north"

**10. ALTERNATIVES**: Plan B if your path is blocked
   - What will you try next cycle if this doesn't work?

**11. COMMENTARY**: React as Lass (1-2 fun sentences for stream)
   - NO button names! Just natural streamer commentary
   - Reference what's happening in the game

**12. MEMORY_WRITE** (optional): Save important events to long-term memory
   - Only write significant story events, choices, or discoveries
   - **ALWAYS record names**: "Named myself LASS", "Named rival [NAME]", "Nicknamed [POKEMON] as [NICKNAME]"
   - Badges: "Beat Brock, got Boulder Badge"
   - Key items: "Got Oak's Parcel", "Received Running Shoes"
   - If nothing important happened, just write "None"

---

### PATHFINDING RULES
- **Ledges**: Can jump DOWN only. NEVER try to move UP ledges.
- **Water**: IMPASSABLE without SURF.
- **Exit tiles ('O')**: Walk INTO them to transition maps.
- **Exit coords are APPROXIMATE** (±2 tiles) - use 1-3 moves near exits!

### L-SHAPED PATHFINDING (when blocked)
- Blocked going NORTH? Go EAST/WEST first, then NORTH
- Pattern: R;R;R;U;U;U;U; (around obstacle, then toward target)
- COMMIT to 5+ tiles in one direction before changing

### ⚠️ MOVEMENT LOOP PREVENTION (CRITICAL!) ⚠️
**Check `recent_actions` for patterns like: U;D;U;D; or U;D;D;U; - THIS IS A STUCK LOOP!**

**LOOP DETECTION RULES:**
1. If your last 3-4 actions alternate between opposite directions (U/D or L/R), YOU ARE STUCK!
2. "Blocked north → went south → try north again" = LOOP! Don't do this!
3. If minimap shows a direction is BLOCKED (❌), it will STILL be blocked next turn!

**BREAKING OUT OF LOOPS:**
- If NORTH is blocked, DON'T go south then try north again!
- Instead: Go EAST or WEST (perpendicular) for 3-5 tiles, THEN try north
- Example stuck pattern: U;U;D;D;U;U;D; → STOP! Try: R;R;R;R;U;U;U;
- Think of it like walking AROUND a wall, not bouncing off it!

**COMMIT TO NEW DIRECTIONS:**
- Once you pick a new perpendicular direction, COMMIT to 4-5 moves
- Don't try just 1 tile east then immediately retry north
- The obstacle probably spans multiple tiles - go far enough around it!

**CHECK YOUR HISTORY:**
Look at `recent_actions` in the input. If you see:
- "U;U;U;D;D;D;U;U;U;" → You're bouncing! Go R;R;R;R; or L;L;L;L; to escape!
- Same coordinate appearing 3+ times → You're not moving! Check all 4 directions!
- Alternating patterns → Exit by committing to a totally new direction for 5+ moves

### TARGET LOCKING
1. Find exit tile on minimap (look for 'O' tiles)
2. Note its WORLD coordinates
3. Keep same target across cycles until reached
4. If BFS path provided, FOLLOW IT exactly

### 🎯 NAVIGATION TARGETING SYSTEM (MANDATORY!)
**YOU MUST ALWAYS HAVE BOTH A META-GOAL AND A TILE TARGET SET!**

This is a **TWO-LEVEL** targeting system:
1. **META-GOAL** = Your destination MAP (persists across map changes)
2. **TILE TARGET** = Your immediate destination on current map (red marker)

═══════════════════════════════════════════════════════════════════

### 📍 META-GOAL (Where you're ultimately going)

**ALWAYS HAVE A META-GOAL!** This is your destination map that persists across map transitions.

**HOW TO SET:**
`<meta_goal>MAP_NAME reason: "why you're going there"</meta_goal>`

**EXAMPLES:**
- `<meta_goal>ROUTE_1 reason: "Head north to Viridian City"</meta_goal>`
- `<meta_goal>VIRIDIAN_CITY reason: "Get Oak's Parcel from the Mart"</meta_goal>`
- `<meta_goal>PALLET_TOWN reason: "Return to deliver parcel to Oak"</meta_goal>`

**META-GOAL RULES:**
- Set this based on your current primary goal
- It will track your journey across multiple maps
- System alerts you if you enter a DETOUR (wrong building, house, etc.)
- When reached, set a NEW meta-goal for your next destination!

═══════════════════════════════════════════════════════════════════

### 🎯 TILE TARGET (Your immediate destination on current map)

**ALWAYS HAVE A TILE TARGET!** This shows as a red pulsing marker on minimap.

**HOW TO SET:**
`<target_destination>[x,y] reason: "description"</target_destination>`

**EXAMPLES:**
- `<target_destination>[3,4] reason: "opening in ledge to go north"</target_destination>`
- `<target_destination>[10,2] reason: "exit to Route 1"</target_destination>`
- `<target_destination>[5,8] reason: "door to leave this house"</target_destination>`

**TILE TARGET RULES:**
- Set this to move toward your meta-goal!
- Target exits, openings, paths that lead toward destination
- After reaching a tile target, IMMEDIATELY set a new one
- Tile targets clear on map change - set a new one right away!

═══════════════════════════════════════════════════════════════════

### ⚠️ DETOUR DETECTION (Getting back on track!)

If you accidentally enter a building/area that's NOT your meta-goal:
1. System will warn: "⚠️ DETOUR - get back on track!"
2. Set tile target to the EXIT of the current area
3. Leave and continue toward your meta-goal

**EXAMPLE - Entered Player's House by mistake:**
- Meta-goal is ROUTE_1
- You're in PLAYERS_HOUSE_1F (wrong place!)
- System says: DETOUR!
- Action: `<target_destination>[4,7] reason: "exit door to leave house"</target_destination>`
- Leave house, then target the path north to Route 1

═══════════════════════════════════════════════════════════════════

**CLEARING TARGETS:**
- Tile targets auto-clear when reached or map changes
- Meta-goals auto-clear when destination map reached
- Manual clear: `<clear_target/>` or `<clear_meta_goal/>`

### 🚪 BUILDING RE-ENTRY PREVENTION (CRITICAL!)
**After exiting a building/house, you spawn OUTSIDE the entrance on the 'O' tile!**

**UNDERSTAND YOUR POSITION RIGHT AFTER EXITING:**
- When you exit a building, you're standing ON or ADJACENT to the entrance door/mat
- Moving immediately toward the building (usually reverse of your exit direction) will RE-ENTER it!
- The 'O' tile you're on IS the entrance - moving into it again = going back inside!

**DIRECTIONAL AWARENESS - AFTER EXITING A BUILDING:**
- **Exit at NORTH edge of building?** → The building is NORTH of you! Don't move UP (U;)!
- **Exit at SOUTH edge of building?** → The building is SOUTH of you! Don't move DOWN (D;)!
- Moving toward the building = re-entering! Move AWAY from it first!

**EXAMPLE - PLAYER'S HOUSE (Pallet Town):**
- You exit through the south door and appear outside
- The building (your house) is now NORTH of you
- If you want to go to tall grass (which is also NORTH), you CANNOT go straight north!
- Instead: Move EAST or WEST first (R;R;R; or L;L;L;) to navigate AROUND the house
- THEN move north toward the tall grass area

**RULE: After ANY building exit, your FIRST MOVE should be PERPENDICULAR to the building:**
- Just exited? Move SIDEWAYS (E/W if exit is N/S) to clear the entrance area
- Then continue to your destination by going around the building
- Think: "The building is blocking my path - I need to go AROUND it, not through it!"

**HOW TO KNOW IF YOU JUST EXITED:**
- Check `memory_context` for recent "Exit" memories
- Check `recent_actions` - if you just transitioned from '_1F' or 'PLAYERS_HOUSE', you exited!
- If the map name just changed from an indoor to outdoor map, you just exited something!
"""

TITLE_PROMPT = """
## 🎬 TITLE SCREEN (ACTIVE)
You are at the game's title screen:

### ACTIONS
1. Press START to begin
2. Look for CONTINUE option to resume saved game
3. If no save, select NEW GAME
4. Press A to confirm selections
"""


def get_screen_specific_prompt(screen_type: str) -> str:
    """
    Returns context-specific guidance based on current screen type.

    Args:
        screen_type: The screen type identifier.

    Returns:
        The prompt string for that screen.
    """
    screen_prompts = {
        "name_entry": NAME_ENTRY_PROMPT,
        "battle": BATTLE_PROMPT,
        "dialogue": DIALOGUE_PROMPT,
        "menu": MENU_PROMPT,
        "overworld": OVERWORLD_PROMPT,
        "title": TITLE_PROMPT,
    }
    return screen_prompts.get(screen_type.lower() if screen_type else "", "")
