"""
Navigation Controller - Goal-Oriented Navigation System

Orchestrates navigation goals, pathfinding, and stuck detection for the Pokemon LLM agent.
Integrates with:
- CoordinateTracker for position history and loop detection
- MapVisitTracker for oscillation detection  
- MemoryManager for stuck detection and exit memory
- BFS pathfinding from pyAIAgent/navigation.py

Key features:
- Goal stack: Maintains primary and sub-goals that persist across cycles
- Auto-path computation: Computes BFS path when goal is set
- Stuck recovery: Suggests alternatives when stuck
- Navigation context injection: Formats context for LLM prompts
"""

import logging
import os
import json
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import deque
from enum import Enum

from trackers.coordinate_tracker import CoordinateTracker
from core.memory.manager import MemoryManager, MapVisitTracker

# Try to import BFS pathfinding (optional - works without it)
try:
    from pyAIAgent.navigation import find_path, get_rom_path
    HAS_PATHFINDING = True
except ImportError:
    HAS_PATHFINDING = False

log = logging.getLogger('navigation_controller')


class GoalType(Enum):
    """Types of navigation goals."""
    EXIT = "exit"              # Navigate to a specific exit
    COORDINATE = "coordinate"  # Navigate to a specific coordinate
    EXPLORE = "explore"        # Explore unexplored areas
    NPC = "npc"               # Interact with an NPC
    ITEM = "item"             # Pick up an item


@dataclass
class NavigationGoal:
    """A navigation goal with target and metadata."""
    goal_type: GoalType
    target_x: int
    target_y: int
    map_name: str
    map_id: int
    reason: str
    created_at: str
    cycles_active: int = 0
    computed_path: Optional[str] = None  # BFS path as action string
    path_computed_at: Optional[int] = None  # Cycle when path was computed
    failed_attempts: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        d = asdict(self)
        d['goal_type'] = self.goal_type.value
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> 'NavigationGoal':
        """Create from dictionary."""
        d['goal_type'] = GoalType(d['goal_type'])
        return cls(**d)


@dataclass
class NavigationState:
    """Current navigation state summary."""
    has_goal: bool
    goal_description: str
    path_available: bool
    next_moves: Optional[str]  # Next 2-5 moves from computed path
    distance_to_goal: Optional[int]
    stuck_status: str  # "ok", "slow_progress", "stuck", "oscillating"
    suggestion: str


class NavigationController:
    """
    Goal-oriented navigation controller.
    
    Maintains navigation goals across cycles, computes paths, and provides
    navigation context for LLM injection.
    """
    
    STUCK_THRESHOLD = 5  # Cycles without progress before considered stuck
    MAX_GOAL_CYCLES = 50  # Max cycles before goal is considered stale
    PATH_RECOMPUTE_INTERVAL = 10  # Cycles between path recomputation
    
    def __init__(
        self, 
        coord_tracker: CoordinateTracker,
        memory_manager: MemoryManager,
        map_visit_tracker: MapVisitTracker,
        storage_path: str = "data/navigation_state.json",
        reset_on_start: bool = False
    ):
        """
        Initialize the navigation controller.
        
        Args:
            coord_tracker: CoordinateTracker for position history
            memory_manager: MemoryManager for stuck detection and exit memory
            map_visit_tracker: MapVisitTracker for oscillation detection
            storage_path: Path to persist navigation state
            reset_on_start: Whether to clear state on initialization
        """
        self.coord_tracker = coord_tracker
        self.memory_manager = memory_manager
        self.map_visit_tracker = map_visit_tracker
        self.storage_path = storage_path
        
        # Goal stack - primary goal and sub-goals
        self.goal_stack: List[NavigationGoal] = []
        
        # Position tracking for local stuck detection
        self.recent_positions: deque = deque(maxlen=10)
        self.cycles_at_same_position: int = 0
        
        # ROM path for pathfinding
        self.rom_path = get_rom_path() if HAS_PATHFINDING else None
        
        # Load or reset
        if not reset_on_start and os.path.exists(storage_path):
            self._load()
            log.info(f"🧭 Navigation controller loaded ({len(self.goal_stack)} goals)")
        else:
            log.info("🧭 Navigation controller initialized (fresh start)")
    
    def _load(self) -> None:
        """Load state from disk."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            self.goal_stack = [
                NavigationGoal.from_dict(g) for g in data.get("goal_stack", [])
            ]
            
        except Exception as e:
            log.error(f"Failed to load navigation state: {e}")
            self.goal_stack = []
    
    def _save(self) -> None:
        """Save state to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                "goal_stack": [g.to_dict() for g in self.goal_stack],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save navigation state: {e}")
    
    def set_goal(
        self, 
        goal_type: GoalType,
        target_x: int, 
        target_y: int, 
        map_name: str,
        map_id: int,
        reason: str,
        current_cycle: int,
        compute_path: bool = True
    ) -> NavigationGoal:
        """
        Set a new navigation goal.
        
        Args:
            goal_type: Type of goal
            target_x: Target X coordinate
            target_y: Target Y coordinate
            map_name: Target map name
            map_id: Target map ID
            reason: Why we're navigating there
            current_cycle: Current cycle number
            compute_path: Whether to compute BFS path immediately
        
        Returns:
            The created NavigationGoal
        """
        goal = NavigationGoal(
            goal_type=goal_type,
            target_x=target_x,
            target_y=target_y,
            map_name=map_name,
            map_id=map_id,
            reason=reason,
            created_at=datetime.now().isoformat(),
            cycles_active=0
        )
        
        # Clear existing goals of same type on same map (replace them)
        self.goal_stack = [
            g for g in self.goal_stack 
            if not (g.map_name == map_name and g.goal_type == goal_type)
        ]
        
        # Add to front of stack (highest priority)
        self.goal_stack.insert(0, goal)
        
        log.info(f"🎯 Navigation goal set: {goal_type.value} -> ({target_x}, {target_y}) on {map_name}: {reason}")
        
        # Compute path if requested
        if compute_path and HAS_PATHFINDING:
            self._compute_path_for_goal(goal, map_id, current_cycle)
        
        self._save()
        return goal
    
    def _compute_path_for_goal(
        self, 
        goal: NavigationGoal, 
        current_map_id: int,
        current_cycle: int,
        current_pos: Optional[Tuple[int, int]] = None
    ) -> Optional[str]:
        """
        Compute BFS path to goal.
        
        Returns action string (e.g., "R;R;D;D;") or None if no path.
        """
        if not HAS_PATHFINDING:
            log.warning("Pathfinding not available (pyAIAgent.navigation not loaded)")
            return None
        
        if goal.map_id != current_map_id:
            log.debug(f"Cannot compute path: goal on different map (goal: {goal.map_id}, current: {current_map_id})")
            return None
        
        # Get current position from coord_tracker if not provided
        if current_pos is None:
            if self.coord_tracker.history:
                latest = self.coord_tracker.history[0]
                current_pos = (latest.x, latest.y)
            else:
                log.warning("Cannot compute path: no current position available")
                return None
        
        try:
            path = find_path(
                self.rom_path,
                current_map_id,
                list(current_pos),
                [goal.target_x, goal.target_y]
            )
            
            if path:
                goal.computed_path = path
                goal.path_computed_at = current_cycle
                log.info(f"🛤️ Path computed: {path[:30]}... ({len(path.split(';'))-1} moves)")
            else:
                log.warning(f"No path found to ({goal.target_x}, {goal.target_y})")
            
            return path
            
        except Exception as e:
            log.error(f"Path computation failed: {e}")
            return None
    
    def update(
        self, 
        current_cycle: int,
        current_pos: Tuple[int, int],
        current_map_name: str,
        current_map_id: int,
        position_history: List[Tuple[str, Tuple[int, int]]]
    ) -> NavigationState:
        """
        Update navigation state for this cycle.
        
        Called each cycle with current position. Updates goal progress,
        detects stuck state, and recomputes paths as needed.
        
        Args:
            current_cycle: Current cycle number
            current_pos: Current (x, y) position
            current_map_name: Current map name
            current_map_id: Current map ID
            position_history: Recent position history for stuck detection
        
        Returns:
            NavigationState with current status and suggestions
        """
        # Track position for local stuck detection
        self.recent_positions.append((current_map_name, current_pos))
        
        # Check for position stuckness
        if len(self.recent_positions) >= 3:
            last_three = list(self.recent_positions)[-3:]
            if all(pos == last_three[0] for pos in last_three):
                self.cycles_at_same_position += 1
            else:
                self.cycles_at_same_position = 0
        
        # Update active goals
        for goal in self.goal_stack:
            goal.cycles_active += 1
        
        # Prune stale goals
        self.goal_stack = [
            g for g in self.goal_stack 
            if g.cycles_active < self.MAX_GOAL_CYCLES
        ]
        
        # Get current goal (if any)
        current_goal = self._get_active_goal(current_map_name)
        
        if not current_goal:
            # No goal - suggest exploration
            return NavigationState(
                has_goal=False,
                goal_description="No navigation goal set",
                path_available=False,
                next_moves=None,
                distance_to_goal=None,
                stuck_status=self._get_stuck_status(position_history),
                suggestion="Consider setting a navigation target (exit, NPC, or unexplored area)"
            )
        
        # Check if goal reached
        distance = abs(current_pos[0] - current_goal.target_x) + abs(current_pos[1] - current_goal.target_y)
        
        if distance <= 1:
            log.info(f"✅ Goal reached: {current_goal.reason}")
            self.goal_stack.remove(current_goal)
            self._save()
            return NavigationState(
                has_goal=False,
                goal_description=f"Goal reached: {current_goal.reason}",
                path_available=False,
                next_moves=None,
                distance_to_goal=0,
                stuck_status="ok",
                suggestion="Goal reached! Set a new navigation target."
            )
        
        # Recompute path if needed
        should_recompute = (
            current_goal.computed_path is None or 
            (current_goal.path_computed_at and 
             current_cycle - current_goal.path_computed_at >= self.PATH_RECOMPUTE_INTERVAL)
        )
        
        if should_recompute and HAS_PATHFINDING:
            self._compute_path_for_goal(
                current_goal, 
                current_map_id, 
                current_cycle,
                current_pos
            )
        
        # Get next moves from path
        next_moves = self._get_next_moves(current_goal.computed_path, num_moves=4)
        
        # Determine stuck status
        stuck_status = self._get_stuck_status(position_history)
        
        # Generate suggestion
        suggestion = self._generate_suggestion(
            current_goal, 
            distance, 
            stuck_status, 
            next_moves
        )
        
        self._save()
        
        return NavigationState(
            has_goal=True,
            goal_description=f"{current_goal.goal_type.value}: {current_goal.reason}",
            path_available=current_goal.computed_path is not None,
            next_moves=next_moves,
            distance_to_goal=distance,
            stuck_status=stuck_status,
            suggestion=suggestion
        )
    
    def _get_active_goal(self, current_map_name: str) -> Optional[NavigationGoal]:
        """Get the active goal for current map (or cross-map goal)."""
        for goal in self.goal_stack:
            if goal.map_name == current_map_name:
                return goal
        
        # If no same-map goal, return first goal (cross-map navigation)
        return self.goal_stack[0] if self.goal_stack else None
    
    def _get_stuck_status(self, position_history: List[Tuple[str, Tuple[int, int]]]) -> str:
        """Determine stuck status from position history."""
        # Check local stuck detector
        if self.cycles_at_same_position >= 5:
            return "stuck"
        elif self.cycles_at_same_position >= 3:
            return "slow_progress"
        
        # Check memory manager's stuck detection
        stuck_info = self.memory_manager.detect_stuck(position_history)
        if stuck_info.get("is_stuck"):
            return "stuck"
        
        # Check for oscillation
        oscillation = self.map_visit_tracker.detect_oscillation()
        if oscillation:
            return "oscillating"
        
        return "ok"
    
    def _get_next_moves(self, path: Optional[str], num_moves: int = 4) -> Optional[str]:
        """Extract next N moves from computed path."""
        if not path:
            return None
        
        moves = path.rstrip(';').split(';')
        if not moves:
            return None
        
        return ';'.join(moves[:num_moves]) + ';'
    
    def _generate_suggestion(
        self, 
        goal: NavigationGoal, 
        distance: int,
        stuck_status: str,
        next_moves: Optional[str]
    ) -> str:
        """Generate navigation suggestion based on current state."""
        
        if stuck_status == "stuck":
            goal.failed_attempts += 1
            if goal.failed_attempts >= 3:
                return f"STUCK for {self.cycles_at_same_position}+ cycles trying to reach {goal.reason}. Consider abandoning this goal and trying a different route or target."
            else:
                return f"STUCK! Can't make progress toward {goal.reason}. Try pressing A to interact, or move in a different direction first."
        
        elif stuck_status == "oscillating":
            return f"MAP LOOP DETECTED! You keep entering and leaving maps. Focus on your goal: {goal.reason}"
        
        elif stuck_status == "slow_progress":
            return f"Making slow progress toward {goal.reason}. Check if you're blocked and try an alternate path."
        
        # Normal progress
        if next_moves:
            return f"FOLLOW PATH: {next_moves} ({distance} tiles to goal)"
        else:
            # No computed path - give direction hint
            return f"Navigate toward ({goal.target_x}, {goal.target_y}) - {distance} tiles away"
    
    def get_context_for_llm(self, current_map_name: str) -> str:
        """
        Generate navigation context string for LLM injection.
        
        Returns formatted context about current goal, path, and suggestions.
        """
        current_goal = self._get_active_goal(current_map_name)
        
        if not current_goal:
            return ""
        
        lines = [
            "═══════════════════════════════════════",
            "🧭 NAVIGATION GOAL",
            "═══════════════════════════════════════",
            f"TARGET: ({current_goal.target_x}, {current_goal.target_y}) on {current_goal.map_name}",
            f"REASON: {current_goal.reason}",
        ]
        
        if current_goal.computed_path:
            next_moves = self._get_next_moves(current_goal.computed_path, num_moves=5)
            lines.append(f"COMPUTED PATH: {next_moves}")
            lines.append(f"FOLLOW THIS PATH for reliable navigation!")
        
        lines.append(f"CYCLES ACTIVE: {current_goal.cycles_active}")
        
        if current_goal.failed_attempts > 0:
            lines.append(f"⚠️ FAILED ATTEMPTS: {current_goal.failed_attempts}")
        
        lines.append("═══════════════════════════════════════")
        
        return "\n".join(lines)
    
    def set_exit_goal(
        self, 
        exit_coords: Tuple[int, int],
        map_name: str,
        map_id: int,
        destination: str,
        current_cycle: int
    ) -> NavigationGoal:
        """
        Convenience method to set a goal to reach an exit tile.
        
        Args:
            exit_coords: (x, y) of exit tile
            map_name: Current map name
            map_id: Current map ID
            destination: Where the exit leads to
            current_cycle: Current cycle number
        """
        return self.set_goal(
            goal_type=GoalType.EXIT,
            target_x=exit_coords[0],
            target_y=exit_coords[1],
            map_name=map_name,
            map_id=map_id,
            reason=f"Exit to {destination}",
            current_cycle=current_cycle
        )
    
    def clear_goals(self, map_name: Optional[str] = None) -> int:
        """
        Clear navigation goals.
        
        Args:
            map_name: If provided, only clear goals for this map.
                     If None, clear all goals.
        
        Returns:
            Number of goals cleared.
        """
        if map_name:
            original_count = len(self.goal_stack)
            self.goal_stack = [g for g in self.goal_stack if g.map_name != map_name]
            cleared = original_count - len(self.goal_stack)
        else:
            cleared = len(self.goal_stack)
            self.goal_stack = []
        
        if cleared > 0:
            log.info(f"🗑️ Cleared {cleared} navigation goal(s)")
            self._save()
        
        return cleared
    
    def record_goal_failure(self, reason: str) -> None:
        """
        Record that the current goal failed.
        
        This increases failed_attempts and may trigger goal abandonment suggestions.
        """
        if self.goal_stack:
            self.goal_stack[0].failed_attempts += 1
            log.warning(f"❌ Goal failure recorded: {reason} (attempts: {self.goal_stack[0].failed_attempts})")
            self._save()
