# Character Assets Documentation

This document describes all character avatar images used in the Pokemon LLM stream overlay.

## Lass Character

The main character "Lass" is a female Pokemon trainer who reacts dynamically to game events.

### Asset Location

All Lass assets are located in: `pokemon-ui/public/lass/`

### Available Poses

| Filename                  | Game State       | Description                | Trigger Condition                            |
| ------------------------- | ---------------- | -------------------------- | -------------------------------------------- |
| `lass-default.png`        | Idle             | Default standing pose      | Fallback if no other state matches           |
| `lass-walking-1.png`      | Walking Frame 1  | Animation frame 1 of 2     | Overworld exploration (alternates)           |
| `lass-walking-2.png`      | Walking Frame 2  | Animation frame 2 of 2     | Overworld exploration (alternates)           |
| `lass-walking.png`        | Walking (static) | Legacy single frame        | Not currently used                           |
| `lass-speech.png`         | Dialogue         | Talking/reading expression | `textState.is_printing === true`             |
| `lass-menu.png`           | Menu Open        | Thoughtful/planning pose   | `inMenu === true`                            |
| `lass-stressed.png`       | Low HP           | Worried expression         | Active Pokemon HP status = "critical"        |
| `lass-battle-wild.png`    | Wild Battle      | Excited battle stance      | `inBattle && battleType.includes("wild")`    |
| `lass-battle-trainer.png` | Trainer Battle   | Competitive stance         | `inBattle && battleType.includes("trainer")` |
| `lass-battle-gym.png`     | Gym Battle       | Intense focus stance       | `inBattle && battleType.includes("gym")`     |
| `lass-victory.png`        | Victory          | Celebration pose           | After winning battle                         |

### State Priority Order

The avatar selection logic in `PokemonStreamOverlay.tsx` follows this priority:

1. **Stressed** (highest) - Active Pokemon is critical HP
2. **Battle States** - Gym > Trainer > Wild > Victory
3. **Dialogue** - Text is printing on screen
4. **Menu** - START menu is open
5. **Walking Animation** (lowest) - Default overworld exploration

### Walking Animation

The walking animation alternates between two frames every 500ms:

- Frame 1: `lass-walking-1.png`
- Frame 2: `lass-walking-2.png`

```typescript
// From PokemonStreamOverlay.tsx
const [walkingFrame, setWalkingFrame] = useState<1 | 2>(1);

useEffect(() => {
  const timer = setInterval(() => {
    setWalkingFrame((prev) => (prev === 1 ? 2 : 1));
  }, 500);
  return () => clearInterval(timer);
}, []);
```

### Image Specifications

| Property    | Value                                           |
| ----------- | ----------------------------------------------- |
| Format      | PNG with transparency                           |
| Resolution  | ~750-950KB per image                            |
| Style       | Anime/manga illustration                        |
| Orientation | Character facing left (looking at game content) |

### Adding New Poses

To add a new pose:

1. Create the image following the style/resolution guidelines above
2. Save to `pokemon-ui/public/lass/lass-{state-name}.png`
3. Update the `getAvatarImage()` function in `PokemonStreamOverlay.tsx`
4. Add condition check based on game state
5. Update this documentation

### Related Files

- **Avatar Logic**: [PokemonStreamOverlay.tsx](../pokemon-ui/src/components/layout/PokemonStreamOverlay.tsx) - `getAvatarImage()` function
- **Game State Types**: [gameTypes.ts](../pokemon-ui/src/types/gameTypes.ts) - `PokemonGameState` interface
