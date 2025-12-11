"""
Coordinate Tracker for Enhanced Navigation

Tracks player world coordinates over time to detect loops and measure progress
toward navigation targets. Persists to disk for run continuity.
"""

import json
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import Counter

log = logging.getLogger('coordinate_tracker')


@dataclass
class PositionRecord:
    """Record of player position at a cycle."""
    cycle: int
    x: int
    y: int
    map_name: str
    timestamp: str


@dataclass 
class NavigationTarget:
    """Target coordinate the agent is trying to reach."""
    x: int
    y: int
    map_name: str
    reason: str
    set_at_cycle: int
    set_at_time: str
    last_distance: Optional[float] = None
    cycles_without_progress: int = 0


class CoordinateTracker:
    """
    Tracks player world coordinates to detect loops and measure navigation progress.
    
    Key features:
    - Maintains history of last N positions
    - Detects when player visits same tile 3+ times in 10 cycles (loop)
    - Tracks distance to target coordinate to measure progress
    - Persists to disk for run continuity
    """
    
    def __init__(self, storage_path: str = "data/coordinate_history.json", 
                 max_history: int = 10, reset_on_start: bool = False):
        """
        Initialize the coordinate tracker.
        
        Args:
            storage_path: Path to JSON file for persistence
            max_history: Number of cycles to keep in history
            reset_on_start: Whether to clear history on initialization
        """
        self.storage_path = storage_path
        self.max_history = max_history
        
        # Position history (newest first)
        self.history: List[PositionRecord] = []
        
        # Current navigation target
        self.target: Optional[NavigationTarget] = None
        
        # Load from disk if not resetting
        if not reset_on_start and os.path.exists(storage_path):
            self._load()
            log.info(f"📍 Coordinate tracker loaded ({len(self.history)} positions, target: {self.target is not None})")
        else:
            log.info(f"📍 Coordinate tracker initialized (fresh start)")
    
    def _load(self) -> None:
        """Load state from disk."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            # Load history
            self.history = [
                PositionRecord(**rec) for rec in data.get("history", [])
            ]
            
            # Load target
            if data.get("target"):
                self.target = NavigationTarget(**data["target"])
            
        except Exception as e:
            log.error(f"Failed to load coordinate history: {e}")
            self.history = []
            self.target = None
    
    def _save(self) -> None:
        """Save state to disk."""
        try:
            data = {
                "history": [asdict(rec) for rec in self.history],
                "target": asdict(self.target) if self.target else None,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save coordinate history: {e}")
    
    def add_position(self, cycle: int, x: int, y: int, map_name: str) -> None:
        """
        Record current player position.
        
        Args:
            cycle: Current cycle number
            x: World X coordinate
            y: World Y coordinate  
            map_name: Current map name
        """
        record = PositionRecord(
            cycle=cycle,
            x=x,
            y=y,
            map_name=map_name,
            timestamp=datetime.now().isoformat()
        )
        
        # Add to front, trim to max
        self.history.insert(0, record)
        while len(self.history) > self.max_history:
            self.history.pop()
        
        # Update target progress if we have one
        if self.target and self.target.map_name == map_name:
            current_dist = self._calculate_distance(x, y, self.target.x, self.target.y)
            
            if self.target.last_distance is not None:
                if current_dist >= self.target.last_distance:
                    self.target.cycles_without_progress += 1
                else:
                    self.target.cycles_without_progress = 0
            
            self.target.last_distance = current_dist
        
        log.debug(f"📍 Position recorded: cycle {cycle} -> ({x}, {y}) on {map_name}")
        self._save()
    
    def _calculate_distance(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """Calculate Manhattan distance between two points."""
        return abs(x2 - x1) + abs(y2 - y1)
    
    def detect_loop(self) -> Optional[str]:
        """
        Detect if player is moving in circles.
        
        Returns description if loop detected (same tile 3+ times in history),
        None otherwise.
        """
        if len(self.history) < 3:
            return None
        
        # Count occurrences of each (map, x, y) tuple
        tile_counts = Counter(
            (rec.map_name, rec.x, rec.y) for rec in self.history
        )
        
        # Find any tiles visited 3+ times
        loops = [(tile, count) for tile, count in tile_counts.items() if count >= 3]
        
        if loops:
            # Sort by count, report worst loop
            loops.sort(key=lambda x: -x[1])
            (map_name, x, y), count = loops[0]
            return f"LOOP DETECTED: Visited ({x}, {y}) on {map_name} {count} times in last {len(self.history)} cycles"
        
        return None
    
    def get_progress_toward_target(self) -> Dict[str, Any]:
        """
        Get information about progress toward current target.
        
        Returns dict with:
        - has_target: bool
        - target_info: Target details if set
        - distance: Current distance to target
        - progress: "approaching", "stuck", "no_progress", or "wrong_map"
        - recommendation: What to do
        """
        if not self.target:
            return {
                "has_target": False,
                "recommendation": "Set a navigation target to track progress"
            }
        
        if not self.history:
            return {
                "has_target": True,
                "target_info": f"({self.target.x}, {self.target.y}) on {self.target.map_name}: {self.target.reason}",
                "recommendation": "Position data not yet available"
            }
        
        current = self.history[0]
        
        # Check if on wrong map
        if current.map_name != self.target.map_name:
            return {
                "has_target": True,
                "target_info": f"({self.target.x}, {self.target.y}) on {self.target.map_name}: {self.target.reason}",
                "progress": "wrong_map",
                "current_map": current.map_name,
                "target_map": self.target.map_name,
                "recommendation": f"Need to travel to {self.target.map_name} first"
            }
        
        distance = self._calculate_distance(current.x, current.y, self.target.x, self.target.y)
        
        # Determine progress status
        if self.target.cycles_without_progress >= 5:
            progress = "stuck"
            recommendation = f"STUCK for {self.target.cycles_without_progress} cycles. Consider invalidating target and trying a different route."
        elif self.target.cycles_without_progress >= 3:
            progress = "no_progress"
            recommendation = "Not making progress. Try going around obstacles or taking a different path."
        else:
            progress = "approaching"
            recommendation = f"Continue toward target ({distance} tiles away)"
        
        return {
            "has_target": True,
            "target_info": f"({self.target.x}, {self.target.y}) on {self.target.map_name}: {self.target.reason}",
            "distance": distance,
            "cycles_without_progress": self.target.cycles_without_progress,
            "progress": progress,
            "recommendation": recommendation
        }
    
    def set_target(self, x: int, y: int, map_name: str, reason: str, cycle: int) -> None:
        """
        Set a new navigation target.
        
        Args:
            x: Target X coordinate
            y: Target Y coordinate
            map_name: Target map name
            reason: Why we're going there
            cycle: Current cycle when target was set
        """
        self.target = NavigationTarget(
            x=x,
            y=y,
            map_name=map_name,
            reason=reason,
            set_at_cycle=cycle,
            set_at_time=datetime.now().isoformat(),
            last_distance=None,
            cycles_without_progress=0
        )
        log.info(f"🎯 Navigation target set: ({x}, {y}) on {map_name} - {reason}")
        self._save()
    
    def invalidate_target(self, reason: str) -> None:
        """
        Clear the current target when stuck or reached.
        
        Args:
            reason: Why the target is being invalidated
        """
        if self.target:
            log.info(f"❌ Target invalidated: {reason} (was: ({self.target.x}, {self.target.y}) on {self.target.map_name})")
        self.target = None
        self._save()
    
    def check_target_reached(self, threshold: int = 2) -> bool:
        """
        Check if we've reached the target (within threshold tiles).
        
        Returns True and invalidates target if reached.
        """
        if not self.target or not self.history:
            return False
        
        current = self.history[0]
        if current.map_name != self.target.map_name:
            return False
        
        distance = self._calculate_distance(
            current.x, current.y, 
            self.target.x, self.target.y
        )
        
        if distance <= threshold:
            log.info(f"✅ Target reached! Distance: {distance}")
            self.invalidate_target("Target reached")
            return True
        
        return False
    
    def get_context_summary(self) -> str:
        """
        Return formatted context string for LLM.
        
        Includes:
        - Recent position history
        - Loop detection results
        - Target progress info
        """
        lines = []
        
        # Position history
        if self.history:
            lines.append("COORDINATE HISTORY (last 10 cycles):")
            for rec in self.history[:10]:
                lines.append(f"  Cycle {rec.cycle}: ({rec.x}, {rec.y}) on {rec.map_name}")
        
        # Loop detection
        loop = self.detect_loop()
        if loop:
            lines.append(f"\n⚠️ {loop}")
        
        # Target progress
        progress = self.get_progress_toward_target()
        if progress.get("has_target"):
            lines.append(f"\n🎯 NAVIGATION TARGET: {progress['target_info']}")
            if "distance" in progress:
                lines.append(f"   Distance: {progress['distance']} tiles")
            lines.append(f"   Status: {progress.get('progress', 'unknown')}")
            lines.append(f"   {progress['recommendation']}")
        
        return "\n".join(lines)
    
    def get_position_at_cycle(self, cycle: int) -> Optional[Tuple[int, int, str]]:
        """Get position at a specific cycle if available."""
        for rec in self.history:
            if rec.cycle == cycle:
                return (rec.x, rec.y, rec.map_name)
        return None
