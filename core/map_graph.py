"""
Map Graph - Hierarchical Navigation for Cross-Map Pathfinding

Builds and manages a graph of map connections for strategic navigation.
Enables the LLM to plan routes across multiple maps (e.g., Pallet Town -> Pewter City).

Key Concepts:
- Each map is a node in the graph
- Exits/warps are edges connecting maps
- Dijkstra's algorithm finds shortest map-to-map routes
- Integration with A* for within-map navigation

Usage:
    from core.map_graph import MapGraph, build_map_graph_from_rom

    # Build graph from ROM
    graph = build_map_graph_from_rom("roms/red.gb")

    # Find route from Pallet Town (1) to Pewter City (2)
    route = graph.find_route(1, 2)
    # Returns: [1, 12, 13, 51, 14, 2] (Pallet -> Route1 -> Viridian -> Forest -> Route2 -> Pewter)

    # Get exit coordinates
    exit_coords = graph.get_exit_coords(1, 12)  # Pallet to Route 1
    # Returns: (x, y) coordinates of the exit
"""

import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import heapq

log = logging.getLogger("map_graph")


@dataclass
class MapConnection:
    """A connection between two maps via an exit/warp."""

    from_map: int
    to_map: int
    from_coords: Tuple[int, int]  # (x, y) where exit is located
    to_coords: Tuple[int, int]  # (x, y) where player arrives
    connection_type: str  # "exit", "warp", "door"

    def __repr__(self):
        return f"Map{self.from_map}@{self.from_coords} -{self.connection_type}-> Map{self.to_map}@{self.to_coords}"


class MapGraph:
    """
    Graph of map connections for hierarchical pathfinding.

    Supports:
    - Finding routes between maps
    - Getting exit coordinates
    - Map traversal cost estimation
    """

    def __init__(self):
        self.connections: List[MapConnection] = []
        self.adjacency: Dict[
            int, List[MapConnection]
        ] = {}  # map_id -> list of outgoing connections
        self.map_names: Dict[int, str] = {}  # map_id -> name

    def add_connection(self, connection: MapConnection):
        """Add a connection to the graph."""
        self.connections.append(connection)

        if connection.from_map not in self.adjacency:
            self.adjacency[connection.from_map] = []
        self.adjacency[connection.from_map].append(connection)

    def add_map_name(self, map_id: int, name: str):
        """Register a map name."""
        self.map_names[map_id] = name

    def get_neighbors(self, map_id: int) -> List[Tuple[int, MapConnection]]:
        """Get all adjacent maps and their connections."""
        if map_id not in self.adjacency:
            return []
        return [(conn.to_map, conn) for conn in self.adjacency[map_id]]

    def find_route(self, start_map: int, goal_map: int) -> Optional[List[int]]:
        """
        Find shortest route between maps using Dijkstra's algorithm.

        Args:
            start_map: Starting map ID
            goal_map: Destination map ID

        Returns:
            List of map IDs forming the route, or None if no route exists
        """
        if start_map == goal_map:
            return [start_map]

        # Dijkstra's algorithm for map-level pathfinding
        frontier = [(0, start_map)]  # (cost, map_id)
        came_from = {}
        cost_so_far = {start_map: 0}

        while frontier:
            current_cost, current_map = heapq.heappop(frontier)

            if current_map == goal_map:
                break

            for next_map, connection in self.get_neighbors(current_map):
                # Each map transition has cost 1 (can be customized later)
                new_cost = cost_so_far[current_map] + 1

                if next_map not in cost_so_far or new_cost < cost_so_far[next_map]:
                    cost_so_far[next_map] = new_cost
                    came_from[next_map] = current_map
                    heapq.heappush(frontier, (new_cost, next_map))

        # Reconstruct path
        if goal_map not in came_from and goal_map != start_map:
            return None

        path = []
        current = goal_map
        while current != start_map:
            path.append(current)
            if current not in came_from:
                return None
            current = came_from[current]
        path.append(start_map)

        return list(reversed(path))

    def get_exit_coords(self, from_map: int, to_map: int) -> Optional[Tuple[int, int]]:
        """Get exit coordinates for traveling from one map to another."""
        if from_map not in self.adjacency:
            return None

        for conn in self.adjacency[from_map]:
            if conn.to_map == to_map:
                return conn.from_coords

        return None

    def get_route_description(self, route: List[int]) -> str:
        """
        Generate human-readable route description.

        Args:
            route: List of map IDs

        Returns:
            String like "Pallet Town -> Route 1 -> Viridian City"
        """
        if not route:
            return "No route"

        names = [self.map_names.get(map_id, f"Map {map_id}") for map_id in route]
        return " -> ".join(names)

    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "maps": len(self.adjacency),
            "connections": len(self.connections),
            "avg_connections_per_map": len(self.connections)
            / max(len(self.adjacency), 1),
        }


def build_map_graph_from_rom(rom_path: str) -> MapGraph:
    """
    Build map graph from Pokemon ROM data.

    NOTE: This is a simplified implementation. A full implementation would:
    - Parse warp data from ROM
    - Extract connection data from map headers
    - Handle special warps (Fly, Dig, Escape Rope)

    For now, we'll build a static graph of known connections.

    Args:
        rom_path: Path to Pokemon ROM file

    Returns:
        MapGraph instance
    """
    graph = MapGraph()

    # HACK: Hardcoded map connections for Pokemon Red
    # TODO: Extract these from ROM automatically

    # Map names
    map_names = {
        0: "Pallet Town",
        1: "Viridian City",
        2: "Pewter City",
        3: "Cerulean City",
        12: "Route 1",
        13: "Route 2",
        14: "Route 2",
        15: "Route 3",
        37: "Oak's Lab",
        39: "Player's House 1F",
        40: "Player's House 2F",
        51: "Viridian Forest",
    }

    for map_id, name in map_names.items():
        graph.add_map_name(map_id, name)

    # Connections (simplified - real ROM has more)
    connections = [
        # Pallet Town connections
        MapConnection(0, 12, (5, 0), (5, 30), "exit"),  # Pallet -> Route 1
        MapConnection(0, 37, (11, 12), (4, 7), "door"),  # Pallet -> Oak's Lab
        MapConnection(0, 39, (5, 5), (3, 7), "door"),  # Pallet -> Player's House
        # Route 1 connections
        MapConnection(12, 0, (5, 30), (5, 0), "exit"),  # Route 1 -> Pallet
        MapConnection(12, 1, (5, 0), (5, 18), "exit"),  # Route 1 -> Viridian
        # Viridian City connections
        MapConnection(1, 12, (5, 18), (5, 0), "exit"),  # Viridian -> Route 1
        MapConnection(1, 13, (5, 0), (5, 15), "exit"),  # Viridian -> Route 2
        # Route 2 connections
        MapConnection(13, 1, (5, 15), (5, 0), "exit"),  # Route 2 -> Viridian
        MapConnection(13, 51, (5, 5), (17, 47), "exit"),  # Route 2 -> Viridian Forest
        # Viridian Forest connections
        MapConnection(51, 13, (17, 47), (5, 5), "exit"),  # Forest -> Route 2
        MapConnection(51, 14, (1, 0), (3, 45), "exit"),  # Forest -> Route 2 (north)
        # Route 2 (north) connections
        MapConnection(14, 51, (3, 45), (1, 0), "exit"),  # Route 2 (north) -> Forest
        MapConnection(14, 2, (3, 0), (10, 17), "exit"),  # Route 2 (north) -> Pewter
        # Pewter City connections
        MapConnection(2, 14, (10, 17), (3, 0), "exit"),  # Pewter -> Route 2 (north)
        MapConnection(2, 15, (30, 8), (0, 4), "exit"),  # Pewter -> Route 3
        # Indoor connections
        MapConnection(37, 0, (4, 7), (11, 12), "door"),  # Oak's Lab -> Pallet
        MapConnection(39, 0, (3, 7), (5, 5), "door"),  # Player's House -> Pallet
        MapConnection(39, 40, (7, 1), (6, 1), "stairs"),  # House 1F -> 2F
        MapConnection(40, 39, (6, 1), (7, 1), "stairs"),  # House 2F -> 1F
    ]

    for conn in connections:
        graph.add_connection(conn)

    log.info(
        f"Built map graph with {len(graph.adjacency)} maps and {len(graph.connections)} connections"
    )

    return graph


# Global map graph instance
_global_map_graph: Optional[MapGraph] = None


def get_map_graph(rom_path: Optional[str] = None) -> MapGraph:
    """
    Get global map graph instance (singleton).

    Args:
        rom_path: Path to ROM file (only used on first call)

    Returns:
        Global MapGraph instance
    """
    global _global_map_graph

    if _global_map_graph is None:
        if rom_path:
            _global_map_graph = build_map_graph_from_rom(rom_path)
        else:
            # Build with default ROM
            try:
                from pyAIAgent.navigation import get_rom_path

                _global_map_graph = build_map_graph_from_rom(get_rom_path())
            except Exception as e:
                log.error(f"Failed to build map graph: {e}")
                # Return empty graph
                _global_map_graph = MapGraph()

    return _global_map_graph
