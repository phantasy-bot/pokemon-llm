"""
Exploration Tracking System for Pokemon LLM Agent

Tracks visited tiles per map to enable systematic exploration
and avoid repetitive navigation patterns.
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime

log = logging.getLogger("exploration_tracker")


@dataclass
class MapExploration:
    """Tracks exploration state for a single map."""
    map_id: int
    map_name: str
    visited_tiles: Set[Tuple[int, int]] = field(default_factory=set)
    total_walkable: int = 0
    last_visited: str = ""
    
    @property
    def exploration_pct(self) -> float:
        """Percentage of walkable tiles that have been visited."""
        if self.total_walkable == 0:
            return 0.0
        return (len(self.visited_tiles) / self.total_walkable) * 100
    
    def to_dict(self) -> dict:
        """Serialize for JSON storage."""
        return {
            "map_id": self.map_id,
            "map_name": self.map_name,
            "visited_tiles": list(self.visited_tiles),  # Convert set to list for JSON
            "total_walkable": self.total_walkable,
            "last_visited": self.last_visited
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MapExploration":
        """Deserialize from JSON storage."""
        return cls(
            map_id=data["map_id"],
            map_name=data["map_name"],
            visited_tiles=set(tuple(t) for t in data.get("visited_tiles", [])),
            total_walkable=data.get("total_walkable", 0),
            last_visited=data.get("last_visited", "")
        )


class ExplorationTracker:
    """
    Tracks which tiles have been visited on each map.
    
    Enables the agent to:
    1. Know what % of a map has been explored
    2. Find unexplored areas to prioritize
    3. Suggest next exploration targets
    """
    
    def __init__(self, storage_path: str = "data/exploration_data.json", reset_on_start: bool = False):
        self.storage_path = storage_path
        self.maps: Dict[int, MapExploration] = {}  # map_id -> MapExploration
        
        if reset_on_start:
            self._save()
            log.info("🗺️ Exploration tracker reset for fresh start")
        else:
            self._load()
            log.info(f"🗺️ Exploration tracker loaded: {len(self.maps)} maps tracked")
    
    def record_visit(self, map_id: int, map_name: str, x: int, y: int, 
                     total_walkable: int = 0) -> None:
        """
        Record that a tile has been visited.
        
        Args:
            map_id: Game map ID
            map_name: Human-readable map name
            x, y: Tile coordinates
            total_walkable: Total walkable tiles on this map (optional, for % calc)
        """
        if map_id not in self.maps:
            self.maps[map_id] = MapExploration(
                map_id=map_id,
                map_name=map_name,
                total_walkable=total_walkable
            )
        
        exploration = self.maps[map_id]
        exploration.visited_tiles.add((x, y))
        exploration.last_visited = datetime.now().isoformat()
        
        # Update total walkable if provided and larger
        if total_walkable > exploration.total_walkable:
            exploration.total_walkable = total_walkable
        
        # Auto-save periodically (every 10 visits)
        if len(exploration.visited_tiles) % 10 == 0:
            self._save()
    
    def get_exploration_summary(self, map_id: int) -> str:
        """
        Get a human-readable exploration summary for a map.
        
        Returns:
            e.g., "PALLET_TOWN: 45% explored (18/40 tiles)"
        """
        if map_id not in self.maps:
            return "Map not yet explored"
        
        exp = self.maps[map_id]
        visited = len(exp.visited_tiles)
        
        if exp.total_walkable > 0:
            return f"{exp.map_name}: {exp.exploration_pct:.0f}% explored ({visited}/{exp.total_walkable} tiles)"
        else:
            return f"{exp.map_name}: {visited} tiles visited"
    
    def get_unexplored_directions(self, map_id: int, player_x: int, player_y: int,
                                   minimap_2d: str) -> List[str]:
        """
        Analyze minimap to find directions with unexplored walkable tiles.
        
        Args:
            map_id: Current map
            player_x, player_y: Player position (in minimap center coords)
            minimap_2d: Semicolon-separated minimap string
        
        Returns:
            List of directions with unexplored tiles, e.g., ["EAST", "NORTH"]
        """
        if not minimap_2d:
            return []
        
        # Parse minimap
        rows = minimap_2d.split(";")
        if not rows:
            return []
        
        grid_size = len(rows)
        center = grid_size // 2  # Player is at center
        
        # Get visited tiles for this map
        visited = self.maps.get(map_id, MapExploration(map_id, "")).visited_tiles
        
        # Check each quadrant for unexplored walkable tiles
        unexplored_dirs = []
        
        # Define quadrant bounds (relative to center)
        quadrants = {
            "NORTH": (0, center, 0, grid_size),           # Top half
            "SOUTH": (center, grid_size, 0, grid_size),   # Bottom half
            "WEST": (0, grid_size, 0, center),            # Left half
            "EAST": (0, grid_size, center, grid_size),    # Right half
        }
        
        for direction, (row_start, row_end, col_start, col_end) in quadrants.items():
            unexplored_count = 0
            
            for row_idx in range(row_start, min(row_end, len(rows))):
                row = rows[row_idx]
                for col_idx in range(col_start, min(col_end, len(row))):
                    tile = row[col_idx]
                    # Walkable or special tiles that aren't visited
                    if tile in ['W', 'O']:
                        # Convert minimap coords to world coords (rough estimate)
                        world_x = player_x + (col_idx - center)
                        world_y = player_y + (row_idx - center)
                        
                        if (world_x, world_y) not in visited:
                            unexplored_count += 1
            
            if unexplored_count > 3:  # Threshold to consider direction worth exploring
                unexplored_dirs.append(f"{direction} ({unexplored_count} unexplored)")
        
        return unexplored_dirs
    
    def suggest_exploration_target(self, map_id: int, player_x: int, player_y: int,
                                    minimap_2d: str) -> Optional[Tuple[int, int]]:
        """
        Suggest the nearest unexplored tile to explore.
        
        Returns:
            (x, y) coordinates of suggested target, or None if fully explored
        """
        if not minimap_2d:
            return None
        
        rows = minimap_2d.split(";")
        if not rows:
            return None
        
        grid_size = len(rows)
        center = grid_size // 2
        
        visited = self.maps.get(map_id, MapExploration(map_id, "")).visited_tiles
        
        # Find nearest unexplored walkable tile (BFS-like expanding search)
        for distance in range(1, center + 1):
            for dy in range(-distance, distance + 1):
                for dx in range(-distance, distance + 1):
                    if abs(dx) != distance and abs(dy) != distance:
                        continue  # Only check perimeter of current distance
                    
                    row_idx = center + dy
                    col_idx = center + dx
                    
                    if 0 <= row_idx < len(rows) and 0 <= col_idx < len(rows[row_idx]):
                        tile = rows[row_idx][col_idx]
                        if tile in ['W', 'O']:
                            world_x = player_x + dx
                            world_y = player_y + dy
                            
                            if (world_x, world_y) not in visited:
                                return (world_x, world_y)
        
        return None  # All visible tiles explored
    
    def get_context_for_llm(self, map_id: int, map_name: str, 
                            player_x: int, player_y: int,
                            minimap_2d: str) -> str:
        """
        Generate exploration context for LLM injection.
        
        Returns:
            Multi-line string with exploration status and suggestions
        """
        parts = []
        
        # Exploration summary
        summary = self.get_exploration_summary(map_id)
        parts.append(f"EXPLORATION: {summary}")
        
        # Unexplored directions with counts
        unexplored = self.get_unexplored_directions(map_id, player_x, player_y, minimap_2d)
        if unexplored:
            # Sort by count (highest first) to prioritize direction with most unexplored
            parts.append(f"UNEXPLORED AREAS: {', '.join(unexplored)}")
            
            # Find direction with most unexplored tiles
            best_dir = unexplored[0].split(" ")[0] if unexplored else None
            if best_dir:
                # Give strong directional command
                dir_to_button = {"NORTH": "U", "SOUTH": "D", "EAST": "R", "WEST": "L"}
                button = dir_to_button.get(best_dir, "U")
                parts.append(f"⚡ PRIORITY: Move {best_dir} (chain 5x {button};{button};{button};{button};{button};) to reach unexplored area")
        
        # Suggested target
        target = self.suggest_exploration_target(map_id, player_x, player_y, minimap_2d)
        if target:
            dx = target[0] - player_x
            dy = target[1] - player_y
            direction = []
            if dy < 0:
                direction.append("NORTH")
            elif dy > 0:
                direction.append("SOUTH")
            if dx > 0:
                direction.append("EAST")
            elif dx < 0:
                direction.append("WEST")
            
            dir_str = "-".join(direction) if direction else "NEARBY"
            # Calculate distance for step suggestion
            distance = abs(dx) + abs(dy)
            steps = min(5, max(3, distance))
            parts.append(f"SUGGESTED TARGET: Move {dir_str} toward unexplored area ({distance} tiles away, use {steps}+ moves)")
        
        return "\n".join(parts) if parts else ""
    
    def _save(self) -> None:
        """Save exploration data to file."""
        try:
            data = {
                str(map_id): exp.to_dict() 
                for map_id, exp in self.maps.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save exploration data: {e}")
    
    def _load(self) -> None:
        """Load exploration data from file."""
        if not os.path.exists(self.storage_path):
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            self.maps = {
                int(map_id): MapExploration.from_dict(exp_data)
                for map_id, exp_data in data.items()
            }
        except Exception as e:
            log.error(f"Failed to load exploration data: {e}")
            self.maps = {}
    
    def save(self) -> None:
        """Public save method."""
        self._save()
