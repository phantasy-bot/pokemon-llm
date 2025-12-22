# --- zora_achievement_tracker.py ---
"""
Zora Achievement Tracker for LLMLetsPlay Brand.

Extends the base AchievementTracker with additional minor achievements
that are posted to Zora only (not Twitter). These create a richer
documentary of the Pokemon journey.

Achievement Tiers:
- MAJOR: Posted to Twitter + Zora with ComfyUI-generated image
- MINOR: Posted to Zora only with screenshot
- PROGRESS: Fallback checkpoint posts (every N cycles with no achievements)

Key Features:
- First-catch-per-species detection (derived from Pokedex state)
- Route/city/dungeon transition detection
- Team change tracking
- HM and key item detection
- Fallback progress checkpoints

Integration:
- Works alongside existing AchievementTracker
- Stores Zora-specific state in separate JSON file
- Provides post counter queried from Zora API on startup
"""

import json
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Set, Any, Tuple
from pathlib import Path

log = logging.getLogger("zora_achievement")


class ZoraAchievementTier(Enum):
    """Achievement tier determines where it's posted and image type."""

    MAJOR = "major"  # Twitter + Zora, ComfyUI image, with footer
    MINOR = "minor"  # Zora only, screenshot, no footer
    PROGRESS = "progress"  # Zora only, screenshot gallery, with footer


class ZoraAchievementType(Enum):
    """
    All achievement types for Zora posting.

    Major achievements match the existing AchievementType values.
    Minor achievements are new and Zora-specific.
    """

    # === MAJOR (Twitter + Zora, ComfyUI image, with cross-promo footer) ===
    STREAM_START = "stream_start"
    BADGE_BOULDER = "badge_boulder"
    BADGE_CASCADE = "badge_cascade"
    BADGE_THUNDER = "badge_thunder"
    BADGE_RAINBOW = "badge_rainbow"
    BADGE_SOUL = "badge_soul"
    BADGE_MARSH = "badge_marsh"
    BADGE_VOLCANO = "badge_volcano"
    BADGE_EARTH = "badge_earth"
    STARTER_EVOLUTION_1 = "starter_evolution_1"
    STARTER_EVOLUTION_2 = "starter_evolution_2"
    LEGENDARY_ARTICUNO = "legendary_articuno"
    LEGENDARY_ZAPDOS = "legendary_zapdos"
    LEGENDARY_MOLTRES = "legendary_moltres"
    LEGENDARY_MEWTWO = "legendary_mewtwo"
    POKEMON_CHAMPION = "pokemon_champion"
    FIRST_POKEMON = "first_pokemon"
    FIRST_CATCH = "first_catch"

    # === MINOR (Zora only, screenshot, no footer) ===
    # Route/Location milestones
    NEW_ROUTE = "new_route"
    NEW_CITY = "new_city"
    NEW_DUNGEON = "new_dungeon"
    DUNGEON_EXIT = "dungeon_exit"

    # Pokemon collection (first catch of each species)
    FIRST_CATCH_SPECIES = "first_catch_species"
    POKEMON_EVOLVED = "pokemon_evolved"  # Non-starter evolutions
    TEAM_FULL = "team_full"
    POKEDEX_MILESTONE = "pokedex_milestone"  # Every 10 entries

    # Battle milestones
    RIVAL_DEFEATED = "rival_defeated"
    ROCKET_DEFEATED = "rocket_defeated"

    # Items/Progress
    HM_OBTAINED = "hm_obtained"
    KEY_ITEM = "key_item"

    # === PROGRESS (Zora only, gallery, with footer - fallback) ===
    CYCLE_CHECKPOINT = "cycle_checkpoint"


# Map achievement types to tiers
ACHIEVEMENT_TIERS: Dict[ZoraAchievementType, ZoraAchievementTier] = {
    # Major achievements
    ZoraAchievementType.STREAM_START: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_BOULDER: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_CASCADE: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_THUNDER: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_RAINBOW: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_SOUL: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_MARSH: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_VOLCANO: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.BADGE_EARTH: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.STARTER_EVOLUTION_1: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.STARTER_EVOLUTION_2: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.LEGENDARY_ARTICUNO: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.LEGENDARY_ZAPDOS: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.LEGENDARY_MOLTRES: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.LEGENDARY_MEWTWO: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.POKEMON_CHAMPION: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.FIRST_POKEMON: ZoraAchievementTier.MAJOR,
    ZoraAchievementType.FIRST_CATCH: ZoraAchievementTier.MAJOR,
    # Minor achievements
    ZoraAchievementType.NEW_ROUTE: ZoraAchievementTier.MINOR,
    ZoraAchievementType.NEW_CITY: ZoraAchievementTier.MINOR,
    ZoraAchievementType.NEW_DUNGEON: ZoraAchievementTier.MINOR,
    ZoraAchievementType.DUNGEON_EXIT: ZoraAchievementTier.MINOR,
    ZoraAchievementType.FIRST_CATCH_SPECIES: ZoraAchievementTier.MINOR,
    ZoraAchievementType.POKEMON_EVOLVED: ZoraAchievementTier.MINOR,
    ZoraAchievementType.TEAM_FULL: ZoraAchievementTier.MINOR,
    ZoraAchievementType.POKEDEX_MILESTONE: ZoraAchievementTier.MINOR,
    ZoraAchievementType.RIVAL_DEFEATED: ZoraAchievementTier.MINOR,
    ZoraAchievementType.ROCKET_DEFEATED: ZoraAchievementTier.MINOR,
    ZoraAchievementType.HM_OBTAINED: ZoraAchievementTier.MINOR,
    ZoraAchievementType.KEY_ITEM: ZoraAchievementTier.MINOR,
    # Progress (fallback)
    ZoraAchievementType.CYCLE_CHECKPOINT: ZoraAchievementTier.PROGRESS,
}


# Location classification for detection
# Maps can be classified as routes, cities, or dungeons
ROUTES = {
    "ROUTE_1",
    "ROUTE_2",
    "ROUTE_3",
    "ROUTE_4",
    "ROUTE_5",
    "ROUTE_6",
    "ROUTE_7",
    "ROUTE_8",
    "ROUTE_9",
    "ROUTE_10",
    "ROUTE_11",
    "ROUTE_12",
    "ROUTE_13",
    "ROUTE_14",
    "ROUTE_15",
    "ROUTE_16",
    "ROUTE_17",
    "ROUTE_18",
    "ROUTE_19",
    "ROUTE_20",
    "ROUTE_21",
    "ROUTE_22",
    "ROUTE_23",
    "ROUTE_24",
    "ROUTE_25",
}

CITIES = {
    "PALLET_TOWN",
    "VIRIDIAN_CITY",
    "PEWTER_CITY",
    "CERULEAN_CITY",
    "VERMILION_CITY",
    "LAVENDER_TOWN",
    "CELADON_CITY",
    "FUCHSIA_CITY",
    "SAFFRON_CITY",
    "CINNABAR_ISLAND",
    "INDIGO_PLATEAU",
}

DUNGEONS = {
    "MT_MOON",
    "ROCK_TUNNEL",
    "POKEMON_TOWER",
    "SILPH_CO",
    "POKEMON_MANSION",
    "SEAFOAM_ISLANDS",
    "VICTORY_ROAD",
    "CERULEAN_CAVE",
    "DIGLETTS_CAVE",
    "VIRIDIAN_FOREST",
    "SS_ANNE",
    "POWER_PLANT",
    "SAFARI_ZONE",
}

# HM names for detection
HM_NAMES = {"CUT", "FLY", "SURF", "STRENGTH", "FLASH"}

# Key items for detection
KEY_ITEMS = {
    "BICYCLE",
    "SILPH_SCOPE",
    "POKE_FLUTE",
    "LIFT_KEY",
    "CARD_KEY",
    "GOLD_TEETH",
    "SECRET_KEY",
    "GOOD_ROD",
    "SUPER_ROD",
    "SS_TICKET",
    "OLD_AMBER",
    "DOME_FOSSIL",
    "HELIX_FOSSIL",
    "TOWN_MAP",
}


@dataclass
class ZoraAchievement:
    """A Zora-specific achievement."""

    achievement_type: ZoraAchievementType
    tier: ZoraAchievementTier
    triggered_at: str  # ISO timestamp
    context: Dict[str, Any] = field(default_factory=dict)
    zora_posted: bool = False
    zora_coin_address: Optional[str] = None
    post_number: Optional[int] = None  # LLP-NNN number

    def get_title(self) -> str:
        """Generate post title based on achievement type and context."""
        prefix = f"LLP-{self.post_number:03d}" if self.post_number else "LLP"

        type_titles = {
            ZoraAchievementType.NEW_ROUTE: f"Exploring {self.context.get('location', 'New Route')}",
            ZoraAchievementType.NEW_CITY: f"Arrived at {self.context.get('location', 'New City')}",
            ZoraAchievementType.NEW_DUNGEON: f"Entering {self.context.get('location', 'Unknown')}",
            ZoraAchievementType.DUNGEON_EXIT: f"Escaped from {self.context.get('location', 'Unknown')}",
            ZoraAchievementType.FIRST_CATCH_SPECIES: f"Caught a {self.context.get('pokemon', 'Pokemon')}!",
            ZoraAchievementType.POKEMON_EVOLVED: f"{self.context.get('pokemon', 'Pokemon')} Evolved!",
            ZoraAchievementType.TEAM_FULL: "Team is Complete!",
            ZoraAchievementType.POKEDEX_MILESTONE: f"Pokedex: {self.context.get('count', 0)} Pokemon",
            ZoraAchievementType.RIVAL_DEFEATED: "Defeated Rival!",
            ZoraAchievementType.ROCKET_DEFEATED: "Team Rocket Defeated!",
            ZoraAchievementType.HM_OBTAINED: f"Obtained {self.context.get('item', 'HM')}!",
            ZoraAchievementType.KEY_ITEM: f"Got {self.context.get('item', 'Key Item')}!",
            ZoraAchievementType.CYCLE_CHECKPOINT: "Journey Progress",
            # Major achievements (these have their own handling)
            ZoraAchievementType.STREAM_START: "Lass Begins Her Journey",
            ZoraAchievementType.BADGE_BOULDER: "Boulder Badge Earned!",
            ZoraAchievementType.BADGE_CASCADE: "Cascade Badge Earned!",
            ZoraAchievementType.BADGE_THUNDER: "Thunder Badge Earned!",
            ZoraAchievementType.BADGE_RAINBOW: "Rainbow Badge Earned!",
            ZoraAchievementType.BADGE_SOUL: "Soul Badge Earned!",
            ZoraAchievementType.BADGE_MARSH: "Marsh Badge Earned!",
            ZoraAchievementType.BADGE_VOLCANO: "Volcano Badge Earned!",
            ZoraAchievementType.BADGE_EARTH: "Earth Badge Earned!",
            ZoraAchievementType.POKEMON_CHAMPION: "Pokemon Champion!",
        }

        title = type_titles.get(
            self.achievement_type, self.achievement_type.value.replace("_", " ").title()
        )
        return f"{prefix}: {title}"

    def should_include_footer(self) -> bool:
        """Check if this achievement should include cross-promotion footer."""
        return self.tier in (ZoraAchievementTier.MAJOR, ZoraAchievementTier.PROGRESS)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "achievement_type": self.achievement_type.value,
            "tier": self.tier.value,
            "triggered_at": self.triggered_at,
            "context": self.context,
            "zora_posted": self.zora_posted,
            "zora_coin_address": self.zora_coin_address,
            "post_number": self.post_number,
        }


class ZoraAchievementTracker:
    """
    Tracks achievements for Zora posting.

    Works alongside the existing AchievementTracker but tracks:
    - Minor achievements (Zora-only)
    - Caught species (for first-catch-per-species)
    - Visited locations (for route/city/dungeon detection)
    - Post counter (LLP-NNN)

    The post counter is queried from Zora API on startup.
    """

    def __init__(
        self,
        storage_path: str = "data/zora_achievements.json",
        fallback_cycles: int = 60,
        min_post_interval: int = 300,  # 5 minutes minimum between posts
    ):
        """
        Initialize the Zora achievement tracker.

        Args:
            storage_path: Path to persist Zora achievement state
            fallback_cycles: Cycles without achievements before checkpoint post
            min_post_interval: Minimum seconds between Zora posts
        """
        self.storage_path = storage_path
        self.fallback_cycles = fallback_cycles
        self.min_post_interval = min_post_interval

        # Achievement tracking
        self.triggered: Dict[str, ZoraAchievement] = {}
        self._pending_achievement: Optional[ZoraAchievement] = None

        # Species catch tracking (derived from Pokedex)
        self._caught_species: Set[str] = set()

        # Location tracking
        self._visited_routes: Set[str] = set()
        self._visited_cities: Set[str] = set()
        self._visited_dungeons: Set[str] = set()
        self._current_location: str = ""
        self._prev_location: str = ""

        # Party tracking
        self._prev_party: List[Dict] = []
        self._prev_party_size: int = 0

        # Pokedex tracking
        self._prev_pokedex_count: int = 0

        # Post counter (will be set from Zora API)
        self._post_counter: int = 0

        # Timing
        self._last_post_time: float = 0
        self._cycles_since_last_post: int = 0

        # Ensure data directory exists
        Path(os.path.dirname(storage_path)).mkdir(parents=True, exist_ok=True)

        self._load()
        log.info(
            f"Zora achievement tracker initialized: "
            f"{len(self.triggered)} achievements, "
            f"post counter at {self._post_counter}"
        )

    def set_post_counter(self, count: int):
        """
        Set the post counter (called after querying Zora API on startup).

        Args:
            count: Current post count from Zora
        """
        self._post_counter = count
        self._save()
        log.info(f"Zora post counter set to {count}")

    def get_next_post_number(self) -> int:
        """Get the next post number (increments counter)."""
        self._post_counter += 1
        self._save()
        return self._post_counter

    def _load(self) -> None:
        """Load state from disk."""
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            # Load triggered achievements
            for key, value in data.get("triggered", {}).items():
                try:
                    achievement_type = ZoraAchievementType(value["achievement_type"])
                    tier = ZoraAchievementTier(value["tier"])
                    self.triggered[key] = ZoraAchievement(
                        achievement_type=achievement_type,
                        tier=tier,
                        triggered_at=value["triggered_at"],
                        context=value.get("context", {}),
                        zora_posted=value.get("zora_posted", False),
                        zora_coin_address=value.get("zora_coin_address"),
                        post_number=value.get("post_number"),
                    )
                except (KeyError, ValueError) as e:
                    log.warning(f"Failed to load Zora achievement {key}: {e}")

            # Load tracking state
            self._caught_species = set(data.get("caught_species", []))
            self._visited_routes = set(data.get("visited_routes", []))
            self._visited_cities = set(data.get("visited_cities", []))
            self._visited_dungeons = set(data.get("visited_dungeons", []))
            self._post_counter = data.get("post_counter", 0)
            self._prev_pokedex_count = data.get("prev_pokedex_count", 0)
            self._cycles_since_last_post = data.get("cycles_since_last_post", 0)

        except Exception as e:
            log.error(f"Failed to load Zora achievements: {e}")

    def _save(self) -> None:
        """Save state to disk."""
        try:
            data = {
                "triggered": {
                    key: ach.to_dict() for key, ach in self.triggered.items()
                },
                "caught_species": list(self._caught_species),
                "visited_routes": list(self._visited_routes),
                "visited_cities": list(self._visited_cities),
                "visited_dungeons": list(self._visited_dungeons),
                "post_counter": self._post_counter,
                "prev_pokedex_count": self._prev_pokedex_count,
                "cycles_since_last_post": self._cycles_since_last_post,
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            log.error(f"Failed to save Zora achievements: {e}")

    def trigger(
        self,
        achievement_type: ZoraAchievementType,
        context: Optional[Dict[str, Any]] = None,
        unique_key: Optional[str] = None,
    ) -> Optional[ZoraAchievement]:
        """
        Trigger a Zora achievement.

        Args:
            achievement_type: The type of achievement
            context: Additional context for the achievement
            unique_key: Optional unique key for achievements that can trigger multiple times
                        (e.g., "first_catch_species_PIDGEY")

        Returns:
            ZoraAchievement if newly triggered, None if already exists
        """
        # Generate key for this achievement
        key = unique_key or achievement_type.value

        if key in self.triggered:
            log.debug(f"Zora achievement already triggered: {key}")
            return None

        tier = ACHIEVEMENT_TIERS.get(achievement_type, ZoraAchievementTier.MINOR)
        post_number = self.get_next_post_number()

        achievement = ZoraAchievement(
            achievement_type=achievement_type,
            tier=tier,
            triggered_at=datetime.now().isoformat(),
            context=context or {},
            post_number=post_number,
        )

        self.triggered[key] = achievement
        self._pending_achievement = achievement
        self._cycles_since_last_post = 0
        self._save()

        log.info(
            f"Zora achievement triggered: {achievement.get_title()} "
            f"(tier: {tier.value})"
        )
        return achievement

    def get_pending_achievement(self) -> Optional[ZoraAchievement]:
        """Get the pending achievement for Zora posting."""
        return self._pending_achievement

    def clear_pending_achievement(self) -> None:
        """Clear the pending achievement after posting."""
        self._pending_achievement = None

    def mark_posted(
        self,
        key: str,
        coin_address: Optional[str] = None,
    ) -> None:
        """Mark an achievement as posted to Zora."""
        if key in self.triggered:
            self.triggered[key].zora_posted = True
            self.triggered[key].zora_coin_address = coin_address
            self._save()

    def check_for_achievements(
        self,
        current_party: List[Dict],
        current_map: str,
        pokedex_caught: int = 0,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[ZoraAchievement]:
        """
        Check current game state for new Zora achievements.

        This checks for MINOR achievements only. MAJOR achievements
        are handled by the main AchievementTracker and forwarded here.

        Args:
            current_party: Current party Pokemon list
            current_map: Current map/location name
            pokedex_caught: Number of Pokemon caught (from Pokedex)
            game_state: Full game state dict

        Returns:
            Newly triggered ZoraAchievement, or None
        """
        self._cycles_since_last_post += 1
        achievement = None

        # Normalize map name
        map_normalized = self._normalize_location(current_map)

        # Check location changes (route/city/dungeon)
        achievement = achievement or self._check_location_change(map_normalized)

        # Check for new Pokemon species in party
        achievement = achievement or self._check_new_species(current_party)

        # Check team size changes
        achievement = achievement or self._check_team_changes(current_party)

        # Check Pokedex milestones
        achievement = achievement or self._check_pokedex_milestone(pokedex_caught)

        # Check for fallback checkpoint
        if not achievement:
            achievement = self._check_fallback_checkpoint()

        # Update previous state
        self._prev_location = map_normalized
        self._prev_party = [
            p.copy() if isinstance(p, dict) else {} for p in current_party
        ]
        self._prev_party_size = len(current_party)
        self._prev_pokedex_count = pokedex_caught

        return achievement

    def _normalize_location(self, location: str) -> str:
        """Normalize location name for comparison."""
        if not location:
            return ""
        return location.upper().replace(" ", "_").replace("-", "_")

    def _classify_location(self, location: str) -> Optional[str]:
        """
        Classify a location as route, city, or dungeon.

        Returns:
            "route", "city", "dungeon", or None
        """
        if not location:
            return None

        # Check exact matches first
        if location in ROUTES:
            return "route"
        if location in CITIES:
            return "city"
        if location in DUNGEONS:
            return "dungeon"

        # Check partial matches
        for route in ROUTES:
            if route in location or location in route:
                return "route"
        for city in CITIES:
            if city in location or location in city:
                return "city"
        for dungeon in DUNGEONS:
            if dungeon in location or location in dungeon:
                return "dungeon"

        return None

    def _check_location_change(
        self, current_location: str
    ) -> Optional[ZoraAchievement]:
        """Check for new location achievements."""
        if not current_location or current_location == self._prev_location:
            return None

        location_type = self._classify_location(current_location)

        if location_type == "route" and current_location not in self._visited_routes:
            self._visited_routes.add(current_location)
            return self.trigger(
                ZoraAchievementType.NEW_ROUTE,
                context={"location": current_location.replace("_", " ").title()},
                unique_key=f"new_route_{current_location}",
            )

        if location_type == "city" and current_location not in self._visited_cities:
            self._visited_cities.add(current_location)
            return self.trigger(
                ZoraAchievementType.NEW_CITY,
                context={"location": current_location.replace("_", " ").title()},
                unique_key=f"new_city_{current_location}",
            )

        if location_type == "dungeon":
            # Check if entering or exiting dungeon
            prev_type = self._classify_location(self._prev_location)

            if current_location not in self._visited_dungeons:
                self._visited_dungeons.add(current_location)
                return self.trigger(
                    ZoraAchievementType.NEW_DUNGEON,
                    context={"location": current_location.replace("_", " ").title()},
                    unique_key=f"new_dungeon_{current_location}",
                )
            elif prev_type == "dungeon" and location_type != "dungeon":
                # Just exited a dungeon
                return self.trigger(
                    ZoraAchievementType.DUNGEON_EXIT,
                    context={"location": self._prev_location.replace("_", " ").title()},
                    unique_key=f"dungeon_exit_{self._prev_location}_{self._cycles_since_last_post}",
                )

        return None

    def _check_new_species(
        self, current_party: List[Dict]
    ) -> Optional[ZoraAchievement]:
        """Check for first catch of a new species."""
        current_species = set()
        for pokemon in current_party:
            if pokemon:
                species = pokemon.get("name", "").upper()
                if species:
                    current_species.add(species)

        # Find newly caught species
        new_species = current_species - self._caught_species

        for species in new_species:
            self._caught_species.add(species)

            # Skip if this is likely the starter (first Pokemon)
            if len(self._caught_species) == 1:
                continue

            # Skip second Pokemon (handled by FIRST_CATCH)
            if len(self._caught_species) == 2:
                continue

            # Trigger first catch for this species
            return self.trigger(
                ZoraAchievementType.FIRST_CATCH_SPECIES,
                context={
                    "pokemon": species.title(),
                    "pokedex_count": len(self._caught_species),
                },
                unique_key=f"first_catch_species_{species}",
            )

        return None

    def _check_team_changes(
        self, current_party: List[Dict]
    ) -> Optional[ZoraAchievement]:
        """Check for team size changes."""
        current_size = len(current_party)

        # Check for full team (6 Pokemon)
        if current_size == 6 and self._prev_party_size < 6:
            key = "team_full"
            if key not in self.triggered:
                pokemon_names = [
                    p.get("name", "Unknown").title() for p in current_party if p
                ]
                return self.trigger(
                    ZoraAchievementType.TEAM_FULL,
                    context={"team": pokemon_names},
                    unique_key=key,
                )

        # Check for evolutions (non-starter)
        for i, pokemon in enumerate(current_party):
            if i >= len(self._prev_party):
                continue

            prev_pokemon = self._prev_party[i]
            current_species = pokemon.get("name", "").upper() if pokemon else ""
            prev_species = prev_pokemon.get("name", "").upper() if prev_pokemon else ""

            if current_species and prev_species and current_species != prev_species:
                # Evolution detected (same slot, different species)
                key = f"evolution_{current_species}"
                if key not in self.triggered:
                    return self.trigger(
                        ZoraAchievementType.POKEMON_EVOLVED,
                        context={
                            "pokemon": current_species.title(),
                            "evolved_from": prev_species.title(),
                        },
                        unique_key=key,
                    )

        return None

    def _check_pokedex_milestone(
        self, pokedex_caught: int
    ) -> Optional[ZoraAchievement]:
        """Check for Pokedex milestone (every 10 Pokemon)."""
        if pokedex_caught <= 0:
            return None

        # Check if we crossed a 10-Pokemon milestone
        prev_milestone = (self._prev_pokedex_count // 10) * 10
        current_milestone = (pokedex_caught // 10) * 10

        if current_milestone > prev_milestone and current_milestone > 0:
            key = f"pokedex_milestone_{current_milestone}"
            if key not in self.triggered:
                return self.trigger(
                    ZoraAchievementType.POKEDEX_MILESTONE,
                    context={"count": current_milestone},
                    unique_key=key,
                )

        return None

    def _check_fallback_checkpoint(self) -> Optional[ZoraAchievement]:
        """Check if we should trigger a fallback checkpoint post."""
        if self._cycles_since_last_post >= self.fallback_cycles:
            key = f"checkpoint_{self._post_counter + 1}"
            return self.trigger(
                ZoraAchievementType.CYCLE_CHECKPOINT,
                context={
                    "cycles": self._cycles_since_last_post,
                    "is_fallback": True,
                },
                unique_key=key,
            )
        return None

    def trigger_from_major_achievement(
        self,
        achievement_type_value: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[ZoraAchievement]:
        """
        Trigger a Zora achievement from a major achievement (from AchievementTracker).

        This is called when the main AchievementTracker triggers a major achievement
        that should also be posted to Zora.

        Args:
            achievement_type_value: The achievement type value string
            context: Achievement context

        Returns:
            ZoraAchievement if triggered
        """
        try:
            zora_type = ZoraAchievementType(achievement_type_value)
        except ValueError:
            log.warning(f"Unknown achievement type for Zora: {achievement_type_value}")
            return None

        return self.trigger(zora_type, context=context)

    def get_stats(self) -> dict:
        """Get tracker statistics."""
        major_count = sum(
            1 for a in self.triggered.values() if a.tier == ZoraAchievementTier.MAJOR
        )
        minor_count = sum(
            1 for a in self.triggered.values() if a.tier == ZoraAchievementTier.MINOR
        )
        progress_count = sum(
            1 for a in self.triggered.values() if a.tier == ZoraAchievementTier.PROGRESS
        )

        return {
            "total_achievements": len(self.triggered),
            "major_achievements": major_count,
            "minor_achievements": minor_count,
            "progress_checkpoints": progress_count,
            "post_counter": self._post_counter,
            "caught_species": len(self._caught_species),
            "visited_routes": len(self._visited_routes),
            "visited_cities": len(self._visited_cities),
            "visited_dungeons": len(self._visited_dungeons),
            "cycles_since_last_post": self._cycles_since_last_post,
        }


# Singleton instance
_zora_tracker: Optional[ZoraAchievementTracker] = None


def get_zora_achievement_tracker(
    storage_path: str = "data/zora_achievements.json",
    fallback_cycles: int = 60,
) -> ZoraAchievementTracker:
    """Get or create the singleton Zora achievement tracker."""
    global _zora_tracker
    if _zora_tracker is None:
        _zora_tracker = ZoraAchievementTracker(
            storage_path=storage_path,
            fallback_cycles=fallback_cycles,
        )
    return _zora_tracker
