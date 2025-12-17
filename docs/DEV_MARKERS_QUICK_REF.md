# Dev Markers - Quick Reference

## Starter Pokémon Positions in Oak's Lab

```
Oak's Lab Map (Top View):

        [5,2]   [6,2]   [7,2]   [8,2]
          O                              ← Professor Oak (O)
          
        [5,3]   [6,3]   [7,3]   [8,3]
                  C       S       B      ← Pokéballs (C=Charmander, S=Squirtle, B=Bulbasaur)
          
        [5,4]   [6,4]   [7,4]   [8,4]
          P       ↑       ↑       ↑      ← Player can stand here (P), facing north (↑)
```

### Interaction Requirements

To choose a starter Pokémon, the player must:

1. **Position**: Be in an **adjacent** tile to the Pokéball
2. **Face**: Face **toward** the Pokéball (usually north if standing south of it)
3. **Action**: Press **A** button to interact

### Example: Choosing Charmander

```
Step 1: Navigate to [6,4] (south of Charmander's Pokéball)
Step 2: Face NORTH (toward [6,3])
Step 3: Press A
```

LLM command sequence:
```xml
<target_destination>[6,4] reason: "Position to get Charmander"</target_destination>
```

Then when adjacent:
```
Action: U;A;  (move Up to face north, then press A)
```

## Minimap Overlay

When player is at [5,4] in Oak's Lab, the minimap shows:

```
Minimap Grid (21x19, player at center [10,10]):

       9    10   11   12   13
    ┌────┬────┬────┬────┬────┐
  8 │    │ O  │    │    │    │  ← Professor Oak
    ├────┼────┼────┼────┼────┤
  9 │    │    │ C  │ S  │ B  │  ← Starter Pokéballs
    ├────┼────┼────┼────┼────┤
 10 │    │ P  │    │    │    │  ← Player position
    └────┴────┴────┴────┴────┘

Legend:
  P = Player
  O = Objective (Professor Oak)
  C = Charmander
  S = Squirtle
  B = Bulbasaur
```

## Pathfinding Integration

Once the LLM chooses a starter, it should:

1. **Set target** to the tile south of chosen starter
2. **Use pathfinding** to navigate there (BFS path will be computed)
3. **Face north** when adjacent
4. **Press A** to interact

Example flow for Squirtle:
```
1. LLM chooses: "I want Squirtle (Water-type)"
2. LLM sets target: <target_destination>[7,4] reason: "Get Squirtle"</target_destination>
3. Pathfinding computes route to [7,4]
4. LLM follows path (e.g., "R;R;U;")
5. When at [7,4], LLM faces north: "U;" 
6. LLM presses A: "A;"
7. Squirtle obtained! 🎉
```

## Adding New Dev Markers

To add markers for other special locations, edit `core/dev_markers.py`:

```python
# Example: Potion in Viridian Poké Center
self.add_marker(DevMarker(
    world_x=10,
    world_y=5,
    map_name="VIRIDIAN_POKECENTER",
    map_id=123,
    marker_type="ITEM",
    label="Free Potion",
    description="Free potion on counter - press A to get it",
    marker_char="I",  # I for Item
    requires_facing=True,
    facing_direction="north"
))
```

## Map IDs Reference

Common map IDs (adjust based on your ROM):
- Oak's Lab: 39
- Pallet Town: 0
- Route 1: 12
- Viridian City: 1
- Viridian Poké Center: ...
- Pewter City: 2

Check actual map IDs from game state or `tools/map_dumper.py`.
