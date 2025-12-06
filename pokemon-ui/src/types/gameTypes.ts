export type PokemonType =
  | "Normal"
  | "Fire"
  | "Water"
  | "Electric"
  | "Grass"
  | "Ice"
  | "Fighting"
  | "Poison"
  | "Ground"
  | "Flying"
  | "Psychic"
  | "Bug"
  | "Rock"
  | "Ghost"
  | "Dragon"
  | "Dark"
  | "Steel"
  | "Fairy";

export type BadgeType =
  | "Boulder"
  | "Cascade"
  | "Thunder"
  | "Rainbow"
  | "Soul"
  | "Marsh"
  | "Volcano"
  | "Earth";

export type StatusCondition =
  | "None"
  | "Poison"
  | "Burn"
  | "Freeze"
  | "Paralyze"
  | "Sleep"
  | "Confusion"
  | "Faint";

export interface Pokemon {
  id: string;
  name: string;
  nickname?: string;
  level: number;
  type: PokemonType;
  // Secondary type for dual-type Pokemon
  type2?: PokemonType;

  // Current/Max Stats
  hp: number;
  maxHp: number;

  // Combat Stats
  attack?: number;
  defense?: number;
  speed?: number;
  special?: number;
  specialAttack?: number;
  specialDefense?: number;

  // Experience
  exp?: number;
  expToNext?: number;

  // Status
  status?: StatusCondition;
  isFainted: boolean;

  // Moves (up to 4)
  moves?: Move[];

  // Position/Location
  x?: number;
  y?: number;
  location?: string;

  // Additional metadata
  ability?: string;
  nature?: string;
  item?: string;
}

export interface Move {
  name: string;
  type: PokemonType;
  power?: number;
  accuracy?: number;
  pp: number;
  currentPp: number;
  category?: "Physical" | "Special" | "Status";
}

export interface LocationInfo {
  name: string;
  area: string;
  region: string;
  coordinates?: [number, number];
}

export interface BattleForecast {
  attacker: {
    pokemon: Pokemon;
    damage: number;
    accuracy: number;
    criticalHit: boolean;
    effectiveness?: "Not very effective" | "Normal" | "Super effective";
  };
  defender: {
    pokemon: Pokemon;
    damage: number;
    accuracy: number;
    criticalHit: boolean;
    effectiveness?: "Not very effective" | "Normal" | "Super effective";
  };
}

export interface Badge {
  name: BadgeType;
  gymLeader?: string;
  location: string;
  earned: boolean;
}

export interface PokemonGameState {
  // Badges
  badges: BadgeType[];
  badgeDetails?: Badge[];

  // Objectives (from Vue app)
  goals: {
    primary: string;
    secondary: string[] | string; // Can be array or string
    tertiary: string;
  };
  otherGoals: string;

  // Location Info
  currentLocation?: string;
  locationDetails?: LocationInfo;

  // Map/Minimap Info
  minimapLocation: string;
  mapWidth?: number;
  mapHeight?: number;
  cursorPosition?: [number, number];
  cameraPosition?: [number, number];

  // Pokemon Team
  currentTeam: Pokemon[]; // From backend WebSocket
  party?: Pokemon[];
  pcBox?: Pokemon[];
  enemyPokemon?: Pokemon[];
  wildPokemon?: Pokemon[];

  // Current State
  selectedPokemon?: Pokemon;
  battleForecast?: BattleForecast;
  inBattle?: boolean;
  battleType?: "Wild" | "Trainer" | "Gym" | "Elite Four" | "Champion";

  // Game Stats
  actions: number;
  gameStatus: string;
  processingStatus?: string; // Detailed status: "ANALYZING VISION...", "RETRYING VISION (2/5)...", "THINKING..."
  modelName: string;
  tokensUsed: number;

  // UI State
  inMenu?: boolean;
  menuType?: string;

  // Display
  screenshotUrl?: string;
  minimapSrc?: string;
  minimapVisible: boolean;
  llmMetrics?: {
    p50LatencySec?: number;
    p95LatencySec?: number;
    successRate?: number; // 0..1
  };
}

// Legacy interface for compatibility with existing components
export interface GameState extends PokemonGameState {}

export interface LogEntry {
  id?: string | number;
  timestamp?: string;
  type:
    | "action"
    | "battle"
    | "system"
    | "error"
    | "ai"
    | "combat"
    | "movement"
    | "info"
    | "vision"
    | "response";
  message?: string;
  text?: string;
  is_action?: boolean;
  is_vision?: boolean;
  is_response?: boolean;
  // Action range fields for displaying "#120 - #123" style labels
  action_start?: number;
  action_end?: number;
  button_count?: number;
  // Strictly synchronized screenshot data
  screenshot_base64?: string;
}

export interface PokemonLogEntry extends LogEntry {
  // Pokemon-specific log categories
  category?:
    | "wild_encounter"
    | "trainer_battle"
    | "capture"
    | "evolution"
    | "level_up"
    | "badge_earned"
    | "move_learned"
    | "item_found"
    | "location_change";
}

export interface ChronicleEntry {
  id?: string;
  session_id?: string;
  timestamp: string;
  location?: string | null; // Changed from chapter
  phase?: string;
  interpretation?: string;
  narrative?: string;
  summary?: string;
  screenshot?: string;
  screenshot_url?: string;
  actions?: string[];
}

export interface SessionInfo {
  session_id: string;
  start_time: string;
  end_time?: string;
  location_start?: string; // Changed from chapter_start
  location_current?: string; // Changed from chapter_current
  total_actions: number;
  status: "active" | "completed" | "interrupted";
  screenshot_count: number;
}
