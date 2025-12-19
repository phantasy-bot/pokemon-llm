"""
Starter Planner for Pokemon LLM Agent

Manages the pre-planned starter Pokemon selection:
- Stores the AI's chosen starter (species + nickname)
- Tracks position for navigation to the correct Pokeball
- Coordinates with ScenarioManager for auto-execution
"""

import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

log = logging.getLogger("starter_planner")

# Starter Pokemon positions in Oak's Lab (world coordinates)
# The player must stand south of the Pokeball and face north to interact
STARTER_POSITIONS = {
    "CHARMANDER": (6, 3),  # Pokeball at (6, 3), player stands at (6, 4)
    "SQUIRTLE": (7, 3),  # Pokeball at (7, 3), player stands at (7, 4)
    "BULBASAUR": (8, 3),  # Pokeball at (8, 3), player stands at (8, 4)
}

# Map ID for Oak's Lab
OAKS_LAB_MAP_ID = 0x28


@dataclass
class StarterPlan:
    """Represents the complete starter selection plan."""

    species: str  # CHARMANDER, SQUIRTLE, or BULBASAUR
    nickname: str  # Nickname for the Pokemon
    pokeball_pos: Tuple[int, int]  # Position of the Pokeball
    player_target_pos: Tuple[int, int]  # Where player should stand

    def __post_init__(self):
        """Validate and set positions."""
        if self.species not in STARTER_POSITIONS:
            raise ValueError(f"Invalid starter species: {self.species}")

        self.pokeball_pos = STARTER_POSITIONS[self.species]
        # Player stands 1 tile south of Pokeball (higher Y)
        self.player_target_pos = (self.pokeball_pos[0], self.pokeball_pos[1] + 1)


class StarterPlanner:
    """
    Manages starter Pokemon selection planning and execution tracking.

    Workflow:
    1. LLM generates starter choice (species + nickname) when entering Oak's lab
    2. StarterPlanner stores the choice and computes target position
    3. ScenarioManager uses A* pathfinding to navigate player to position
    4. When at position, facing north + A triggers Pokeball interaction
    5. After obtaining starter, nickname entry screen appears
    6. NamePlanner handles auto-typing the pre-planned nickname
    """

    def __init__(self):
        self._plan: Optional[StarterPlan] = None

        # Execution state
        self._navigation_started: bool = False
        self._at_target_position: bool = False
        self._starter_obtained: bool = False
        self._waiting_for_nickname: bool = False
        self._nickname_entered: bool = False

        # Track if choice was made this run (for persistence)
        self._choice_made_this_run: bool = False

    @property
    def has_plan(self) -> bool:
        """Check if a starter plan exists."""
        return self._plan is not None

    @property
    def plan(self) -> Optional[StarterPlan]:
        """Get the current starter plan."""
        return self._plan

    @property
    def species(self) -> Optional[str]:
        """Get the planned starter species."""
        return self._plan.species if self._plan else None

    @property
    def nickname(self) -> Optional[str]:
        """Get the planned starter nickname."""
        return self._plan.nickname if self._plan else None

    @property
    def target_position(self) -> Optional[Tuple[int, int]]:
        """Get the target position for the player to stand."""
        return self._plan.player_target_pos if self._plan else None

    @property
    def pokeball_position(self) -> Optional[Tuple[int, int]]:
        """Get the Pokeball position."""
        return self._plan.pokeball_pos if self._plan else None

    @property
    def is_complete(self) -> bool:
        """Check if starter selection is fully complete (obtained + nicknamed)."""
        return self._starter_obtained and self._nickname_entered

    @property
    def waiting_for_nickname(self) -> bool:
        """Check if waiting for nickname entry screen."""
        return self._waiting_for_nickname

    def set_choice(self, species: str, nickname: str) -> bool:
        """
        Set the starter Pokemon choice.

        Args:
            species: CHARMANDER, SQUIRTLE, or BULBASAUR
            nickname: Nickname for the Pokemon (max 10 chars, uppercase)

        Returns:
            True if valid choice set, False otherwise
        """
        species = species.upper().strip()
        nickname = nickname.upper().strip()[:10]

        if species not in STARTER_POSITIONS:
            log.error(f"Invalid starter species: {species}")
            return False

        if not nickname:
            log.warning("Empty nickname provided, using species name as fallback")
            nickname = species[:10]

        self._plan = StarterPlan(
            species=species,
            nickname=nickname,
            pokeball_pos=STARTER_POSITIONS[species],
            player_target_pos=(
                STARTER_POSITIONS[species][0],
                STARTER_POSITIONS[species][1] + 1,
            ),
        )

        self._choice_made_this_run = True
        self._navigation_started = False
        self._at_target_position = False
        self._starter_obtained = False
        self._waiting_for_nickname = False
        self._nickname_entered = False

        log.info(
            f"Starter plan set: {species} nicknamed '{nickname}' "
            f"(target pos: {self._plan.player_target_pos})"
        )
        return True

    def is_at_target(self, player_x: int, player_y: int) -> bool:
        """
        Check if player is at the target position for starter selection.

        Args:
            player_x, player_y: Current player world coordinates

        Returns:
            True if at target position
        """
        if not self._plan:
            return False

        target_x, target_y = self._plan.player_target_pos
        at_target = player_x == target_x and player_y == target_y

        if at_target and not self._at_target_position:
            self._at_target_position = True
            log.info(
                f"Player reached starter target position: ({player_x}, {player_y})"
            )

        return at_target

    def mark_navigation_started(self):
        """Mark that navigation to starter has begun."""
        self._navigation_started = True
        log.info("Starter navigation started")

    def mark_starter_obtained(self):
        """Mark that the starter Pokemon was obtained."""
        self._starter_obtained = True
        self._waiting_for_nickname = True
        log.info(f"Starter {self.species} obtained! Waiting for nickname entry...")

    def mark_nickname_entered(self):
        """Mark that the nickname was entered."""
        self._nickname_entered = True
        self._waiting_for_nickname = False
        log.info(f"Nickname '{self.nickname}' entered! Starter selection complete.")

    def get_nav_context(self, player_x: int, player_y: int) -> str:
        """
        Get navigation context for LLM about starter selection.

        Args:
            player_x, player_y: Current player position

        Returns:
            Formatted string for LLM context
        """
        if not self._plan:
            return ""

        target_x, target_y = self._plan.player_target_pos
        dx = target_x - player_x
        dy = target_y - player_y
        distance = abs(dx) + abs(dy)

        if self._at_target_position or distance == 0:
            return (
                f"STARTER SELECTION - AT TARGET POSITION!\n"
                f"You chose: {self._plan.species} (nickname: {self._plan.nickname})\n"
                f"Face NORTH and press A to pick up the Pokeball!\n"
            )
        else:
            direction_hints = []
            if dx > 0:
                direction_hints.append(f"go RIGHT {dx}")
            elif dx < 0:
                direction_hints.append(f"go LEFT {abs(dx)}")
            if dy > 0:
                direction_hints.append(f"go DOWN {dy}")
            elif dy < 0:
                direction_hints.append(f"go UP {abs(dy)}")

            return (
                f"STARTER SELECTION - NAVIGATE TO POKEBALL\n"
                f"You chose: {self._plan.species} (nickname: {self._plan.nickname})\n"
                f"Target position: ({target_x}, {target_y})\n"
                f"Your position: ({player_x}, {player_y})\n"
                f"Distance: {distance} tiles ({', '.join(direction_hints)})\n"
            )

    def reset(self):
        """Reset all state (for new run or testing)."""
        self._plan = None
        self._navigation_started = False
        self._at_target_position = False
        self._starter_obtained = False
        self._waiting_for_nickname = False
        self._nickname_entered = False
        self._choice_made_this_run = False
        log.info("StarterPlanner reset")

    def to_dict(self) -> dict:
        """Serialize state for persistence."""
        return {
            "species": self._plan.species if self._plan else None,
            "nickname": self._plan.nickname if self._plan else None,
            "navigation_started": self._navigation_started,
            "at_target_position": self._at_target_position,
            "starter_obtained": self._starter_obtained,
            "waiting_for_nickname": self._waiting_for_nickname,
            "nickname_entered": self._nickname_entered,
            "choice_made_this_run": self._choice_made_this_run,
        }

    def from_dict(self, data: dict):
        """Restore state from persistence."""
        species = data.get("species")
        nickname = data.get("nickname")

        if species and nickname:
            self.set_choice(species, nickname)

        self._navigation_started = data.get("navigation_started", False)
        self._at_target_position = data.get("at_target_position", False)
        self._starter_obtained = data.get("starter_obtained", False)
        self._waiting_for_nickname = data.get("waiting_for_nickname", False)
        self._nickname_entered = data.get("nickname_entered", False)
        self._choice_made_this_run = data.get("choice_made_this_run", False)

        log.info(f"StarterPlanner restored: {self.to_dict()}")


# Global singleton
_starter_planner_instance: Optional[StarterPlanner] = None


def get_starter_planner() -> StarterPlanner:
    """Get the global StarterPlanner instance."""
    global _starter_planner_instance
    if _starter_planner_instance is None:
        _starter_planner_instance = StarterPlanner()
    return _starter_planner_instance


def reset_starter_planner():
    """Reset the global StarterPlanner instance."""
    global _starter_planner_instance
    if _starter_planner_instance:
        _starter_planner_instance.reset()
    _starter_planner_instance = None
