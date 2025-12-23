# UI Components Documentation

This document describes the React component structure and CSS conventions for the Pokemon LLM stream overlay.

## Component Hierarchy

```
PokemonStreamOverlay (main layout)
├── AnalysisPanel (left column)
│   ├── RecentActions
│   ├── VisionScreenshot
│   └── LogEntry (list)
├── PokemonTeamBar (center bottom)
│   ├── PokemonCard (×6)
│   ├── PokemonEmptySlot (×remaining)
│   └── Minimap
│       └── LassMinimapOverlay
└── Goals/Commentary (right column)
    └── Character Avatar (Lass)
```

## Layout Structure

### Three-Column Layout

```
┌────────────────┬────────────────┬────────────────┐
│  Left Column   │ Center Column  │  Right Column  │
│  (Analysis)    │   (Game Feed)  │   (Character)  │
├────────────────┼────────────────┼────────────────┤
│ • Title        │ • Badges       │ • Folder UI    │
│ • Recent       │ • Game         │ • Stats        │
│   Actions      │   Placeholder  │ • Goals        │
│ • Vision       │ • Status Bar   │ • Commentary   │
│ • Analysis Log │ • Team Bar     │ • Lass Avatar  │
│                │   + Minimap    │ • Sponsor      │
└────────────────┴────────────────┴────────────────┘
```

### Column CSS Classes

| Class                 | Current Position | Purpose                 |
| --------------------- | ---------------- | ----------------------- |
| `.pokemon-left-col`   | Left             | LLM Analysis content    |
| `.pokemon-center-col` | Center           | Game feed, badges, team |
| `.pokemon-right-col`  | Right            | Character panel         |

## CSS Naming Convention

We use BEM (Block Element Modifier) naming:

```css
/* Block: main component */
.pokemon-card {
}

/* Element: child of block */
.pokemon-card__sprite {
}
.pokemon-card__name {
}
.pokemon-card__level {
}

/* Modifier: variation */
.pokemon-card--compact {
}

/* State: dynamic condition */
.pokemon-card.fainted {
}
```

### Component-Specific Prefixes

| Prefix                 | Component                      |
| ---------------------- | ------------------------------ |
| `.analysis-panel`      | AnalysisPanel                  |
| `.log-entry`           | LogEntry                       |
| `.recent-actions`      | RecentActions                  |
| `.pokemon-card`        | PokemonCard                    |
| `.pokemon-team-bar`    | PokemonTeamBar                 |
| `.minimap`             | Minimap component              |
| `.lass-overlay`        | LassMinimapOverlay             |
| `.character-container` | Right column character section |
| `.goals-log`           | Goals display                  |
| `.folder-*`            | T3-style folder UI elements    |

## Key Components

### AnalysisPanel

**Purpose**: Displays LLM analysis, vision data, and recent actions.

**File**: `src/components/analysis/AnalysisPanel.tsx`

**Key Props**:

```typescript
interface AnalysisPanelProps {
  logs: LogEntry[];
  totalActions: number;
  isProcessing: boolean;
  memoryWrite?: string | null;
  debugMode?: boolean;
}
```

### PokemonCard

**Purpose**: Displays individual Pokemon stats with HP bar and type badge.

**File**: `src/components/pokemon/PokemonCard.tsx`

**Key Props**:

```typescript
interface PokemonCardProps {
  pokemon: PokemonDisplay;
  compact?: boolean;
}
```

**CSS States**:

- `.fainted` - Grayscale filter, reduced opacity
- `.pokemon-card__header-bar` - Type-colored top bar

### PokemonTeamBar

**Purpose**: Grid of 6 Pokemon cards + minimap.

**File**: `src/components/pokemon/PokemonTeamBar.tsx`

**Layout**:

- Left side: 3×2 grid of Pokemon cards
- Right side: Minimap with overlay

### RecentActions

**Purpose**: Shows last 3 action groups with button squares.

**File**: `src/components/shared/RecentActions.tsx`

**Features**:

- 3-column grid layout
- Numbered action groups
- Flash animation on new actions

### LassMinimapOverlay

**Purpose**: Pink overlay on minimap showing NPCs and exits.

**File**: `src/components/pokemon/LassMinimapOverlay.tsx`

**Markers**:

- `N` = NPC location
- `O` = Exit/Opening

## CSS Variables

All components use CSS custom properties from the root theme:

```css
:root {
  /* Colors */
  --bg-root: #e8e3e2;
  --bg-panel: #ded8d6;
  --bg-card: #f0eae8;
  --text-primary: #2d2a26;
  --text-secondary: #5a5550;
  --accent-primary: #ff6b6b;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;

  /* Typography */
  --font-display: "UltraHyper", sans-serif;
  --font-mono: "Sometype Mono", monospace;

  /* Borders */
  --border-subtle: #d0cac8;
  --border-default: #c0bab8;
}
```

## TUI Box Pattern

Many components use a "TUI box" style with floating labels:

```css
.component {
  border: 1px dotted var(--border-subtle);
  padding: var(--space-md);
  padding-top: var(--space-lg);
  position: relative;
}

.component__label {
  position: absolute;
  top: -8px;
  left: var(--space-md);
  background: var(--bg-panel);
  padding: 0 6px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
```

## State Management

Components receive state via props from `PokemonStreamOverlay`:

1. **WebSocket** → `App.tsx` receives messages
2. **App.tsx** → Parses into typed state
3. **PokemonStreamOverlay** → Distributes to child components

No global state management (Redux/Context) - props drilling is acceptable given the component depth.

## Adding New Components

1. Create component file in appropriate subfolder
2. Create matching CSS file
3. Follow BEM naming with component prefix
4. Use CSS variables for colors/spacing
5. Add TypeScript interface for props
6. Update this documentation
