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
from typing import Optional, Dict, List, Set, Any
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


# Starter evolution chains for detection
STARTER_EVOLUTIONS = {
    # Charmander line
    "CHARMANDER": {"stage": 1, "next": "CHARMELEON", "line": "fire"},
    "CHARMELEON": {"stage": 2, "next": "CHARIZARD", "line": "fire"},
    "CHARIZARD": {"stage": 3, "next": None, "line": "fire"},
    # Squirtle line
    "SQUIRTLE": {"stage": 1, "next": "WARTORTLE", "line": "water"},
    "WARTORTLE": {"stage": 2, "next": "BLASTOISE", "line": "water"},
    "BLASTOISE": {"stage": 3, "next": None, "line": "water"},
    # Bulbasaur line
    "BULBASAUR": {"stage": 1, "next": "IVYSAUR", "line": "grass"},
    "IVYSAUR": {"stage": 2, "next": "VENUSAUR", "line": "grass"},
    "VENUSAUR": {"stage": 3, "next": None, "line": "grass"},
}

# Legendary Pokemon names
LEGENDARY_POKEMON = {"ARTICUNO", "ZAPDOS", "MOLTRES", "MEWTWO"}

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
    """Image generation prompts for an achievement."""

    positive_prompt: str  # Added to base prompt for image generation
    negative_prompt: str = ""  # Additional negative prompt (optional)
    scene_description: str = ""  # Description for tweet context


# Achievement-specific image prompts
# These are ADDED to the base Lass character prompt
ACHIEVEMENT_IMAGE_PROMPTS: Dict[AchievementType, AchievementImagePrompt] = {
    AchievementType.STREAM_START: AchievementImagePrompt(
        positive_prompt="excited pose, waving at viewer, sparkles, happy expression, energetic, ready for adventure",
        scene_description="Starting a new Pokemon adventure",
    ),
    AchievementType.FIRST_POKEMON: AchievementImagePrompt(
        positive_prompt="holding pokeball lovingly, gentle smile, warm lighting, professor oak's lab background, first pokemon moment, emotional, happy tears",
        scene_description="Receiving first Pokemon from Professor Oak",
    ),
    AchievementType.ROUTE_1_FLOWER: AchievementImagePrompt(
        positive_prompt="kneeling in flower field, smelling flowers, peaceful expression, route 1 grassland, wildflowers, butterflies, serene nature scene, golden hour lighting",
        scene_description="Taking a peaceful moment on Route 1",
    ),
    AchievementType.FIRST_CATCH: AchievementImagePrompt(
        positive_prompt="triumphant pose, holding pokeball up victoriously, excited expression, celebration, first catch success, sparkles around pokeball",
        scene_description="Catching first wild Pokemon",
    ),
    AchievementType.VIRIDIAN_FOREST_BREAK: AchievementImagePrompt(
        positive_prompt="sitting on log, forest background, dappled sunlight through trees, peaceful rest, viridian forest, bug pokemon nearby, relaxed pose, drinking from canteen",
        scene_description="Taking a break in Viridian Forest",
    ),
    AchievementType.STARTER_EVOLUTION_1: AchievementImagePrompt(
        positive_prompt="amazed expression, watching evolution light, bright glow effects, evolution energy swirling, proud moment, emotional",
        scene_description="Watching starter Pokemon evolve for the first time",
    ),
    AchievementType.STARTER_EVOLUTION_2: AchievementImagePrompt(
        positive_prompt="standing with fully evolved starter, powerful pose, dramatic lighting, final evolution complete, bond between trainer and pokemon, epic moment",
        scene_description="Starter Pokemon reaches final evolution",
    ),
    AchievementType.BADGE_BOULDER: AchievementImagePrompt(
        positive_prompt="holding boulder badge proudly, pewter city gym, rock type aesthetic, determined expression, first gym victory",
        scene_description="Earning the Boulder Badge from Brock",
    ),
    AchievementType.BADGE_CASCADE: AchievementImagePrompt(
        positive_prompt="holding cascade badge, cerulean city gym, water droplets, aquarium background, refreshed and victorious",
        scene_description="Earning the Cascade Badge from Misty",
    ),
    AchievementType.BADGE_THUNDER: AchievementImagePrompt(
        positive_prompt="holding thunder badge, electric sparks, vermilion city gym, lightning effects, electrifying victory",
        scene_description="Earning the Thunder Badge from Lt. Surge",
    ),
    AchievementType.BADGE_RAINBOW: AchievementImagePrompt(
        positive_prompt="holding rainbow badge, celadon city gym, flowers and nature, colorful lighting, grass type aesthetic",
        scene_description="Earning the Rainbow Badge from Erika",
    ),
    AchievementType.BADGE_SOUL: AchievementImagePrompt(
        positive_prompt="holding soul badge, fuchsia city gym, ninja aesthetic, mysterious atmosphere, poison type vibes",
        scene_description="Earning the Soul Badge from Koga",
    ),
    AchievementType.BADGE_MARSH: AchievementImagePrompt(
        positive_prompt="holding marsh badge, saffron city gym, psychic energy effects, mystical atmosphere, mind power",
        scene_description="Earning the Marsh Badge from Sabrina",
    ),
    AchievementType.BADGE_VOLCANO: AchievementImagePrompt(
        positive_prompt="holding volcano badge, cinnabar island gym, fire and lava background, intense heat, fire type power",
        scene_description="Earning the Volcano Badge from Blaine",
    ),
    AchievementType.BADGE_EARTH: AchievementImagePrompt(
        positive_prompt="holding earth badge, viridian city gym, ground type aesthetic, final badge triumph, all eight badges complete, epic achievement",
        scene_description="Earning the Earth Badge - all 8 badges collected",
    ),
    AchievementType.LEGENDARY_ARTICUNO: AchievementImagePrompt(
        positive_prompt="standing with articuno, ice cave background, frozen beauty, legendary bird, majestic ice wings, snowflakes, awe-struck expression",
        scene_description="Capturing the legendary Articuno",
    ),
    AchievementType.LEGENDARY_ZAPDOS: AchievementImagePrompt(
        positive_prompt="standing with zapdos, power plant background, electric legendary, lightning storm, electrifying presence, hair standing from static",
        scene_description="Capturing the legendary Zapdos",
    ),
    AchievementType.LEGENDARY_MOLTRES: AchievementImagePrompt(
        positive_prompt="standing with moltres, victory road background, fire legendary, blazing wings, warm glow, phoenix-like majesty",
        scene_description="Capturing the legendary Moltres",
    ),
    AchievementType.LEGENDARY_MEWTWO: AchievementImagePrompt(
        positive_prompt="standing with mewtwo, cerulean cave background, psychic legendary, mysterious aura, ultimate pokemon, genetic power",
        scene_description="Capturing the legendary Mewtwo",
    ),
    AchievementType.POKEMON_CHAMPION: AchievementImagePrompt(
        positive_prompt="champion pose, hall of fame, trophy, confetti, championship victory, ultimate triumph, tears of joy, all pokemon team behind her, legendary achievement, golden lighting, epic finale",
        scene_description="Becoming the Pokemon League Champion",
    ),
    # New scripted location moments
    AchievementType.TEAM_ROCKET_FIRST: AchievementImagePrompt(
        positive_prompt="defensive battle pose, facing team rocket grunt, determined expression, standing ground against evil, heroic moment, underground hideout background",
        scene_description="First encounter with Team Rocket",
    ),
    AchievementType.SS_ANNE_DECK: AchievementImagePrompt(
        positive_prompt="standing on ship deck, looking out at ocean, wind in hair, peaceful ocean view, sunset over water, SS Anne cruise ship, nautical atmosphere, serene expression",
        scene_description="Enjoying the view from SS Anne deck",
    ),
    AchievementType.POKEMON_TOWER_SPOOKED: AchievementImagePrompt(
        positive_prompt="scared expression, haunted tower background, ghost pokemon silhouettes, spooky purple mist, lavender town cemetery, frightened but brave, holding onto pokeball nervously",
        scene_description="Spooked by ghosts in Pokemon Tower",
    ),
    AchievementType.GAME_CORNER_SLOTS: AchievementImagePrompt(
        positive_prompt="sitting at slot machine, casino lights, excited gambling expression, coins and tokens, game corner neon signs, celadon city, lucky pose, fun atmosphere",
        scene_description="Trying luck at the Game Corner slots",
    ),
    AchievementType.FIGHTING_DOJO: AchievementImagePrompt(
        positive_prompt="martial arts pose, fighting dojo background, karate stance, determined expression, training with fighting type pokemon, saffron city dojo, black belt aesthetic, powerful aura",
        scene_description="Training at the Fighting Dojo",
    ),
    AchievementType.SAFARI_ZONE_EXPLORER: AchievementImagePrompt(
        positive_prompt="wearing safari hat, explorer pose, binoculars in hand, safari zone wilderness, exotic pokemon in background, adventure outfit, excited explorer expression, tall grass",
        scene_description="Exploring the Safari Zone",
    ),
    # Scenic/Nature photo moments
    AchievementType.CERULEAN_CAPE: AchievementImagePrompt(
        positive_prompt="standing on coastal cliff, ocean view, sea breeze blowing hair, cerulean cape, bill's cottage in background, peaceful seaside, sparkling water, seagulls flying",
        scene_description="Enjoying the ocean view from Cerulean Cape",
    ),
    AchievementType.MT_MOON_EXIT: AchievementImagePrompt(
        positive_prompt="stepping into sunlight, shielding eyes from brightness, relief expression, mountain exit, fresh air, blue sky visible, leaving cave behind, happy to see daylight",
        scene_description="Finally emerging from Mt. Moon into daylight",
    ),
    AchievementType.ROCK_TUNNEL_EXIT: AchievementImagePrompt(
        positive_prompt="blinking in bright light, exhausted but relieved, cave exit, daylight streaming in, dusty from tunnel, triumphant survival, route 10 visible ahead",
        scene_description="Escaping the darkness of Rock Tunnel",
    ),
    AchievementType.CYCLING_ROAD: AchievementImagePrompt(
        positive_prompt="riding bicycle, wind in hair, cycling road downhill, speed lines, excited expression, bike path scenery, ocean visible below, freedom feeling, sporty pose",
        scene_description="Cruising down Cycling Road",
    ),
    AchievementType.SEAFOAM_ISLANDS: AchievementImagePrompt(
        positive_prompt="bundled up from cold, icy cave background, frozen crystals, breath visible in cold air, beautiful ice formations, seafoam islands interior, winter wonderland underground",
        scene_description="Exploring the frozen Seafoam Islands caves",
    ),
    AchievementType.ROUTE_12_FISHING: AchievementImagePrompt(
        positive_prompt="sitting on pier with fishing rod, relaxed pose, waiting for bite, route 12 silence pier, calm water, peaceful fishing moment, sunset colors, patient expression, tackle box nearby",
        scene_description="Peaceful fishing on Route 12",
    ),
    # Milestone photo moments
    AchievementType.PEWTER_GYM_ENTRANCE: AchievementImagePrompt(
        positive_prompt="standing at gym entrance, determined expression, pewter city gym sign, first gym challenge, nervous but excited, rock type decorations, taking deep breath before entering",
        scene_description="About to enter the first gym",
    ),
    AchievementType.INDIGO_PLATEAU: AchievementImagePrompt(
        positive_prompt="standing at pokemon league entrance, awe-struck expression, indigo plateau grand building, final destination reached, epic journey complete, majestic architecture, elite four awaits",
        scene_description="Arriving at the Indigo Plateau Pokemon League",
    ),
    AchievementType.DAYCARE_VISIT: AchievementImagePrompt(
        positive_prompt="standing at daycare fence, looking at pokemon playing, route 5 daycare, wholesome scene, curious expression, elderly daycare couple, baby pokemon in background, pastoral setting",
        scene_description="Visiting the Pokemon Daycare on Route 5",
    ),
}


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
        context: Dict[str, Any] = None,
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
        self, achievement_type: AchievementType, tweet_url: str = None
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
            AchievementImagePrompt(positive_prompt="", scene_description=""),
        )

    # =========================================================================
    # Achievement Detection Methods
    # =========================================================================

    def check_for_achievements(
        self,
        current_party: List[Dict],
        current_badges: List[str],
        current_map: str,
        game_state: Dict[str, Any] = None,
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
        self, current_map: str, game_state: Dict[str, Any] = None
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
