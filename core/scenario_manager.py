import logging
from typing import Optional, Dict, Any, Tuple, Callable
from pyAIAgent.game.name_planner import get_name_planner
from core.navigation_controller import NavigationController
from core.starter_planner import get_starter_planner, OAKS_LAB_MAP_ID

log = logging.getLogger("scenario_manager")

# Map IDs for scripted photo locations
ROUTE_1_MAP_ID = 0x0C  # Route 1
VIRIDIAN_FOREST_MAP_ID = 0x33  # Viridian Forest
SS_ANNE_BOW_MAP_ID = 0x63  # SS Anne Bow/Deck
POKEMON_TOWER_3F_MAP_ID = 0x90  # Pokemon Tower 3F (spooky floor)
POKEMON_TOWER_4F_MAP_ID = 0x91  # Pokemon Tower 4F
GAME_CORNER_MAP_ID = 0x87  # Game Corner
FIGHTING_DOJO_MAP_ID = 0xB1  # Fighting Dojo
SAFARI_ZONE_CENTER_MAP_ID = 0xDC  # Safari Zone Center
ROCKET_HIDEOUT_B1F_MAP_ID = 0xC7  # Rocket Hideout B1F (first encounter)

# New scenic/nature photo locations
ROUTE_25_MAP_ID = 0x1B  # Route 25 (Cerulean Cape / Bill's area)
ROUTE_4_MAP_ID = 0x0F  # Route 4 (Mt. Moon exit)
ROUTE_10_MAP_ID = 0x15  # Route 10 (Rock Tunnel exit)
ROUTE_16_MAP_ID = 0x11  # Route 16 (Cycling Road start)
ROUTE_17_MAP_ID = 0x12  # Route 17 (Cycling Road main)
SEAFOAM_B4F_MAP_ID = 0xC0  # Seafoam Islands B4F (ice area)
ROUTE_12_MAP_ID = 0x17  # Route 12 (Fishing pier)

# Milestone photo locations
PEWTER_GYM_MAP_ID = 0x36  # Pewter City Gym
INDIGO_PLATEAU_LOBBY_MAP_ID = 0x76  # Indigo Plateau Lobby
DAYCARE_MAP_ID = 0x48  # Pokemon Daycare (Route 5)

# Scripted photo positions (x, y) - specific scenic spots
ROUTE_1_FLOWER_POSITION = (10, 18)  # Middle of Route 1, flower area
VIRIDIAN_FOREST_BREAK_POSITION = (17, 25)  # Clearing in forest
SS_ANNE_DECK_POSITION = (7, 2)  # Bow of SS Anne looking out
POKEMON_TOWER_POSITION = (10, 8)  # Center of tower floor
GAME_CORNER_SLOT_POSITION = (7, 8)  # Slot machine area
FIGHTING_DOJO_POSITION = (5, 5)  # Center of dojo
SAFARI_ZONE_POSITION = (15, 15)  # Safari Zone exploration spot

# New scenic photo positions
CERULEAN_CAPE_POSITION = (45, 3)  # Near Bill's house, ocean view
ROUTE_4_EXIT_POSITION = (15, 10)  # East side of Route 4 after Mt. Moon
ROUTE_10_EXIT_POSITION = (8, 40)  # South Route 10 after Rock Tunnel
CYCLING_ROAD_START_POSITION = (10, 5)  # Start of Cycling Road
SEAFOAM_ICE_POSITION = (12, 10)  # Near ice puzzle area
ROUTE_12_FISHING_POSITION = (8, 30)  # Fishing pier on Route 12 (Silence Bridge area)


class ScenarioManager:
    """
    Manages hardcoded game scenarios, overrides, and scripted events.
    Handles:
    - Name Entry sequence (player name LASS, LLM-preplanned rival name)
    - Starter Pokemon selection (LLM-preplanned choice + nickname)
    - Pallet Town loop breaking
    - Invisible obstacle handling (stuck state)
    - Scripted photo moments (Route 1 flowers, Viridian Forest break)
    """

    def __init__(self, navigation_controller: NavigationController):
        self.navigation_controller = navigation_controller
        self._achievement_tracker = None  # Set externally when initialized
        self._photo_callback = None  # Callback when photo moment triggers

        # Track if we've already triggered each photo moment this session
        self._route1_photo_triggered = False
        self._viridian_photo_triggered = False
        self._ss_anne_photo_triggered = False
        self._pokemon_tower_photo_triggered = False
        self._game_corner_photo_triggered = False
        self._fighting_dojo_photo_triggered = False
        self._safari_zone_photo_triggered = False
        self._team_rocket_photo_triggered = False
        # New scenic/nature photo flags
        self._cerulean_cape_photo_triggered = False
        self._mt_moon_exit_photo_triggered = False
        self._rock_tunnel_exit_photo_triggered = False
        self._cycling_road_photo_triggered = False
        self._seafoam_photo_triggered = False
        self._route12_fishing_photo_triggered = False
        # Milestone photo flags
        self._pewter_gym_photo_triggered = False
        self._indigo_plateau_photo_triggered = False
        self._daycare_photo_triggered = False

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

        # 3. Scripted Photo Moments (Route 1 flowers, Viridian Forest break)
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

        Scripted photo moments:
        - Route 1 flowers: Scenic spot to appreciate nature
        - Viridian Forest break: Rest spot in the forest
        - SS Anne deck: Looking out at the ocean
        - Pokemon Tower: Spooked by ghosts
        - Game Corner: Playing the slots
        - Fighting Dojo: Training martial arts
        - Safari Zone: Explorer adventure
        - Rocket Hideout: First Team Rocket encounter
        """
        if not self._achievement_tracker:
            return  # No tracker set, skip

        map_id = state.get("map_id", 0)
        player_x = state.get("world_x", 0)
        player_y = state.get("world_y", 0)

        # Route 1 Flower Photo
        if (
            map_id == ROUTE_1_MAP_ID
            and not self._route1_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("route_1_flower")
            )
        ):
            target_x, target_y = ROUTE_1_FLOWER_POSITION
            if abs(player_x - target_x) <= 2 and abs(player_y - target_y) <= 2:
                self._trigger_photo_moment("route_1_flower")
                self._route1_photo_triggered = True

        # Viridian Forest Break Photo
        if (
            map_id == VIRIDIAN_FOREST_MAP_ID
            and not self._viridian_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("viridian_forest_break")
            )
        ):
            target_x, target_y = VIRIDIAN_FOREST_BREAK_POSITION
            if abs(player_x - target_x) <= 3 and abs(player_y - target_y) <= 3:
                self._trigger_photo_moment("viridian_forest_break")
                self._viridian_photo_triggered = True

        # SS Anne Deck Photo - Looking out at the ocean
        if (
            map_id == SS_ANNE_BOW_MAP_ID
            and not self._ss_anne_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("ss_anne_deck")
            )
        ):
            target_x, target_y = SS_ANNE_DECK_POSITION
            if abs(player_x - target_x) <= 2 and abs(player_y - target_y) <= 2:
                self._trigger_photo_moment("ss_anne_deck")
                self._ss_anne_photo_triggered = True

        # Pokemon Tower Spooked Photo - Any floor 3-5 (spookiest)
        if (
            map_id in (POKEMON_TOWER_3F_MAP_ID, POKEMON_TOWER_4F_MAP_ID)
            and not self._pokemon_tower_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("pokemon_tower_spooked")
            )
        ):
            # Trigger anywhere on these floors (always spooky!)
            self._trigger_photo_moment("pokemon_tower_spooked")
            self._pokemon_tower_photo_triggered = True

        # Game Corner Slots Photo - At the slot machines
        if (
            map_id == GAME_CORNER_MAP_ID
            and not self._game_corner_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("game_corner_slots")
            )
        ):
            target_x, target_y = GAME_CORNER_SLOT_POSITION
            if abs(player_x - target_x) <= 3 and abs(player_y - target_y) <= 3:
                self._trigger_photo_moment("game_corner_slots")
                self._game_corner_photo_triggered = True

        # Fighting Dojo Photo - Training at the dojo
        if (
            map_id == FIGHTING_DOJO_MAP_ID
            and not self._fighting_dojo_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("fighting_dojo")
            )
        ):
            # Trigger when entering the dojo
            self._trigger_photo_moment("fighting_dojo")
            self._fighting_dojo_photo_triggered = True

        # Safari Zone Explorer Photo
        if (
            map_id == SAFARI_ZONE_CENTER_MAP_ID
            and not self._safari_zone_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("safari_zone_explorer")
            )
        ):
            # Trigger when entering Safari Zone center
            self._trigger_photo_moment("safari_zone_explorer")
            self._safari_zone_photo_triggered = True

        # Team Rocket First Encounter Photo
        if (
            map_id == ROCKET_HIDEOUT_B1F_MAP_ID
            and not self._team_rocket_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("team_rocket_first")
            )
        ):
            # Trigger when first entering Rocket Hideout
            self._trigger_photo_moment("team_rocket_first")
            self._team_rocket_photo_triggered = True

        # ═══════════════════════════════════════════════════════════════════════════
        # NEW SCENIC/NATURE PHOTO MOMENTS
        # ═══════════════════════════════════════════════════════════════════════════

        # Cerulean Cape - Ocean view near Bill's house (position-based)
        if (
            map_id == ROUTE_25_MAP_ID
            and not self._cerulean_cape_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("cerulean_cape")
            )
        ):
            target_x, target_y = CERULEAN_CAPE_POSITION
            if abs(player_x - target_x) <= 4 and abs(player_y - target_y) <= 3:
                self._trigger_photo_moment("cerulean_cape")
                self._cerulean_cape_photo_triggered = True

        # Mt. Moon Exit - Relief after darkness (position-based, east side of Route 4)
        if (
            map_id == ROUTE_4_MAP_ID
            and not self._mt_moon_exit_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("mt_moon_exit")
            )
        ):
            target_x, target_y = ROUTE_4_EXIT_POSITION
            # Trigger when on east side of Route 4 (exited Mt. Moon)
            if player_x >= 10 and abs(player_y - target_y) <= 3:
                self._trigger_photo_moment("mt_moon_exit")
                self._mt_moon_exit_photo_triggered = True

        # Rock Tunnel Exit - Daylight after darkness (position-based, south Route 10)
        if (
            map_id == ROUTE_10_MAP_ID
            and not self._rock_tunnel_exit_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("rock_tunnel_exit")
            )
        ):
            target_x, target_y = ROUTE_10_EXIT_POSITION
            # Trigger when in southern part of Route 10 (exited Rock Tunnel)
            if player_y >= 35:
                self._trigger_photo_moment("rock_tunnel_exit")
                self._rock_tunnel_exit_photo_triggered = True

        # Cycling Road - Cruising down the bike path (map-entry based)
        if (
            map_id in (ROUTE_16_MAP_ID, ROUTE_17_MAP_ID)
            and not self._cycling_road_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("cycling_road")
            )
        ):
            # Trigger when entering Cycling Road
            self._trigger_photo_moment("cycling_road")
            self._cycling_road_photo_triggered = True

        # Seafoam Islands - Icy cave adventure (map-entry based)
        if (
            map_id == SEAFOAM_B4F_MAP_ID
            and not self._seafoam_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("seafoam_islands")
            )
        ):
            # Trigger when reaching the deep ice floor
            self._trigger_photo_moment("seafoam_islands")
            self._seafoam_photo_triggered = True

        # Route 12 Fishing - Peaceful fishing moment (position-based)
        if (
            map_id == ROUTE_12_MAP_ID
            and not self._route12_fishing_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("route_12_fishing")
            )
        ):
            target_x, target_y = ROUTE_12_FISHING_POSITION
            if abs(player_x - target_x) <= 3 and abs(player_y - target_y) <= 5:
                self._trigger_photo_moment("route_12_fishing")
                self._route12_fishing_photo_triggered = True

        # ═══════════════════════════════════════════════════════════════════════════
        # MILESTONE PHOTO MOMENTS
        # ═══════════════════════════════════════════════════════════════════════════

        # Pewter Gym Entrance - First gym challenge (map-entry based)
        if (
            map_id == PEWTER_GYM_MAP_ID
            and not self._pewter_gym_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("pewter_gym_entrance")
            )
        ):
            # Trigger when entering Pewter Gym for the first time
            self._trigger_photo_moment("pewter_gym_entrance")
            self._pewter_gym_photo_triggered = True

        # Indigo Plateau - Arriving at Pokemon League (map-entry based)
        if (
            map_id == INDIGO_PLATEAU_LOBBY_MAP_ID
            and not self._indigo_plateau_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("indigo_plateau")
            )
        ):
            # Trigger when arriving at the Pokemon League
            self._trigger_photo_moment("indigo_plateau")
            self._indigo_plateau_photo_triggered = True

        # Daycare Visit - First visit to Pokemon Daycare (map-entry based)
        if (
            map_id == DAYCARE_MAP_ID
            and not self._daycare_photo_triggered
            and not self._achievement_tracker.is_triggered(
                self._get_achievement_type("daycare_visit")
            )
        ):
            # Trigger when visiting the daycare
            self._trigger_photo_moment("daycare_visit")
            self._daycare_photo_triggered = True

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
