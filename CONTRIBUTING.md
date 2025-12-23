# Contributing to Pokemon LLM

Thank you for your interest in contributing! This guide covers development setup, code style, and workflow.

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for UI)
- mGBA emulator with scripting support ([dev builds](https://mgba.io/downloads.html#development-downloads))
- Pokemon Red ROM (not included)

### Installation

```bash
# Clone the repository
git clone https://github.com/phantasy-bot/pokemon-llm.git
cd pokemon-llm

# Create conda environment
conda env create -f .conda-env.yml
conda activate pokemon-llm

# Or use pip
pip install -r requirements.txt

# Install UI dependencies
cd apps/livestream
npm install
cd ../..

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application

```bash
# Start everything (recommended)
./start_agent.sh

# Or run components separately:
# Terminal 1: UI
cd apps/livestream && npm run dev

# Terminal 2: Agent
python run.py --mode ZAI --auto
```

## Branch Strategy

| Branch           | Purpose                             |
| ---------------- | ----------------------------------- |
| `production`     | Stable release, deployed to stream  |
| `development`    | Integration branch, tested features |
| `feature/*`      | New features in development         |
| `fix/*`          | Bug fixes                           |
| `experimental/*` | Experiments (may not merge)         |

### Workflow

1. Create feature branch from `development`
2. Make changes and test locally
3. Commit with descriptive messages
4. Push and create PR to `development`
5. After testing, merge `development` → `production`

## Code Style

### Python

- Follow PEP 8
- Use type hints where practical
- Docstrings for public functions
- Log with the `log` logger (not `print`)

```python
def extract_commentary(analysis_text: str) -> Optional[str]:
    """Extract commentary section from LLM analysis.

    Args:
        analysis_text: Full LLM response text

    Returns:
        Commentary string or None if not found
    """
    match = re.search(r'11\.\s*\*{0,2}COMMENTARY', analysis_text)
    return match.group(1) if match else None
```

### TypeScript/React

- Functional components with hooks
- TypeScript interfaces for props
- CSS modules or component CSS files
- BEM-style class naming

```tsx
interface PokemonCardProps {
  pokemon: PokemonDisplay;
  compact?: boolean;
}

export function PokemonCard({ pokemon, compact = false }: PokemonCardProps) {
  return (
    <div className={`pokemon-card ${compact ? "pokemon-card--compact" : ""}`}>
      {/* ... */}
    </div>
  );
}
```

### CSS Naming Conventions

```css
/* Component: .component-name */
.pokemon-card {
}

/* Element: .component-name__element */
.pokemon-card__sprite {
}

/* Modifier: .component-name--modifier */
.pokemon-card--compact {
}

/* State: .component-name.state */
.pokemon-card.fainted {
}
```

## Project Structure

```
pokemon-llm/
├── core/              # Core logic
│   ├── memory/        # Persistent memory
│   │   └── manager.py
│   ├── llmdriver.py   # Main LLM interaction loop
│   ├── prompts.py     # System prompts (12-section format)
│   └── battle_strategy.py
├── services/          # External integrations
│   ├── comfyui_tts_service.py
│   └── websocket_service.py
├── trackers/          # State tracking
│   ├── history_tracker.py
│   └── achievement_tracker.py
├── pyAIAgent/         # mGBA communication
│   ├── game/state.py  # RAM reading
│   └── utils/socket_utils.py
├── apps/              # Frontend applications
│   ├── livestream/    # React stream overlay
│   └── chronicle-worker/ # Cloudflare backend
├── docs/              # Documentation
└── scripts/           # CLI utilities
```

## Key Documentation

- [docs/architecture/MEMORY.md](docs/architecture/MEMORY.md) - RAM addresses and data formats
- [docs/reference/ASSETS.md](docs/reference/ASSETS.md) - Lass avatar poses
- [docs/features/GAME_HINTS.md](docs/features/GAME_HINTS.md) - Area-specific navigation hints

## Testing

```bash
# Run Python tests
python -m pytest tests/

# Test specific module
python -m pytest tests/unit/test_compression.py

# Run UI in dev mode
cd apps/livestream && npm run dev
```

## Common Tasks

### Adding a New LLM Provider

1. Add API configuration to `.env.example`
2. Implement provider in `run.py` (see existing providers)
3. Add to mode selection list
4. Update README.md

### Adding a New Memory Address

1. Find address in [DataCrystal RAM Map](https://datacrystal.romhacking.net/wiki/Pok%C3%A9mon_Red/Blue:RAM_map)
2. Add to `socketserver.lua` if reading from Lua
3. Add to `pyAIAgent/game/state.py` for Python access
4. Document in `docs/architecture/MEMORY.md`

### Modifying the Analysis Format

1. Update prompts in `core/prompts.py`
2. Update UI parsing in `AnalysisPanel.tsx` if needed
3. Update TTS regex in `llmdriver.py` if COMMENTARY moves
4. Update memory regex in `core/memory/manager.py` if MEMORY_WRITE moves

## Questions?

Open an issue or check existing documentation in the `docs/` folder.
