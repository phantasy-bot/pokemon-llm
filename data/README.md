# Runtime Data Files

These files are generated during agent runtime and should **not** be committed to git.

| File                      | Purpose                                     |
| ------------------------- | ------------------------------------------- |
| `coordinate_history.json` | Player position tracking for loop detection |
| `exploration_data.json`   | Map exploration percentages                 |
| `game_goals.json`         | Active goals and objectives                 |
| `pokemon_memories.json`   | Agent's long-term memory storage            |

## Regeneration

All files are automatically regenerated when the agent starts. Delete them to reset state.
