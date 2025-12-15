# Persistence & Memory Storage

The agent uses several file-based storage mechanisms to persist state between runs.

## Data Directory (`data/`)

All JSON persistence files are stored in the `data/` directory.

### `memories.json` (Game Memory)

Stores the agent's long-term memory of the game world.

**Structure:**

```json
{
  "spatial": {
    "Pallet Town": { "exits": [...], "buildings": [...] }
  },
  "narrative": [
    { "text": "Chose Charmander", "timestamp": 1234567890 }
  ],
  "gameplay": [
    { "text": "Defeated Brock", "timestamp": 1234567890 }
  ],
  "feedback": [],
  "quests": {
    "active": [],
    "completed": []
  }
}
```

- **Managed by:** `trackers/memory_storage.py`
- **Updated:** Every cycle when `MEMORY_WRITE` prompt section is populated.

### `twitch_chatters.json` (Social Memory)

Stores profiles of Twitch users who interact with the stream.

**Structure:**

```json
{
  "username": {
    "username": "user123",
    "display_name": "User123",
    "first_seen": 1700000000,
    "last_seen": 1700000500,
    "interaction_count": 42,
    "sentiment_score": 5.0,
    "relationship_tier": "Regular"
  }
}
```

- **Managed by:** `services/twitch_engagement_service.py`
- **Updated:** On every chat message.

## Root Directory Files

### `coordinate_history.json` (Navigation)

Stores the last 100 positions to help detect when the agent is stuck in a loop.

**Structure:** List of `[map_id, x, y]` tuples.

- **Managed by:** `trackers/map_visit_tracker.py`

## Save States (`roms/`)

The emulator state is persisted using mGBA save states.

- **Files:** `*.ss1` (e.g., `firered.ss1`)
- **Managed by:** mGBA (auto-save/load via Python commands)
- **Frequency:** Saved at the end of every action cycle.
