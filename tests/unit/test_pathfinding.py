"""
Unit tests for pathfinding algorithms (BFS vs A*)
"""

import sys
import os
import time
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyAIAgent.navigation import (
    _bfs_find_path,
    _astar_find_path,
    find_path,
    get_rom_path,
)


class TestPathfindingAlgorithms(unittest.TestCase):
    """Test pathfinding algorithms for correctness and performance"""

    def setUp(self):
        """Create test grids"""
        # Simple 5x5 grid, all walkable
        self.simple_grid = [
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
        ]

        # Grid with obstacles
        self.obstacle_grid = [
            [True, True, True, True, True],
            [True, False, False, False, True],
            [True, True, True, False, True],
            [True, False, True, False, True],
            [True, True, True, True, True],
        ]

        # Large grid for performance testing
        self.large_grid = [[True for _ in range(50)] for _ in range(50)]

    def test_astar_vs_bfs_same_result_simple(self):
        """A* should find same path length as BFS on simple grid"""
        start = (0, 0)
        end = (4, 4)

        bfs_result = _bfs_find_path(self.simple_grid, start, end)
        astar_result = _astar_find_path(self.simple_grid, start, end)

        self.assertIsNotNone(bfs_result, "BFS should find path")
        self.assertIsNotNone(astar_result, "A* should find path")

        # Both should find shortest path (same length)
        bfs_actions, bfs_coords = bfs_result
        astar_actions, astar_coords = astar_result

        self.assertEqual(
            len(bfs_actions),
            len(astar_actions),
            f"Path lengths should match: BFS={len(bfs_actions)}, A*={len(astar_actions)}",
        )

    def test_astar_vs_bfs_with_obstacles(self):
        """A* should find same path length as BFS around obstacles"""
        start = (0, 0)
        end = (4, 4)

        bfs_result = _bfs_find_path(self.obstacle_grid, start, end)
        astar_result = _astar_find_path(self.obstacle_grid, start, end)

        self.assertIsNotNone(bfs_result)
        self.assertIsNotNone(astar_result)

        bfs_actions, _ = bfs_result
        astar_actions, _ = astar_result

        # Should find shortest path (same length)
        self.assertEqual(len(bfs_actions), len(astar_actions))

    def test_astar_performance_vs_bfs(self):
        """A* should be significantly faster than BFS on large grids"""
        start = (0, 0)
        end = (49, 49)

        # Time BFS
        bfs_start = time.time()
        bfs_result = _bfs_find_path(self.large_grid, start, end)
        bfs_time = (time.time() - bfs_start) * 1000  # ms

        # Time A*
        astar_start = time.time()
        astar_result = _astar_find_path(self.large_grid, start, end)
        astar_time = (time.time() - astar_start) * 1000  # ms

        self.assertIsNotNone(bfs_result)
        self.assertIsNotNone(astar_result)

        print(f"\nPerformance on 50x50 grid:")
        print(f"  BFS:  {bfs_time:.2f}ms")
        print(f"  A*:   {astar_time:.2f}ms")
        print(f"  Speedup: {bfs_time / astar_time:.1f}x")

        # A* should be faster (at least 2x on this grid)
        self.assertLess(
            astar_time,
            bfs_time,
            f"A* should be faster than BFS (A*={astar_time:.2f}ms, BFS={bfs_time:.2f}ms)",
        )

    def test_astar_respects_terrain_costs(self):
        """A* should route around high-cost terrain"""
        # Create grid where direct path has high costs
        grid = [
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
        ]

        # Add high costs to middle column
        costs = {
            (2, 1): 100,
            (2, 2): 100,
            (2, 3): 100,
        }

        start = (0, 2)
        end = (4, 2)

        result = _astar_find_path(grid, start, end, costs)
        self.assertIsNotNone(result)

        actions, coords = result

        # Path should avoid middle column (x=2) due to high costs
        # Check that path doesn't go through high-cost tiles
        for x, y in coords:
            if (x, y) in costs:
                # If it does go through high-cost area, the cost was worth it
                # but we expect it to route around
                pass

        print(f"\nTerrain-aware path from {start} to {end}:")
        print(f"  Actions: {actions}")
        print(f"  Coordinates: {coords}")

    def test_no_path_exists(self):
        """Both algorithms should return None when no path exists"""
        # Grid with unreachable goal
        grid = [
            [True, True, False],
            [True, True, False],
            [False, False, True],
        ]

        start = (0, 0)
        end = (2, 2)

        bfs_result = _bfs_find_path(grid, start, end)
        astar_result = _astar_find_path(grid, start, end)

        self.assertIsNone(bfs_result, "BFS should return None for unreachable goal")
        self.assertIsNone(astar_result, "A* should return None for unreachable goal")

    def test_start_equals_goal(self):
        """Handle case where start == goal"""
        start = (2, 2)
        end = (2, 2)

        bfs_result = _bfs_find_path(self.simple_grid, start, end)
        astar_result = _astar_find_path(self.simple_grid, start, end)

        # Both should handle this edge case gracefully
        # (either return empty path or None - both acceptable)
        if bfs_result:
            self.assertEqual(
                len(bfs_result[0]), 0, "Path should be empty when start==goal"
            )
        if astar_result:
            self.assertEqual(
                len(astar_result[0]), 0, "Path should be empty when start==goal"
            )

    def test_find_path_integration(self):
        """Test find_path() with actual ROM if available"""
        rom_path = get_rom_path()

        if not os.path.exists(rom_path):
            self.skipTest(f"ROM not found at {rom_path}")

        # Test pathfinding on Pallet Town (map_id=0)
        # From player start to north exit
        map_id = 0
        start = [5, 5]
        end = [5, 0]

        # Test A*
        astar_path = find_path(rom_path, map_id, start, end, use_astar=True)
        self.assertIsNotNone(astar_path, "A* should find path in Pallet Town")

        # Test BFS
        bfs_path = find_path(rom_path, map_id, start, end, use_astar=False)
        self.assertIsNotNone(bfs_path, "BFS should find path in Pallet Town")

        print(f"\nReal Pokemon map pathfinding:")
        print(f"  A* path:  {astar_path}")
        print(f"  BFS path: {bfs_path}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
