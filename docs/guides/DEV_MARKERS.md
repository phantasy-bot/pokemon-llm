# Dev Markers System Implementation

## Summary

Implemented a developer-defined marker system for special locations in the game that aren't automatically detected by the game state parser. This helps the LLM agent identify and navigate to important locations like starter Pokémon in Oak's Lab.

## Components Created

### 1. `core/dev_markers.py` - Main Module

**DevMarker Class:**
- Represents a static developer-defined marker
- Fields:
  - `world_x`, `world_y`: Absolute map coordinates
  - `map_name`, `map_id`: Map identification
  - `marker_type`: "STARTER_POKEMON", "ITEM", "OBJECTIVE", "HINT"
  - `label`: Short label (e.g., "Charmander")
  - `description`: Full description for LLM context
  - `marker_char`: Visual character for minimap ('C', 'S', 'B', 'O', etc.)
  - `requires_facing`: Whether player must face the tile
  - `facing_direction`: Required facing direction

**DevMarkerRegistry Class:**
- Singleton registry managing all dev markers
- Methods:
  - `get_markers_for_map(map_name, marker_type)`: Get markers for a specific map
  - `get_overlay_markers_for_map(...)`: Convert to minimap overlay format
  - `get_llm_context_for_map(...)`: Generate formatted context for LLM
  - `get_starter_pokemon_choices(map_name)`: Get starter Pokémon markers

**Default Markers - Oak's Lab:**
```python
# Starter Pokémon positions
Charmander: [6,3] - marker_char: 'C'
Squirtle:   [7,3] - marker_char: 'S'
Bulbasaur:  [8,3] - marker_char: 'B'

# Professor Oak
Professor Oak: [5,2] - marker_char: 'O'
```

### 2. Integration with `core/llmdriver.py`

**Two Integration Points:**

1. **Minimap Overlay** (line ~2067):
   - Dev markers are added to `lassMarkings` array
   - Displayed on the minimap overlay alongside player-created markers
   - Automatically filtered to only show markers in current viewport
   - Uses same coordinate transformation as other markers

2. **LLM Context** (line ~1520):
   - Dev marker context injected into `llm_input_state["special_locations"]`
   - Special handling for starter Pokémon:
     - Adds `llm_input_state["starter_choice_available"]` when starters detected
     - Prompts LLM to choose and navigate to a starter
   - Includes distance and direction hints to each marker

### 3. Test Script - `test_dev_markers.py`

Comprehensive test suite validating:
- ✅ Marker registration and retrieval
- ✅ Correct positions for all 3 starters
- ✅ Overlay marker generation with coordinate transformation
- ✅ LLM context formatting
- ✅ Adjacent tile interaction requirements

## How It Works

### Coordinate System

```
World Coordinates [absolute]  →  Grid Coordinates [viewport-relative]
        ↓                                   ↓
   Marker at [6,3]           Player at [5,4] (world) = [10,10] (grid)
                            Marker becomes [11,9] (grid)
```

### Minimap Display

Dev markers appear on the minimap with distinct characters:
- **C** = Charmander (Fire starter)
- **S** = Squirtle (Water starter)  
- **B** = Bulbasaur (Grass starter)
- **O** = Professor Oak / Objectives
- **T** = Player-set navigation targets (from TargetTracker)
- **N** = NPCs (from Lass markings)

### LLM Interaction Flow

1. **Detection**: When player enters Oak's Lab, dev markers are loaded
2. **Context**: LLM receives:
   - List of special locations with positions
   - Distance and direction to each
   - Interaction requirements (must face tile, press A)
   - Starter choice prompt if applicable
3. **Navigation**: LLM can set navigation target to chosen starter
4. **Interaction**: Once adjacent and facing, LLM presses A to choose

## Example LLM Context

When player is at [5,4] in Oak's Lab:

```
═══════════════════════════════════════
📍 SPECIAL LOCATIONS (Dev Markers)
═══════════════════════════════════════

STARTER_POKEMON:
  • [6,3] Charmander (face north) - Fire-type starter Pokémon
    Distance: 2 tiles NORTH-EAST
  • [7,3] Squirtle (face north) - Water-type starter Pokémon
    Distance: 3 tiles NORTH-EAST
  • [8,3] Bulbasaur (face north) - Grass/Poison-type starter Pokémon
    Distance: 4 tiles NORTH-EAST

⭐ CHOOSE YOUR STARTER POKEMON! Available: Charmander, Squirtle, Bulbasaur
To choose, navigate to adjacent tile and face the Pokéball, then press A.
Set a navigation target to the starter you want!
```

## Usage

### For Developers - Adding New Markers

Edit `core/dev_markers.py` in the `_register_default_markers()` method:

```python
self.add_marker(DevMarker(
    world_x=10,
    world_y=5,
    map_name="VIRIDIAN_POKECENTER",
    map_id=123,
    marker_type="ITEM",
    label="Potion",
    description="Free Potion on counter",
    marker_char="I",  # I for Item
    requires_facing=True
))
```

### For the LLM Agent

The LLM will automatically receive:
- Visual markers on minimap (if in viewport)
- Text context with locations and instructions
- Special prompts for important choices (like starters)

The LLM can then:
1. Choose which starter it wants
2. Set navigation target: `<target_destination>[6,3] reason: "Get Charmander"</target_destination>`
3. Navigate to adjacent tile
4. Face the tile (by moving to south of it)
5. Press A to interact

## Benefits

1. **Clear Guidance**: LLM knows exact positions of important items/NPCs
2. **Visual Aid**: Markers visible on minimap for path planning
3. **Game Progress**: Helps LLM make critical choices (starter selection)
4. **Extensible**: Easy to add new markers for other important locations
5. **Integration**: Works seamlessly with existing navigation and pathfinding systems

## Future Enhancements

Potential additions:
- Mark Poké Center healing stations
- Mark Poké Mart entrances/exits
- Mark gym leader positions
- Mark important NPCs (Oak's Parcel delivery, etc.)
- Mark HM/TM locations
- Mark legendary Pokémon positions

## Testing

Run test suite:
```bash
python test_dev_markers.py
```

Expected output: All tests pass with ✅ markers showing correct positions and coordinate transformations.
