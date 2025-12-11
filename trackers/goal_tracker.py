"""
Goal Tracker Module for Pokemon LLM

Implements hierarchical goal stack that persists across summaries.
Provides structured goal context for LLM decision making.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json
import os


class GoalPriority(Enum):
    """
    Goal priority levels - QUESTS are PRIMARY, healing is SECONDARY
    
    Priority Order:
    1. CRITICAL - Main story quests (deliver Oak's Parcel, beat Gyms)
    2. HIGH - Quest item objectives (pick up items, find NPCs)
    3. MEDIUM - Urgent needs (heal at Pokemon Center when low HP)
    4. LOW - Optional (extra exploration, training)
    """
    CRITICAL = 1    # Main story quests (Oak's Parcel delivery, Gym battles)
    HIGH = 2        # Quest-related tasks (go to target location)
    MEDIUM = 3      # Urgent but not quest-critical (healing when HP < 30%)
    LOW = 4         # Optional (explore, train, catch Pokemon)


class GoalStatus(Enum):
    """Goal completion status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Goal:
    """A single goal with priority and status"""
    id: str
    description: str
    priority: int  # 1-4 from GoalPriority
    status: str = "pending"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    parent_id: Optional[str] = None  # For sub-goals
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Goal':
        return cls(**data)


class GoalTracker:
    """
    Manages hierarchical goal stack for Pokemon gameplay.
    
    Goal hierarchy:
    - Main Quest: Beat the Elite Four
      - Milestone: Get 8 badges
        - Current: Beat Pewter Gym
          - Micro: Navigate to Pewter City
            - Immediate: Exit current building
    """
    
    def __init__(self, storage_path: str = "data/game_goals.json"):
        self.storage_path = storage_path
        self.goals: Dict[str, Goal] = {}
        self.goal_stack: List[str] = []  # IDs in priority order
        self.failure_history: List[Dict] = []  # Recent failures for replay
        self._load()
    
    def add_goal(
        self, 
        description: str, 
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> str:
        """Add a new goal to the tracker"""
        goal_id = f"goal_{len(self.goals) + 1}_{int(datetime.now().timestamp())}"
        
        goal = Goal(
            id=goal_id,
            description=description,
            priority=priority.value,
            parent_id=parent_id,
            context=context or {}
        )
        
        self.goals[goal_id] = goal
        self._update_stack()
        self._save()
        
        return goal_id
    
    def update_goal(self, goal_id: str, status: GoalStatus) -> bool:
        """Update goal status"""
        if goal_id not in self.goals:
            return False
        
        self.goals[goal_id].status = status.value
        if status == GoalStatus.COMPLETED:
            self.goals[goal_id].completed_at = datetime.now().isoformat()
        
        self._update_stack()
        self._save()
        return True
    
    def complete_goal(self, goal_id: str) -> bool:
        """Mark a goal as completed"""
        return self.update_goal(goal_id, GoalStatus.COMPLETED)
    
    def fail_goal(self, goal_id: str, reason: str = "") -> bool:
        """Mark a goal as failed and record for replay"""
        if goal_id not in self.goals:
            return False
        
        goal = self.goals[goal_id]
        self.failure_history.append({
            "goal": goal.description,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only last 5 failures
        self.failure_history = self.failure_history[-5:]
        
        return self.update_goal(goal_id, GoalStatus.FAILED)
    
    def get_current_goal(self) -> Optional[Goal]:
        """Get the highest priority active goal"""
        for goal_id in self.goal_stack:
            goal = self.goals.get(goal_id)
            if goal and goal.status in ["pending", "in_progress"]:
                return goal
        return None
    
    def get_goal_hierarchy(self) -> List[Goal]:
        """Get goals from highest to lowest priority (main quest → micro)"""
        hierarchy = []
        for goal_id in self.goal_stack:
            goal = self.goals.get(goal_id)
            if goal and goal.status in ["pending", "in_progress"]:
                hierarchy.append(goal)
        # Sort by priority (1=critical first)
        return sorted(hierarchy, key=lambda g: g.priority)[:4]
    
    def record_failure(self, action: str, position: tuple, reason: str):
        """Record a failed action for replay context"""
        self.failure_history.append({
            "action": action,
            "position": position,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        self.failure_history = self.failure_history[-5:]
        self._save()
    
    def get_failure_context(self) -> str:
        """Get recent failures as context for LLM"""
        if not self.failure_history:
            return ""
        
        lines = ["⚠️ RECENT FAILURES (don't repeat these):"]
        for i, failure in enumerate(self.failure_history[-3:], 1):
            if "goal" in failure:
                lines.append(f"  {i}. Goal failed: {failure['goal']} - {failure.get('reason', 'unknown')}")
            else:
                lines.append(f"  {i}. Action '{failure['action']}' failed at {failure.get('position', '?')} - {failure.get('reason', 'unknown')}")
        
        return "\n".join(lines)
    
    def get_context_for_llm(self, team_size: int = 0, team_pokemon: list = None) -> str:
        """Generate compact goal context for LLM injection with progress tracking"""
        lines = ["🎯 GOAL STATUS:"]
        
        # Show team status first - this is critical for progress awareness
        if team_size > 0:
            pokemon_names = ", ".join(team_pokemon[:3]) if team_pokemon else "your Pokemon"
            lines.append(f"  ✓ OBTAINED STARTER: You have {team_size} Pokemon ({pokemon_names})")
            lines.append(f"  → The 'get first Pokemon' objective is COMPLETE - do NOT repeat it!")
        else:
            lines.append(f"  ○ NO POKEMON YET: You need to get your starter from Professor Oak")
        
        # Show recently completed goals (helps LLM remember progress)
        completed = self.get_completed_goals(limit=3)
        if completed:
            lines.append("  📋 COMPLETED:")
            for goal in completed:
                lines.append(f"    ✓ {goal.description}")
        
        # Show active goals hierarchy
        hierarchy = self.get_goal_hierarchy()
        if hierarchy:
            lines.append("  📍 ACTIVE GOALS:")
            labels = ["MAIN", "CURRENT", "MICRO", "IMMEDIATE"]
            for i, goal in enumerate(hierarchy):
                label = labels[i] if i < len(labels) else f"#{i+1}"
                status_icon = "→" if goal.status == "in_progress" else "○"
                lines.append(f"    {status_icon} {label}: {goal.description}")
        
        # Add failure context if any
        failure_ctx = self.get_failure_context()
        if failure_ctx:
            lines.append(failure_ctx)
        
        return "\n".join(lines)
    
    def get_completed_goals(self, limit: int = 5) -> List[Goal]:
        """Get recently completed goals"""
        completed = [
            g for g in self.goals.values() 
            if g.status == "completed"
        ]
        # Sort by completion time, most recent first
        completed.sort(key=lambda g: g.completed_at or "", reverse=True)
        return completed[:limit]
    
    def complete_goal_by_keyword(self, keyword: str) -> bool:
        """Find and complete a goal containing the keyword"""
        for goal_id, goal in self.goals.items():
            if keyword.lower() in goal.description.lower() and goal.status != "completed":
                self.complete_goal(goal_id)
                return True
        return False
    
    def add_quest_goal(
        self,
        quest_id: str,
        description: str,
        target_location: Optional[str] = None,
        target_npc: Optional[str] = None,
        priority: GoalPriority = GoalPriority.CRITICAL  # Quests are CRITICAL priority
    ) -> Optional[str]:
        """
        Add a goal derived from a quest item pickup.
        
        Quest goals are CRITICAL priority because the game's story progression
        depends on completing them. Healing can wait, but the Parcel must be delivered.
        """
        # Check if we already have a goal for this quest
        for goal in self.goals.values():
            if goal.context.get("quest_id") == quest_id and goal.status != "completed":
                return goal.id  # Already have this quest goal
        
        context = {
            "type": "quest",
            "quest_id": quest_id,
            "target_location": target_location,
            "target_npc": target_npc
        }
        
        # Get main quest ID as parent
        main_quest_id = self._get_main_quest_id()
        
        return self.add_goal(
            description=description,
            priority=priority,
            parent_id=main_quest_id,
            context=context
        )
    
    def _get_main_quest_id(self) -> Optional[str]:
        """Get the main quest goal ID."""
        for goal_id, goal in self.goals.items():
            if goal.context.get("type") == "main_quest":
                return goal_id
        return None
    
    def has_quest_goal(self, quest_id: str) -> bool:
        """Check if we already have an active goal for this quest."""
        for goal in self.goals.values():
            if (goal.context.get("quest_id") == quest_id and 
                goal.status in ["pending", "in_progress"]):
                return True
        return False

    def initialize_default_goals(self):
        """Set up initial game goals"""
        # Main quest
        main_id = self.add_goal(
            "Complete Pokemon Red - Become Champion",
            GoalPriority.LOW,
            context={"type": "main_quest"}
        )
        
        # Current milestone
        self.add_goal(
            "Get first Pokemon and start journey",
            GoalPriority.HIGH,
            parent_id=main_id,
            context={"type": "milestone"}
        )
    
    def _update_stack(self):
        """Rebuild priority stack"""
        active = [
            g for g in self.goals.values() 
            if g.status in ["pending", "in_progress"]
        ]
        # Sort by priority (lower number = higher priority)
        active.sort(key=lambda g: g.priority)
        self.goal_stack = [g.id for g in active]
    
    def _save(self):
        """Save goals to file"""
        try:
            data = {
                "goals": {gid: g.to_dict() for gid, g in self.goals.items()},
                "stack": self.goal_stack,
                "failures": self.failure_history
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving goals: {e}")
    
    def _load(self):
        """Load goals from file"""
        if not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            self.goals = {
                gid: Goal.from_dict(gdata) 
                for gid, gdata in data.get("goals", {}).items()
            }
            self.goal_stack = data.get("stack", [])
            self.failure_history = data.get("failures", [])
        except Exception as e:
            print(f"Error loading goals: {e}")
