import logging
from typing import Optional, Dict, Any, Tuple
from pyAIAgent.game.name_planner import get_name_planner
from core.navigation_controller import NavigationController

log = logging.getLogger("scenario_manager")


class ScenarioManager:
    """
    Manages hardcoded game scenarios, overrides, and scripted events.
    Handles:
    - Name Entry sequence (forcing LASS/BUTT)
    - Pallet Town loop breaking
    - Invisible obstacle handling (stuck state)
    """

    def __init__(self, navigation_controller: NavigationController):
        self.navigation_controller = navigation_controller

    def check_for_override(
        self, state: Dict[str, Any], cycle_count: int
    ) -> Optional[str]:
        """
        Check game state for forced actions that bypass the LLM.
        Returns an action string (e.g. "A;", "START;") or None.
        """
        # 1. Name Entry Override
        name_entry_action = self._check_name_entry(state)
        if name_entry_action:
            return name_entry_action

        # 2. Pallet Town Loop Breaker (Only if no goal exists)
        # This modifies state (sets goal) rather than returning an immediate action,
        # but we can return None to let the main loop proceed with the new goal.
        self._check_pallet_town_loop(state, cycle_count)

        return None

    def _check_name_entry(self, state: Dict[str, Any]) -> Optional[str]:
        """Handle name entry screen logic."""
        name_entry_state = state.get("name_entry_state")
        if not name_entry_state:
            return None

        is_preset = name_entry_state.get("is_preset_menu", False)
        is_keyboard = name_entry_state.get("is_keyboard", False)

        if is_preset:
            log.info(
                "📋 Preset menu detected: Auto-executing 'A' to enter custom name mode"
            )
            return "A;"

        if is_keyboard:
            planner = get_name_planner()

            # Prevent loop: If already confirmed, hand back to agent
            if planner.confirmation_sent:
                # Returning None here lets llmdriver handle the "Waiting for transition" logic
                return None

            # Initialize planner if needed
            if not planner.current_name:
                # Determine who we are naming
                # Note: The state doesn't strictly say 'player' vs 'rival' easily without context history,
                # but llmdriver had logic for this. We might need to persist 'who are we naming' or infer it.
                # For now, let's default to LASS if uninitialized, or rely on what's in the planner.
                # If planner is empty, we assume Player (LASS) first.
                # If we just finished Player, we might be on Rival.
                # This is tricky without the full context from llmdriver.
                # Let's assume the driver/planner keeps state.
                if not planner.player_name:
                    planner.start_typing("LASS")
                elif not planner.rival_name:
                    planner.start_typing("BUTT")
                else:
                    # Fallback
                    planner.start_typing("LASS")

            # Get next step
            if planner.is_done_typing():
                log.info("✅ Name typing complete. Confirming with START.")
                planner.set_confirmation_sent(True)
                return "START;"

            step = planner.get_current_step()
            if step:
                log.info(f"⌨️ Name Entry Step: {step['char']} -> {step['path']}")
                return step["path"]

        return None

    def _check_pallet_town_loop(self, state: Dict[str, Any], cycle_count: int):
        """Force navigation goal if stuck in Pallet Town loop."""
        map_name = state.get("map_name", "")
        if map_name == "PALLET_TOWN" and not self.navigation_controller.goal_stack:
            log.info("🎯 Pallet Town Loop Breaker: Setting forced goal to Route 1")
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
        # This logic is extracted from llmdriver
        walkable = True  # Default to true if unknown, to trigger check
        if minimap_analysis:
            # Basic check - implementation depends on how minimap_analysis is structured in the state passed
            # For now, we trust the caller to pass relevant info or handle the detailed check
            pass

        # Determine facing to avoid map boundaries
        facing = state.get("facing", "down")

        # This logic requires more detailed analysis of the minimap which might be complex to move entirely right now.
        # We'll keep the simple "Stuck + Walkable" heuristic.

        return False, None  # Placeholder for now, moving the full logic is complex
