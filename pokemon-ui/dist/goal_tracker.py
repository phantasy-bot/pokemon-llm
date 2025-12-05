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
    """Goal priority levels"""
    CRITICAL = 1    # Must complete (heal at Pokemon Center when dying)
    HIGH = 2        # Main quest objective (beat next gym)
    MEDIUM = 3      # Current task (navigate to location)
    LOW = 4         # Optional (collect items, train)


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
    
    def __init__(self, storage_path: str = "game_goals.json"):
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
    
    def get_context_for_llm(self) -> str:
        """Generate compact goal context for LLM injection"""
        hierarchy = self.get_goal_hierarchy()
        if not hierarchy:
            return ""
        
        lines = ["🎯 GOALS:"]
        labels = ["MAIN", "CURRENT", "MICRO", "IMMEDIATE"]
        
        for i, goal in enumerate(hierarchy):
            label = labels[i] if i < len(labels) else f"#{i+1}"
            status_icon = "→" if goal.status == "in_progress" else "○"
            lines.append(f"  {status_icon} {label}: {goal.description}")
        
        # Add failure context if any
        failure_ctx = self.get_failure_context()
        if failure_ctx:
            lines.append(failure_ctx)
        
        return "\n".join(lines)
    
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
