"""
Achievement Tracker for Pokemon LLM Agent.

Tracks game achievements/milestones and triggers tweet generation with
customized image prompts for each achievement type.

Only triggers once per achievement type per run.
"""

import json
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Set, Any, cast
from pathlib import Path

log = logging.getLogger("achievement_tracker")


class AchievementType(Enum):
    """All trackable achievements in the game."""

    # Stream events
    STREAM_START = "stream_start"

    # Early game milestones
    FIRST_POKEMON = "first_pokemon"  # Getting starter from Oak
    ROUTE_1_FLOWER = "route_1_flower"  # Scripted photo moment
    FIRST_CATCH = "first_catch"  # First Pokemon caught with Pokeball
    VIRIDIAN_FOREST_BREAK = "viridian_forest_break"  # Scripted photo moment
    TEAM_ROCKET_FIRST = "team_rocket_first"  # First encounter with Team Rocket

    # Evolution milestones
    STARTER_EVOLUTION_1 = (
        "starter_evolution_1"  # First evolution (e.g., Charmander -> Charmeleon)
    )
    STARTER_EVOLUTION_2 = (
        "starter_evolution_2"  # Final evolution (e.g., Charmeleon -> Charizard)
    )

    # Gym badges
    BADGE_BOULDER = "badge_boulder"  # Brock
    BADGE_CASCADE = "badge_cascade"  # Misty
    BADGE_THUNDER = "badge_thunder"  # Lt. Surge
    BADGE_RAINBOW = "badge_rainbow"  # Erika
    BADGE_SOUL = "badge_soul"  # Koga
    BADGE_MARSH = "badge_marsh"  # Sabrina
    BADGE_VOLCANO = "badge_volcano"  # Blaine
    BADGE_EARTH = "badge_earth"  # Giovanni

    # Scripted location moments
    SS_ANNE_DECK = "ss_anne_deck"  # Looking out from SS Anne bow
    POKEMON_TOWER_SPOOKED = "pokemon_tower_spooked"  # Scared in Pokemon Tower
    GAME_CORNER_SLOTS = "game_corner_slots"  # Playing slots in Game Corner
    FIGHTING_DOJO = "fighting_dojo"  # Training at Fighting Dojo
    SAFARI_ZONE_EXPLORER = "safari_zone_explorer"  # Exploring Safari Zone

    # Scenic/Nature photo moments
    CERULEAN_CAPE = "cerulean_cape"  # Ocean view near Bill's house
    MT_MOON_EXIT = "mt_moon_exit"  # Relief after exiting Mt. Moon
    ROCK_TUNNEL_EXIT = "rock_tunnel_exit"  # Daylight after Rock Tunnel
    CYCLING_ROAD = "cycling_road"  # Cruising down Cycling Road
    SEAFOAM_ISLANDS = "seafoam_islands"  # Icy cave adventure
    ROUTE_12_FISHING = "route_12_fishing"  # Fishing by the pier

    # Milestone photo moments
    PEWTER_GYM_ENTRANCE = "pewter_gym_entrance"  # First gym entrance
    INDIGO_PLATEAU = "indigo_plateau"  # Arriving at Pokemon League
    DAYCARE_VISIT = "daycare_visit"  # First visit to the Daycare

    # Legendary captures
    LEGENDARY_ARTICUNO = "legendary_articuno"
    LEGENDARY_ZAPDOS = "legendary_zapdos"
    LEGENDARY_MOLTRES = "legendary_moltres"
    LEGENDARY_MEWTWO = "legendary_mewtwo"

    # Endgame
    POKEMON_CHAMPION = "pokemon_champion"  # Defeated Elite 4 and Champion


# Starter evolution chains and legendary data (loaded from YAML)
STARTER_EVOLUTIONS: Dict[str, Any] = {}
LEGENDARY_POKEMON: Set[str] = set()


def _load_game_constants():
    """Load game constants from YAML."""
    global STARTER_EVOLUTIONS, LEGENDARY_POKEMON
    data_path = Path(__file__).parent.parent / "data" / "game_data.yaml"
    if not data_path.exists():
        log.warning(f"Game data YAML not found: {data_path}")
        return

    try:
        import yaml

        with open(data_path, "r") as f:
            data = yaml.safe_load(f)

        STARTER_EVOLUTIONS = data.get("pokemon", {}).get("starter_evolutions", {})
        LEGENDARY_POKEMON = set(data.get("pokemon", {}).get("legendaries", []))
        log.info("Loaded game constants from YAML")
    except Exception as e:
        log.error(f"Failed to load game constants YAML: {e}")


# Load on module import
_load_game_constants()

# Badge name to achievement type mapping
BADGE_TO_ACHIEVEMENT = {
    "Boulder": AchievementType.BADGE_BOULDER,
    "Cascade": AchievementType.BADGE_CASCADE,
    "Thunder": AchievementType.BADGE_THUNDER,
    "Rainbow": AchievementType.BADGE_RAINBOW,
    "Soul": AchievementType.BADGE_SOUL,
    "Marsh": AchievementType.BADGE_MARSH,
    "Volcano": AchievementType.BADGE_VOLCANO,
    "Earth": AchievementType.BADGE_EARTH,
}

# Legendary to achievement type mapping
LEGENDARY_TO_ACHIEVEMENT = {
    "ARTICUNO": AchievementType.LEGENDARY_ARTICUNO,
    "ZAPDOS": AchievementType.LEGENDARY_ZAPDOS,
    "MOLTRES": AchievementType.LEGENDARY_MOLTRES,
    "MEWTWO": AchievementType.LEGENDARY_MEWTWO,
}


@dataclass
class AchievementImagePrompt:
    """
    Image generation prompts for an achievement.

    Prompts are composed from 4 structured fields that are combined at runtime:
    - setting: background, location, camera angle
    - mood_expression: facial expression, emotional state
    - action: pose, what she's doing
    - extras: lighting, effects, additional elements

    The positive_prompt property combines these fields into a single string.
    """

    # Structured prompt components
    setting: str = ""  # background, location, camera angle
    mood_expression: str = ""  # facial expression, emotional state
    action: str = ""  # pose, what she's doing
    extras: str = ""  # lighting, effects, additional elements

    # Compose positive prompt from structured fields
    @property
    def positive_prompt(self) -> str:
        """Combine structured fields into a single prompt string."""
        parts = [
            self.setting,
            self.mood_expression,
            self.action,
            self.extras,
        ]
        # Filter empty parts and join with commas
        return ", ".join(p.strip() for p in parts if p and p.strip())


# YAML-based prompt loading
_PROMPTS_YAML_PATH = Path(__file__).parent.parent / "data" / "image_prompts.yaml"
_yaml_prompts_cache: Optional[Dict[str, Any]] = None


def _load_yaml_prompts() -> Dict[str, Any]:
    """Load prompts from YAML file with caching."""
    global _yaml_prompts_cache

    if _yaml_prompts_cache is not None:
        return _yaml_prompts_cache

    if not _PROMPTS_YAML_PATH.exists():
        log.warning(f"Image prompts YAML not found: {_PROMPTS_YAML_PATH}")
        return {}

    try:
        import yaml

        with open(_PROMPTS_YAML_PATH, "r") as f:
            loaded_data = yaml.safe_load(f)

        if loaded_data is None:
            log.warning("Image prompts YAML is empty")
            return {}

        _yaml_prompts_cache = cast(Dict[str, Any], loaded_data)

        # Safe access to checkpoints
        checkpoints = _yaml_prompts_cache.get("checkpoints", {})
        checkpoint_count = len(checkpoints) if checkpoints else 0
        log.info(f"Loaded image prompts from YAML: {checkpoint_count} checkpoints")
        return _yaml_prompts_cache
    except ImportError:
        log.warning("PyYAML not installed, using fallback prompts")
        return {}
    except Exception as e:
        log.error(f"Failed to load image prompts YAML: {e}")
        return {}


def _build_prompts_from_yaml() -> Dict[AchievementType, AchievementImagePrompt]:
    """Build ACHIEVEMENT_IMAGE_PROMPTS dict from YAML data."""
    yaml_data = _load_yaml_prompts()
    checkpoints = yaml_data.get("checkpoints", {})

    prompts: Dict[AchievementType, AchievementImagePrompt] = {}

    for key, data in checkpoints.items():
        try:
            # Convert YAML key to AchievementType enum
            achievement_type = AchievementType(key)

            prompts[achievement_type] = AchievementImagePrompt(
                setting=data.get("setting", ""),
                mood_expression=data.get("mood_expression", ""),
                action=data.get("action", ""),
                extras=data.get("extras", ""),
            )
        except ValueError:
            log.warning(f"Unknown achievement type in YAML: {key}")

    return prompts


def get_achievement_image_prompts() -> Dict[AchievementType, AchievementImagePrompt]:
    """Get achievement image prompts, preferring YAML source."""
    yaml_prompts = _build_prompts_from_yaml()
    if yaml_prompts:
        return yaml_prompts
    return _FALLBACK_ACHIEVEMENT_IMAGE_PROMPTS


# Fallback prompts (used if YAML not available)
_FALLBACK_ACHIEVEMENT_IMAGE_PROMPTS: Dict[AchievementType, AchievementImagePrompt] = {
    AchievementType.STREAM_START: AchievementImagePrompt(
        action="excited pose, waving at viewer, sparkles, happy expression, energetic, ready for adventure",
    ),
    AchievementType.FIRST_POKEMON: AchievementImagePrompt(
        setting="professor oak's lab background",
        mood_expression="gentle smile, emotional, happy tears",
        action="holding pokeball lovingly",
        extras="warm lighting, first pokemon moment",
    ),
    AchievementType.FIRST_CATCH: AchievementImagePrompt(
        mood_expression="excited expression",
        action="triumphant pose, holding pokeball up victoriously",
        extras="celebration, first catch success, sparkles around pokeball",
    ),
    AchievementType.POKEMON_CHAMPION: AchievementImagePrompt(
        setting="hall of fame, golden lighting, epic finale",
        mood_expression="tears of joy, ultimate triumph",
        action="champion pose, all pokemon team behind her",
        extras="trophy, confetti, championship victory, legendary achievement",
    ),
}

# Main export - dynamically loads from YAML
ACHIEVEMENT_IMAGE_PROMPTS: Dict[AchievementType, AchievementImagePrompt] = (
    get_achievement_image_prompts()
)


def get_dynamic_prompt_template() -> str:
    """
    Get the dynamic prompt template for LLM-generated image prompts.

    Used for CYCLE_CHECKPOINT (progress/fallback) posts where the LLM
    generates prompt components based on the current game state.

    Returns:
        The system prompt template with placeholders for game state.
    """
    yaml_data = _load_yaml_prompts()
    dynamic = yaml_data.get("dynamic_template", {})
    return dynamic.get("system_prompt", _DEFAULT_DYNAMIC_TEMPLATE)


# Default template if YAML not available
_DEFAULT_DYNAMIC_TEMPLATE = """You are generating image prompt components for Lass, a Pokemon trainer taking a 
social media photo during her Pokemon Red adventure.

Based on the current game state, generate creative and varied prompt components.
Make each photo unique and fitting for the location/situation.

Current game state:
- Location: {location}
- Map Type: {map_type}
- Party Pokemon: {party}
- Badges: {badges}/8
- Recent events: {recent_events}

Generate a JSON object with these 4 fields:
- setting: background, location details, camera angle (be specific to location)
- mood_expression: facial expression and emotional state (vary based on situation)
- action: pose and what Lass is doing (make it natural for the location)
- extras: lighting, effects, additional scene elements

Keep each field concise (under 100 characters). Be creative and avoid repetition.
"""


def build_dynamic_prompt_context(
    location: str = "",
    map_type: str = "",
    party: Optional[List[str]] = None,
    badges: int = 0,
    recent_events: str = "",
) -> str:
    """
    Build the dynamic prompt with game state filled in.

    Args:
        location: Current map/location name
        map_type: Type of location (city, route, dungeon, etc.)
        party: List of Pokemon names in party
        badges: Number of badges earned
        recent_events: Description of recent game events

    Returns:
        Formatted prompt string ready to send to LLM.
    """
    template = get_dynamic_prompt_template()
    party_str = ", ".join(party) if party else "None"

    return template.format(
        location=location or "Unknown",
        map_type=map_type or "unknown",
        party=party_str,
        badges=badges,
        recent_events=recent_events or "Continuing the adventure",
    )


def parse_dynamic_prompt_response(response: str) -> Optional[AchievementImagePrompt]:
    """
    Parse LLM response into an AchievementImagePrompt.

    Expects JSON with: setting, mood_expression, action, extras

    Args:
        response: Raw LLM response string

    Returns:
        AchievementImagePrompt or None if parsing fails.
    """
    import json
    import re

    try:
        # Try to extract JSON from response (may have extra text)
        json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if not json_match:
            log.warning("No JSON found in dynamic prompt response")
            return None

        data = json.loads(json_match.group())

        return AchievementImagePrompt(
            setting=data.get("setting", ""),
            mood_expression=data.get("mood_expression", ""),
            action=data.get("action", ""),
            extras=data.get("extras", ""),
        )
    except Exception as e:
        log.error(f"Error parsing dynamic prompt response: {e}")
        return None


@dataclass
class Achievement:
    """A triggered achievement."""

    achievement_type: AchievementType
    triggered_at: str  # ISO timestamp
    context: Dict[str, Any] = field(default_factory=dict)  # Pokemon name, badge, etc.
    tweet_posted: bool = False
    tweet_url: Optional[str] = None


class AchievementTracker:
    """
    Tracks game achievements and triggers tweet generation.

    Persists state to disk to survive restarts.
    Only triggers each achievement type once per run.
    """

    def __init__(
        self,
        storage_path: str = "data/achievements.json",
        reset_on_start: bool = False,
    ):
        """
        Initialize the achievement tracker.

        Args:
            storage_path: Path to persist achievement state
            reset_on_start: If True, clear all achievements on initialization
        """
        self.storage_path = storage_path
        self.triggered: Dict[
            str, Achievement
        ] = {}  # achievement_type.value -> Achievement
        self._pending_achievement: Optional[Achievement] = None

        # Track previous state for change detection
        self._prev_party: List[Dict] = []
        self._prev_badges: List[str] = []
        self._starter_species: Optional[str] = None  # Track which starter was chosen
        self._first_pokemon_count: int = 0  # Track if first catch already happened

        # Ensure data directory exists
        Path(os.path.dirname(storage_path)).mkdir(parents=True, exist_ok=True)

        if reset_on_start:
            self._save()
            log.info("Achievement tracker: Fresh start (all achievements reset)")
        else:
            self._load()
            log.info(f"Achievement tracker: Loaded {len(self.triggered)} achievements")

    def _load(self) -> None:
        """Load achievements from disk."""
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            for key, value in data.get("triggered", {}).items():
                try:
                    achievement_type = AchievementType(value["achievement_type"])
                    self.triggered[key] = Achievement(
                        achievement_type=achievement_type,
                        triggered_at=value["triggered_at"],
                        context=value.get("context", {}),
                        tweet_posted=value.get("tweet_posted", False),
                        tweet_url=value.get("tweet_url"),
                    )
                except (KeyError, ValueError) as e:
                    log.warning(f"Failed to load achievement {key}: {e}")

            # Restore tracking state
            self._starter_species = data.get("starter_species")
            self._first_pokemon_count = data.get("first_pokemon_count", 0)

        except Exception as e:
            log.error(f"Failed to load achievements: {e}")

    def _save(self) -> None:
        """Save achievements to disk."""
        try:
            data = {
                "triggered": {
                    key: {
                        "achievement_type": ach.achievement_type.value,
                        "triggered_at": ach.triggered_at,
                        "context": ach.context,
                        "tweet_posted": ach.tweet_posted,
                        "tweet_url": ach.tweet_url,
                    }
                    for key, ach in self.triggered.items()
                },
                "starter_species": self._starter_species,
                "first_pokemon_count": self._first_pokemon_count,
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            log.error(f"Failed to save achievements: {e}")

    def is_triggered(self, achievement_type: AchievementType) -> bool:
        """Check if an achievement has already been triggered."""
        return achievement_type.value in self.triggered

    def trigger(
        self,
        achievement_type: AchievementType,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Achievement]:
        """
        Trigger an achievement if not already triggered.

        Args:
            achievement_type: The achievement to trigger
            context: Additional context (Pokemon name, badge, etc.)

        Returns:
            The Achievement if newly triggered, None if already triggered
        """
        if self.is_triggered(achievement_type):
            log.debug(f"Achievement already triggered: {achievement_type.value}")
            return None

        achievement = Achievement(
            achievement_type=achievement_type,
            triggered_at=datetime.now().isoformat(),
            context=context or {},
        )

        self.triggered[achievement_type.value] = achievement
        self._pending_achievement = achievement
        self._save()

        log.info(f"Achievement triggered: {achievement_type.value}")
        return achievement

    def get_pending_achievement(self) -> Optional[Achievement]:
        """Get the pending achievement for tweet generation."""
        return self._pending_achievement

    def clear_pending_achievement(self) -> None:
        """Clear the pending achievement after tweet generation."""
        self._pending_achievement = None

    def mark_tweet_posted(
        self, achievement_type: AchievementType, tweet_url: Optional[str] = None
    ) -> None:
        """Mark an achievement's tweet as posted."""
        if achievement_type.value in self.triggered:
            self.triggered[achievement_type.value].tweet_posted = True
            self.triggered[achievement_type.value].tweet_url = tweet_url
            self._save()

    def get_image_prompt(
        self, achievement_type: AchievementType
    ) -> AchievementImagePrompt:
        """Get the image prompt for an achievement type."""
        return ACHIEVEMENT_IMAGE_PROMPTS.get(
            achievement_type,
            AchievementImagePrompt(),  # Empty prompt as fallback
        )

    # =========================================================================
    # Achievement Detection Methods
    # =========================================================================

    def check_for_achievements(
        self,
        current_party: List[Dict],
        current_badges: List[str],
        current_map: str,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[Achievement]:
        """
        Check current game state for new achievements.

        Should be called each game cycle.

        Returns:
            Newly triggered Achievement, or None
        """
        achievement = None

        # Check badge achievements
        achievement = achievement or self._check_badge_achievements(current_badges)

        # Check first Pokemon (starter from Oak)
        achievement = achievement or self._check_first_pokemon(current_party)

        # Check first catch (second Pokemon)
        achievement = achievement or self._check_first_catch(current_party)

        # Check evolution achievements
        achievement = achievement or self._check_evolution(current_party)

        # Check legendary catches
        achievement = achievement or self._check_legendary_catch(current_party)

        # Check champion victory
        achievement = achievement or self._check_champion(current_map, game_state)

        # Update previous state for next cycle
        self._prev_party = [
            p.copy() if isinstance(p, dict) else {} for p in current_party
        ]
        self._prev_badges = list(current_badges) if current_badges else []

        return achievement

    def _check_badge_achievements(
        self, current_badges: List[str]
    ) -> Optional[Achievement]:
        """Check for new badge achievements."""
        if not current_badges:
            return None

        prev_badge_set = set(self._prev_badges) if self._prev_badges else set()
        current_badge_set = set(current_badges)

        new_badges = current_badge_set - prev_badge_set

        for badge_name in new_badges:
            achievement_type = BADGE_TO_ACHIEVEMENT.get(badge_name)
            if achievement_type and not self.is_triggered(achievement_type):
                return self.trigger(
                    achievement_type,
                    context={
                        "badge_name": badge_name,
                        "total_badges": len(current_badges),
                    },
                )

        return None

    def _check_first_pokemon(self, current_party: List[Dict]) -> Optional[Achievement]:
        """Check if player just got their first Pokemon (starter)."""
        if self.is_triggered(AchievementType.FIRST_POKEMON):
            return None

        prev_count = len(self._prev_party)
        current_count = len(current_party)

        # First Pokemon obtained
        if prev_count == 0 and current_count > 0:
            first_pokemon = current_party[0]
            species = first_pokemon.get("name", "").upper()

            # Track starter species for evolution detection
            if species in STARTER_EVOLUTIONS:
                self._starter_species = species
                self._first_pokemon_count = 1

            return self.trigger(
                AchievementType.FIRST_POKEMON,
                context={
                    "pokemon": species,
                    "nickname": first_pokemon.get("nickname", ""),
                },
            )

        return None

    def _check_first_catch(self, current_party: List[Dict]) -> Optional[Achievement]:
        """Check if player caught their first wild Pokemon."""
        if self.is_triggered(AchievementType.FIRST_CATCH):
            return None

        prev_count = len(self._prev_party)
        current_count = len(current_party)

        # Second Pokemon obtained (first catch after starter)
        if prev_count == 1 and current_count == 2:
            caught_pokemon = current_party[1]
            species = caught_pokemon.get("name", "")

            return self.trigger(
                AchievementType.FIRST_CATCH,
                context={
                    "pokemon": species,
                    "nickname": caught_pokemon.get("nickname", ""),
                },
            )

        return None

    def _check_evolution(self, current_party: List[Dict]) -> Optional[Achievement]:
        """Check for starter evolution."""
        if not self._starter_species:
            return None

        # Find starter in current party by checking evolution line
        starter_line = STARTER_EVOLUTIONS.get(self._starter_species, {}).get("line")
        if not starter_line:
            return None

        for pokemon in current_party:
            species = pokemon.get("name", "").upper()
            evo_info = STARTER_EVOLUTIONS.get(species)

            if not evo_info or evo_info.get("line") != starter_line:
                continue

            # Check for first evolution (stage 2)
            if evo_info.get("stage") == 2 and not self.is_triggered(
                AchievementType.STARTER_EVOLUTION_1
            ):
                return self.trigger(
                    AchievementType.STARTER_EVOLUTION_1,
                    context={
                        "pokemon": species,
                        "evolved_from": self._starter_species,
                    },
                )

            # Check for final evolution (stage 3)
            if evo_info.get("stage") == 3 and not self.is_triggered(
                AchievementType.STARTER_EVOLUTION_2
            ):
                return self.trigger(
                    AchievementType.STARTER_EVOLUTION_2,
                    context={
                        "pokemon": species,
                        "starter": self._starter_species,
                    },
                )

        return None

    def _check_legendary_catch(
        self, current_party: List[Dict]
    ) -> Optional[Achievement]:
        """Check for legendary Pokemon catches."""
        prev_species = {p.get("name", "").upper() for p in self._prev_party if p}
        current_species = {p.get("name", "").upper() for p in current_party if p}

        new_pokemon = current_species - prev_species

        for species in new_pokemon:
            if species in LEGENDARY_POKEMON:
                achievement_type = LEGENDARY_TO_ACHIEVEMENT.get(species)
                if achievement_type and not self.is_triggered(achievement_type):
                    return self.trigger(
                        achievement_type,
                        context={"pokemon": species},
                    )

        return None

    def _check_champion(
        self, current_map: str, game_state: Optional[Dict[str, Any]] = None
    ) -> Optional[Achievement]:
        """Check for Pokemon Champion victory."""
        if self.is_triggered(AchievementType.POKEMON_CHAMPION):
            return None

        # Detect entering Hall of Fame
        map_upper = current_map.upper() if current_map else ""
        if "HALL_OF_FAME" in map_upper or "HALL OF FAME" in map_upper:
            return self.trigger(
                AchievementType.POKEMON_CHAMPION,
                context={"location": current_map},
            )

        return None

    def trigger_scripted_photo(
        self, photo_type: AchievementType
    ) -> Optional[Achievement]:
        """
        Trigger a scripted photo moment.

        Called by ScenarioManager when scripted moment is reached.
        Supports all photo-type achievements (scenic, milestone, story).
        """
        # All valid scripted photo types
        valid_photo_types = {
            # Original photo moments
            AchievementType.ROUTE_1_FLOWER,
            AchievementType.VIRIDIAN_FOREST_BREAK,
            # Story/location moments
            AchievementType.SS_ANNE_DECK,
            AchievementType.POKEMON_TOWER_SPOOKED,
            AchievementType.GAME_CORNER_SLOTS,
            AchievementType.FIGHTING_DOJO,
            AchievementType.SAFARI_ZONE_EXPLORER,
            AchievementType.TEAM_ROCKET_FIRST,
            # Scenic/Nature moments
            AchievementType.CERULEAN_CAPE,
            AchievementType.MT_MOON_EXIT,
            AchievementType.ROCK_TUNNEL_EXIT,
            AchievementType.CYCLING_ROAD,
            AchievementType.SEAFOAM_ISLANDS,
            AchievementType.ROUTE_12_FISHING,
            # Milestone moments
            AchievementType.PEWTER_GYM_ENTRANCE,
            AchievementType.INDIGO_PLATEAU,
            AchievementType.DAYCARE_VISIT,
        }

        if photo_type not in valid_photo_types:
            log.warning(f"Invalid scripted photo type: {photo_type}")
            return None

        return self.trigger(photo_type)

    def get_summary(self) -> str:
        """Get a summary of triggered achievements."""
        if not self.triggered:
            return "No achievements yet"

        lines = []
        for ach in self.triggered.values():
            status = "tweeted" if ach.tweet_posted else "pending"
            lines.append(f"- {ach.achievement_type.value}: {status}")

        return "\n".join(lines)


def create_achievement_tracker(
    storage_path: str = "data/achievements.json",
    reset_on_start: bool = False,
) -> AchievementTracker:
    """Factory function to create an AchievementTracker instance."""
    return AchievementTracker(storage_path=storage_path, reset_on_start=reset_on_start)
