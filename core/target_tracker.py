"""
Target Tracker for Pokemon LLM Agent.

Manages navigation targets that persist across cycles until reached.
Enables precise pathfinding by allowing the LLM to set explicit destinations
that are displayed as visual markers on the minimap.

Supports two levels of targeting:
1. MetaGoal - High-level destination that persists across maps (e.g., "Get to Route 1")
2. NavigationTarget - Specific tile target on current map (e.g., "Grid[3,3]")
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

log = logging.getLogger("target_tracker")


@dataclass
class MetaGoal:
    """High-level navigation objective that persists across maps."""
    destination_map: str  # Target map name (e.g., "ROUTE_1", "VIRIDIAN_CITY")
    reason: str  # Why we're going there (e.g., "Get Oak's Parcel from Viridian Mart")
    created_at: float = field(default_factory=time.time)
    cycles_active: int = 0
    maps_visited: List[str] = field(default_factory=list)  # Track journey
    
    def to_dict(self) -> dict:
        return {
            "destination_map": self.destination_map,
            "reason": self.reason,
            "created_at": self.created_at,
            "cycles_active": self.cycles_active,
            "maps_visited": self.maps_visited
        }


@dataclass
class NavigationTarget:
    """A navigation target destination on the current map."""
    # Grid coordinates (minimap viewport position)
    grid_x: int
    grid_y: int
    # World coordinates (absolute map position)
    world_x: int
    world_y: int
    # Map context
    map_id: int
    map_name: str
    # Reason for targeting this location
    reason: str
    # Timestamp when target was set
    created_at: float = field(default_factory=time.time)
    # Number of cycles this target has been active
    cycles_active: int = 0
    # Is this a waypoint toward a meta-goal?
    is_waypoint: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "world_x": self.world_x,
            "world_y": self.world_y,
            "map_id": self.map_id,
            "map_name": self.map_name,
            "reason": self.reason,
            "created_at": self.created_at,
            "cycles_active": self.cycles_active,
            "is_waypoint": self.is_waypoint
        }


class TargetTracker:
    """
    Manages navigation targets for the Pokemon LLM agent.
    
    Two-level targeting system:
    1. MetaGoal - Persists across maps (e.g., "Get to Route 1")
    2. NavigationTarget - Current map tile target (clears on map change)
    
    Targets/goals clear when:
    1. The destination is reached
    2. The LLM explicitly clears/changes the target
    3. Too many cycles pass without progress (abandoned)
    """
    
    # How close (in tiles) player must be to consider target reached
    REACH_TOLERANCE = 1
    # Maximum cycles before considering target stale/abandoned
    MAX_CYCLES_ACTIVE = 50
    # Maximum cycles for meta-goals
    MAX_META_CYCLES = 200
    
    def __init__(self):
        self._current_target: Optional[NavigationTarget] = None
        self._meta_goal: Optional[MetaGoal] = None
        self._target_history: List[dict] = []  # Recent targets for context
        self._last_distance: Optional[float] = None
        
    @property
    def has_target(self) -> bool:
        """Check if there's an active navigation target."""
        return self._current_target is not None
    
    @property
    def has_meta_goal(self) -> bool:
        """Check if there's an active high-level goal."""
        return self._meta_goal is not None
    
    @property
    def meta_goal(self) -> Optional[MetaGoal]:
        """Get the current meta-goal."""
        return self._meta_goal

    @property
    def current(self) -> Optional[NavigationTarget]:
        """Get the current navigation target."""
        return self._current_target
    
    def set_meta_goal(self, destination_map: str, reason: str) -> MetaGoal:
        """
        Set a high-level navigation goal that persists across maps.
        
        Args:
            destination_map: Target map name (e.g., "ROUTE_1", "VIRIDIAN_CITY")
            reason: Why we're going there
            
        Returns:
            The created MetaGoal
        """
        # Log if replacing existing goal
        if self._meta_goal:
            old_dest = self._meta_goal.destination_map
            log.info(f"🎯 META-GOAL REPLACED: {old_dest} → {destination_map}")
        
        self._meta_goal = MetaGoal(
            destination_map=destination_map,
            reason=reason
        )
        
        log.info(f"🎯 META-GOAL SET: {destination_map}")
        log.info(f"   Reason: {reason}")
        
        return self._meta_goal
    
    def clear_meta_goal(self, reason: str = "cleared") -> bool:
        """Clear the current meta-goal."""
        if not self._meta_goal:
            return False
        
        dest = self._meta_goal.destination_map
        log.info(f"🎯 META-GOAL CLEARED: {dest} - {reason}")
        self._meta_goal = None
        return True
    
    def check_meta_goal_reached(self, current_map_name: str) -> bool:
        """
        Check if we've reached the meta-goal destination map.
        
        Args:
            current_map_name: Current map name
            
        Returns:
            True if meta-goal reached and cleared
        """
        if not self._meta_goal:
            return False
        
        # Track visited maps
        if current_map_name and current_map_name not in self._meta_goal.maps_visited:
            self._meta_goal.maps_visited.append(current_map_name)
            log.info(f"🎯 META-GOAL PROGRESS: Now at {current_map_name}, heading to {self._meta_goal.destination_map}")
        
        # Check if destination reached (case-insensitive, partial match)
        dest = self._meta_goal.destination_map.upper().replace(" ", "_")
        current = current_map_name.upper().replace(" ", "_")
        
        if dest in current or current in dest:
            log.info(f"🎯 META-GOAL REACHED! Arrived at {current_map_name}")
            self.clear_meta_goal("reached")
            return True
        
        return False
    
    def get_meta_goal_progress(self, current_map_name: str) -> str:
        """
        Get a status string about meta-goal progress.
        
        Args:
            current_map_name: Current map name
            
        Returns:
            Progress description for LLM context
        """
        if not self._meta_goal:
            return ""
        
        dest = self._meta_goal.destination_map
        reason = self._meta_goal.reason
        visited = len(self._meta_goal.maps_visited)
        cycles = self._meta_goal.cycles_active
        
        # Check if current map is on path or detour
        path_status = "ON PATH" if self._is_on_path(current_map_name) else "⚠️ DETOUR - get back on track!"
        
        return (
            f"🎯 META-GOAL: {dest} ({reason})\n"
            f"   Status: {path_status}\n"
            f"   Maps visited: {visited} | Cycles: {cycles}/{self.MAX_META_CYCLES}\n"
            f"   Journey: {' → '.join(self._meta_goal.maps_visited[-5:]) if self._meta_goal.maps_visited else 'Just started'}"
        )
    
    def _is_on_path(self, current_map_name: str) -> bool:
        """Check if current map is reasonably on path to meta-goal."""
        if not self._meta_goal:
            return True
        
        # Common detour patterns
        detour_indicators = ["_HOUSE", "_HOME", "_MART", "_CENTER", "_1F", "_2F", "_B1F"]
        current_upper = current_map_name.upper()
        
        # If we're in a building, it's likely a detour unless it's our destination
        dest_upper = self._meta_goal.destination_map.upper()
        for indicator in detour_indicators:
            if indicator in current_upper and indicator not in dest_upper:
                return False
        
        return True
    
    def set_target(
        self,
        grid_x: int,
        grid_y: int,
        world_x: int,
        world_y: int,
        map_id: int,
        map_name: str,
        reason: str
    ) -> NavigationTarget:
        """
        Set a new navigation target.
        
        Args:
            grid_x, grid_y: Position in minimap grid coordinates
            world_x, world_y: Position in world/map coordinates
            map_id: Current map ID
            map_name: Human-readable map name
            reason: Why we're targeting this location
            
        Returns:
            The created NavigationTarget
        """
        # Archive previous target if exists
        if self._current_target:
            self._archive_target("replaced")
        
        self._current_target = NavigationTarget(
            grid_x=grid_x,
            grid_y=grid_y,
            world_x=world_x,
            world_y=world_y,
            map_id=map_id,
            map_name=map_name,
            reason=reason
        )
        
        self._last_distance = None
        
        log.info(f"🎯 TARGET SET: Grid[{grid_x},{grid_y}] World[{world_x},{world_y}] on {map_name}")
        log.info(f"   Reason: {reason}")
        
        return self._current_target
    
    def clear_target(self, reason: str = "cleared") -> bool:
        """
        Clear the current navigation target.
        
        Args:
            reason: Why the target was cleared (for logging/history)
            
        Returns:
            True if a target was cleared, False if no target existed
        """
        if not self._current_target:
            return False
        
        self._archive_target(reason)
        target_info = f"Grid[{self._current_target.grid_x},{self._current_target.grid_y}]"
        self._current_target = None
        self._last_distance = None
        
        log.info(f"🎯 TARGET CLEARED: {target_info} - {reason}")
        return True
    
    def _archive_target(self, outcome: str):
        """Archive target to history for context."""
        if self._current_target:
            archived = self._current_target.to_dict()
            archived["outcome"] = outcome
            archived["archived_at"] = time.time()
            self._target_history.append(archived)
            # Keep only recent history
            self._target_history = self._target_history[-10:]
    
    def check_reached(
        self,
        player_world_x: int,
        player_world_y: int,
        current_map_id: int
    ) -> bool:
        """
        Check if player has reached the target destination.
        
        Args:
            player_world_x, player_world_y: Player's current world coordinates
            current_map_id: Player's current map
            
        Returns:
            True if target reached and cleared, False otherwise
        """
        if not self._current_target:
            return False
        
        # Map changed - tile target is invalid, but meta-goal persists
        if current_map_id != self._current_target.map_id:
            old_map = self._current_target.map_name
            log.info(f"🎯 TILE TARGET CLEARED: Map changed from {old_map} (ID {self._current_target.map_id}) to new map (ID {current_map_id})")
            if self._meta_goal:
                log.info(f"   Meta-goal still active: {self._meta_goal.destination_map}")
                log.info(f"   → Set a new tile target on this map toward meta-goal!")
            self.clear_target("map_changed")
            return False
        
        # Calculate distance to target
        dx = abs(player_world_x - self._current_target.world_x)
        dy = abs(player_world_y - self._current_target.world_y)
        distance = max(dx, dy)  # Chebyshev distance (allows diagonal)
        
        # Track distance for progress detection
        self._last_distance = distance
        
        # Check if reached
        if distance <= self.REACH_TOLERANCE:
            log.info(f"🎯 TARGET REACHED! Player at [{player_world_x},{player_world_y}], "
                    f"target was [{self._current_target.world_x},{self._current_target.world_y}]")
            self.clear_target("reached")
            return True
        
        return False
    
    def increment_cycle(self) -> bool:
        """
        Increment the cycle counter for the current target.
        
        Returns:
            True if target is still valid, False if expired
        """
        if not self._current_target:
            return False
        
        self._current_target.cycles_active += 1
        
        # Check for stale target
        if self._current_target.cycles_active > self.MAX_CYCLES_ACTIVE:
            log.warning(f"🎯 Target expired after {self.MAX_CYCLES_ACTIVE} cycles without reaching")
            self.clear_target("expired")
            return False
        
        return True
    
    def get_llm_context(self, player_grid_x: int, player_grid_y: int) -> str:
        """
        Get formatted target info for LLM context.
        
        Args:
            player_grid_x, player_grid_y: Player's current grid position
            
        Returns:
            Formatted string describing current target status
        """
        if not self._current_target:
            return "🎯 NO ACTIVE TARGET - Set one with <target_destination>[x,y] reason: \"description\"</target_destination>"
        
        t = self._current_target
        
        # Calculate grid distance
        dx = t.grid_x - player_grid_x
        dy = t.grid_y - player_grid_y
        
        # Direction hints
        directions = []
        if dy < 0:
            directions.append(f"NORTH {abs(dy)} tiles")
        elif dy > 0:
            directions.append(f"SOUTH {abs(dy)} tiles")
        if dx > 0:
            directions.append(f"EAST {abs(dx)} tiles")
        elif dx < 0:
            directions.append(f"WEST {abs(dx)} tiles")
        
        direction_str = " + ".join(directions) if directions else "AT TARGET"
        
        return (
            f"🎯 ACTIVE TARGET: Grid[{t.grid_x},{t.grid_y}] - {t.reason}\n"
            f"   Direction: {direction_str}\n"
            f"   Cycles active: {t.cycles_active}/{self.MAX_CYCLES_ACTIVE}\n"
            f"   Move toward this target! Clear with <clear_target/> if no longer needed."
        )
    
    def get_full_navigation_context(self, player_grid_x: int, player_grid_y: int, current_map_name: str) -> str:
        """
        Get complete navigation context including both meta-goal and current target.
        
        This is the main method for providing target info to the LLM.
        
        Args:
            player_grid_x, player_grid_y: Player's current grid position
            current_map_name: Current map name
            
        Returns:
            Complete navigation context string for LLM
        """
        lines = ["═══════════════════════════════════════"]
        lines.append("🎯 NAVIGATION STATUS (ALWAYS SET A TARGET!)")
        lines.append("═══════════════════════════════════════")
        
        # Meta-goal status
        if self._meta_goal:
            meta_progress = self.get_meta_goal_progress(current_map_name)
            lines.append(meta_progress)
            lines.append("")
        else:
            lines.append("⚠️ NO META-GOAL SET!")
            lines.append("   Set one with: <meta_goal>MAP_NAME reason: \"why\"</meta_goal>")
            lines.append("   Example: <meta_goal>ROUTE_1 reason: \"Head to Viridian City\"</meta_goal>")
            lines.append("")
        
        # Current target status
        if self._current_target:
            target_ctx = self.get_llm_context(player_grid_x, player_grid_y)
            lines.append(target_ctx)
        else:
            lines.append("⚠️ NO TILE TARGET SET!")
            lines.append("   You MUST set a target for precise navigation!")
            lines.append("   Set with: <target_destination>[x,y] reason: \"why\"</target_destination>")
            lines.append("")
            lines.append("   Find an exit 'O' tile or path opening and target it!")
            lines.append("   If meta-goal set, target should move you toward that goal!")
        
        lines.append("")
        lines.append("💡 TARGET RULES:")
        lines.append("   1. ALWAYS have both a meta-goal (map) AND tile target active")
        lines.append("   2. If in wrong building/area, set target to EXIT and leave!")
        lines.append("   3. After reaching a target, immediately set a new one")
        lines.append("   4. Tile targets clear on map change - set new ones immediately!")
        
        return "\n".join(lines)
    
    def get_marker_for_overlay(self) -> Optional[dict]:
        """
        Get target as a marker dict for the minimap overlay.
        
        Returns:
            Dict with x, y, type='T', opacity=1.0, reason
            or None if no target
        """
        if not self._current_target:
            return None
        
        return {
            "x": self._current_target.grid_x,
            "y": self._current_target.grid_y,
            "type": "T",  # T for Target
            "opacity": 1.0,
            "reason": self._current_target.reason
        }
    
    def update_grid_position(
        self,
        player_world_x: int,
        player_world_y: int,
        player_grid_x: int,
        player_grid_y: int
    ):
        """
        Update target's grid position based on viewport shift.
        
        As the player moves, the minimap viewport shifts. The target's
        world position stays constant but its grid position changes.
        
        Args:
            player_world_x, player_world_y: Player's world coordinates
            player_grid_x, player_grid_y: Player's grid coordinates (usually center)
        """
        if not self._current_target:
            return
        
        # Calculate offset from player to target in world space
        world_dx = self._current_target.world_x - player_world_x
        world_dy = self._current_target.world_y - player_world_y
        
        # Apply same offset to grid position
        new_grid_x = player_grid_x + world_dx
        new_grid_y = player_grid_y + world_dy
        
        # Only update if changed
        if new_grid_x != self._current_target.grid_x or new_grid_y != self._current_target.grid_y:
            self._current_target.grid_x = new_grid_x
            self._current_target.grid_y = new_grid_y
            log.debug(f"🎯 Target grid position updated to [{new_grid_x},{new_grid_y}]")
