import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Callable, Set
from pyAIAgent.game.name_planner import get_name_planner
from core.navigation_controller import NavigationController
from core.starter_planner import get_starter_planner, OAKS_LAB_MAP_ID

log = logging.getLogger("scenario_manager")

# Photo moments configuration (loaded from YAML)
PHOTO_MOMENTS = {}


def _load_scenario_data():
    """Load scenario data from YAML."""
    global PHOTO_MOMENTS
    data_path = Path(__file__).parent.parent / "data" / "game_data.yaml"
    if not data_path.exists():
        return

    try:
        import yaml

        with open(data_path, "r") as f:
            data = yaml.safe_load(f)
        PHOTO_MOMENTS = data.get("photo_moments", {})
    except Exception as e:
        log.error(f"Failed to load scenario data: {e}")


_load_scenario_data()


class ScenarioManager:
    """
    Manages hardcoded game scenarios, overrides, and scripted events.
    Handles:
    - Name Entry sequence (player name LASS, LLM-preplanned rival name)
    - Starter Pokemon selection (LLM-preplanned choice + nickname)
    - Pallet Town loop breaking
    - Invisible obstacle handling (stuck state)
    - Scripted photo moments (Loaded from game_data.yaml)
    """

    def __init__(self, navigation_controller: NavigationController):
        self.navigation_controller = navigation_controller
        self._achievement_tracker = None  # Set externally when initialized
        self._photo_callback = None  # Callback when photo moment triggers

        # Track triggered photo moments this session to avoid spam
        self._triggered_moments: Set[str] = set()

    def set_achievement_tracker(self, tracker) -> None:
        """Set the achievement tracker reference for photo moment triggers."""
        self._achievement_tracker = tracker

    def set_photo_callback(self, callback: Callable) -> None:
        """Set callback function to call when a photo moment is triggered."""
        self._photo_callback = callback

    def check_for_override(
        self, state: Dict[str, Any], cycle_count: int
    ) -> Optional[str]:
        """
        Check game state for forced actions that bypass the LLM.
        Returns an action string (e.g. "A;", "START;") or None.
        """
        # 1. Name Entry Override (handles player, rival, and pokemon nicknames)
        name_entry_action = self._check_name_entry(state)
        if name_entry_action:
            return name_entry_action

        # 2. Starter Selection Override (auto-navigate and select preplanned starter)
        starter_action = self._check_starter_selection(state)
        if starter_action:
            return starter_action

        # 3. Scripted Photo Moments
        self._check_photo_moments(state)

        # 4. Pallet Town Loop Breaker (Only if no goal exists)
        self._check_pallet_town_loop(state, cycle_count)

        return None

    def _check_name_entry(self, state: Dict[str, Any]) -> Optional[str]:
        """
        Handle name entry screen logic.

        Supports:
        - Player name: Always "LASS"
        - Rival name: LLM-preplanned or random fallback
        - Pokemon nickname: From StarterPlanner if available
        """
        name_entry_state = state.get("name_entry_state")
        if not name_entry_state:
            return None

        is_preset = name_entry_state.get("is_preset_menu", False)
        is_keyboard = name_entry_state.get("is_keyboard", False)

        if is_preset:
            # For preset menus, we ALWAYS want to select "NEW NAME" (Index 0)
            # to enter the custom name entry screen.
            cursor_index = name_entry_state.get("cursor_index", 0)

            if cursor_index > 0:
                log.info(
                    f"Preset menu detected (index {cursor_index}): Auto-executing 'UP' to reach 'NEW NAME'"
                )
                return "UP;"
            else:
                log.info(
                    "Preset menu detected (index 0): Auto-executing 'A' to enter custom name mode"
                )
                return "A;"

        if is_keyboard:
            planner = get_name_planner()
            starter_planner = get_starter_planner()

            # Prevent loop: If already confirmed, hand back to agent
            if planner.confirmation_sent:
                return None

            # Initialize typing if not already started
            if not planner.current_name:
                # Determine what we're naming based on name_type
                name_type = planner.name_type

                if name_type == "player":
                    # Always type LASS for player
                    planner.start_typing("LASS")
                    log.info("Name Entry: Typing player name 'LASS'")

                elif name_type == "rival":
                    # Use preplanned rival name (LLM-generated or random fallback)
                    rival_name = planner.get_planned_name()
                    if rival_name:
                        planner.start_typing(rival_name)
                        log.info(
                            f"Name Entry: Typing preplanned rival name '{rival_name}'"
                        )
                    else:
                        # Fallback to random if somehow not set
                        fallback = planner.get_random_rival_name()
                        planner.set_preplanned_rival_name(fallback, source="fallback")
                        planner.start_typing(fallback)
                        log.info(f"Name Entry: Using fallback rival name '{fallback}'")

                elif name_type == "pokemon":
                    # Check if this is a starter nickname
                    if (
                        starter_planner.waiting_for_nickname
                        and starter_planner.nickname
                    ):
                        nickname = starter_planner.nickname
                        planner.set_current_starter_nickname(nickname)
                        planner.start_typing(nickname)
                        log.info(f"Name Entry: Typing starter nickname '{nickname}'")
                    else:
                        # No preplanned nickname - skip by pressing START
                        log.info("Name Entry: No preplanned nickname, skipping")
                        return "START;"
                else:
                    # Unknown name type - try to infer from context
                    # Default to LASS if player_name not yet typed, otherwise skip
                    log.warning(
                        f"Name Entry: Unknown name_type '{name_type}', defaulting to LASS"
                    )
                    planner.start_typing("LASS")

            # Get next step in typing sequence
            # Ensure we actually have a name to type before checking completion
            if (
                planner.current_name
                and planner.is_done_typing()
                and not planner.confirmation_sent
            ):
                log.info("Name typing complete. Confirming with START.")
                planner.set_confirmation_sent(True)

                # If this was a starter nickname, mark it as entered
                if (
                    planner.name_type == "pokemon"
                    and starter_planner.waiting_for_nickname
                ):
                    starter_planner.mark_nickname_entered()

                return "START;"

            # If already confirmed but state still active, wait (return None)
            if planner.confirmation_sent:
                return None

            step = planner.get_current_step()
            if step:
                log.debug(f"Name Entry Step: '{step['char']}' -> {step['path']}")
                return step["path"]

        return None

    def _check_starter_selection(self, state: Dict[str, Any]) -> Optional[str]:
        """
        Handle starter Pokemon selection when player is in position.

        This is called after the LLM has generated a starter choice and
        the player has navigated to the target position.
        """
        starter_planner = get_starter_planner()

        # Skip if no plan or already obtained
        if not starter_planner.has_plan or starter_planner._starter_obtained:
            return None

        # Check if we're in Oak's lab
        map_id = state.get("map_id", 0)
        if map_id != OAKS_LAB_MAP_ID:
            return None

        # Get player position
        player_x = state.get("world_x", 0)
        player_y = state.get("world_y", 0)

        # Check if at target position
        if starter_planner.is_at_target(player_x, player_y):
            facing = state.get("facing", "").lower()

            # If facing north and at target, press A to get starter
            if facing == "up" or facing == "north":
                log.info(
                    f"At starter position facing north - pressing A to get {starter_planner.species}"
                )
                return "A;"
            else:
                # Face north first
                log.info(f"At starter position but facing {facing} - turning north")
                return "U;"

        return None

    def _check_pallet_town_loop(self, state: Dict[str, Any], cycle_count: int):
        """Force navigation goal if stuck in Pallet Town loop."""
        map_name = state.get("map_name", "")
        if map_name == "PALLET_TOWN" and not self.navigation_controller.goal_stack:
            log.info("Pallet Town Loop Breaker: Setting forced goal to Route 1")
            self.navigation_controller.set_exit_goal(
                exit_coords=(10, 1),
                map_name=map_name,
                map_id=state.get("map_id", 0),
                destination="Route 1 (Go EAST around house!)",
                current_cycle=cycle_count,
            )

    def check_invisible_obstacle(
        self,
        state: Dict[str, Any],
        stuck_info: Dict[str, Any],
        minimap_analysis: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check for invisible obstacles (stuck but map says walkable).
        Returns (is_detected, hint_text).
        """
        if not stuck_info.get("is_stuck"):
            return False, None

        # Check walkability from minimap analysis (if available)
        walkable = True  # Default to true if unknown, to trigger check
        if minimap_analysis:
            pass

        # Determine facing to avoid map boundaries
        facing = state.get("facing", "down")

        return False, None  # Placeholder for now

    def set_starter_navigation_goal(
        self, state: Dict[str, Any], cycle_count: int
    ) -> bool:
        """
        Set navigation goal to the preplanned starter Pokemon position.

        Called by llmdriver when starter choice is made and navigation should begin.

        Returns:
            True if goal was set, False otherwise
        """
        starter_planner = get_starter_planner()

        if not starter_planner.has_plan:
            log.warning("Cannot set starter nav goal: no starter plan exists")
            return False

        if starter_planner._starter_obtained:
            log.info("Starter already obtained, no navigation needed")
            return False

        target_pos = starter_planner.target_position
        if not target_pos:
            log.error("Starter plan has no target position")
            return False

        map_name = state.get("map_name", "OAKS_LAB")
        map_id = state.get("map_id", OAKS_LAB_MAP_ID)

        # Set navigation goal to stand in front of the starter Pokeball
        self.navigation_controller.set_exit_goal(
            exit_coords=target_pos,
            map_name=map_name,
            map_id=map_id,
            destination=f"Get {starter_planner.species} from Pokeball",
            current_cycle=cycle_count,
        )

        starter_planner.mark_navigation_started()
        log.info(
            f"Navigation goal set to starter position {target_pos} for {starter_planner.species}"
        )

        return True

    def _check_photo_moments(self, state: Dict[str, Any]) -> None:
        """
        Check if player is at a scripted photo location and trigger photo moment.
        Uses configuration from game_data.yaml.
        """
        if not self._achievement_tracker:
            return

        map_id = state.get("map_id", 0)
        player_x = state.get("world_x", 0)
        player_y = state.get("world_y", 0)

        for moment_id, info in PHOTO_MOMENTS.items():
            # Skip if already triggered this session
            if moment_id in self._triggered_moments:
                continue

            # Skip if already in achievement tracker
            achievement_type = self._get_achievement_type(moment_id)
            if not achievement_type or self._achievement_tracker.is_triggered(
                achievement_type
            ):
                self._triggered_moments.add(moment_id)
                continue

            # Check Map ID (can be single ID or list)
            target_map_ids = info.get("map_ids") or [info.get("map_id")]
            if map_id not in target_map_ids:
                continue

            # Check specific triggers
            triggered = False

            if "position" in info:
                target_x, target_y = info["position"]
                dist_range = info.get("range", 2)
                if (
                    abs(player_x - target_x) <= dist_range
                    and abs(player_y - target_y) <= dist_range
                ):
                    triggered = True
            elif "min_x" in info:
                if player_x >= info["min_x"]:
                    triggered = True
            elif "min_y" in info:
                if player_y >= info["min_y"]:
                    triggered = True
            else:
                # Map entry only
                triggered = True

            if triggered:
                self._trigger_photo_moment(moment_id)
                self._triggered_moments.add(moment_id)

    def _get_achievement_type(self, name: str):
        """Get AchievementType enum from string name."""
        try:
            from trackers.achievement_tracker import AchievementType

            type_map = {
                # Original photo moments
                "route_1_flower": AchievementType.ROUTE_1_FLOWER,
                "viridian_forest_break": AchievementType.VIRIDIAN_FOREST_BREAK,
                # Story/location moments
                "ss_anne_deck": AchievementType.SS_ANNE_DECK,
                "pokemon_tower_spooked": AchievementType.POKEMON_TOWER_SPOOKED,
                "game_corner_slots": AchievementType.GAME_CORNER_SLOTS,
                "fighting_dojo": AchievementType.FIGHTING_DOJO,
                "safari_zone_explorer": AchievementType.SAFARI_ZONE_EXPLORER,
                "team_rocket_first": AchievementType.TEAM_ROCKET_FIRST,
                # Scenic/Nature moments
                "cerulean_cape": AchievementType.CERULEAN_CAPE,
                "mt_moon_exit": AchievementType.MT_MOON_EXIT,
                "rock_tunnel_exit": AchievementType.ROCK_TUNNEL_EXIT,
                "cycling_road": AchievementType.CYCLING_ROAD,
                "seafoam_islands": AchievementType.SEAFOAM_ISLANDS,
                "route_12_fishing": AchievementType.ROUTE_12_FISHING,
                # Milestone moments
                "pewter_gym_entrance": AchievementType.PEWTER_GYM_ENTRANCE,
                "indigo_plateau": AchievementType.INDIGO_PLATEAU,
                "daycare_visit": AchievementType.DAYCARE_VISIT,
            }
            return type_map.get(name)
        except ImportError:
            return None

    def _trigger_photo_moment(self, photo_type: str) -> None:
        """
        Trigger a scripted photo moment.

        This will:
        1. Trigger the achievement in the tracker
        2. Call the photo callback if set (for tweet generation)
        """
        log.info(f"📸 SCRIPTED PHOTO MOMENT: {photo_type}")

        achievement_type = self._get_achievement_type(photo_type)
        if not achievement_type:
            log.warning(f"Unknown photo type: {photo_type}")
            return

        # Trigger achievement
        if self._achievement_tracker:
            achievement = self._achievement_tracker.trigger_scripted_photo(
                achievement_type
            )
            if achievement and self._photo_callback:
                # Call the callback to trigger tweet generation
                try:
                    self._photo_callback(achievement)
                except Exception as e:
                    log.error(f"Photo callback error: {e}")
