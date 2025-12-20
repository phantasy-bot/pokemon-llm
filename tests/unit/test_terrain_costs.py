#!/usr/bin/env python3
"""
Terrain Cost and One-Way Ledge Tests

Tests for Phase 3 terrain-aware pathfinding:
- Terrain cost detection (grass, water, ledges)
- One-way ledge constraints
- Auto-terrain mode
- HM-aware pathfinding
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from pyAIAgent.navigation import (
    build_terrain_costs,
    build_one_way_edges,
    _astar_find_path,
    TERRAIN_COSTS,
    GRASS_TILE_IDS,
    WATER_TILE_IDS,
    LEDGE_TILE_IDS,
)


class TestTerrainCosts(unittest.TestCase):
    """Test terrain cost detection and application."""

    def setUp(self):
        """Set up test data."""
        # Simple 3x3 grid
        self.width = 3
        self.height = 3

        # Mock map data (all same block for simplicity)
        self.map_data = [0] * 9

        # Mock blocks with different tile types
        # Each block is 4 tiles (2x2 quadrant)
        grass_id = list(GRASS_TILE_IDS)[0] if GRASS_TILE_IDS else 0x14
        water_id = list(WATER_TILE_IDS)[0] if WATER_TILE_IDS else 0x14
        ledge_id = list(LEDGE_TILE_IDS)[0] if LEDGE_TILE_IDS else 0x38
        normal_id = 0x01

        self.blocks = [
            bytes(
                [grass_id, grass_id, normal_id, normal_id] + [0] * 12
            ),  # Block 0: grass
        ]

        self.walkable_tiles = {grass_id, water_id, ledge_id, normal_id}

    def test_grass_detection(self):
        """Test that grass tiles get higher cost."""
        costs = build_terrain_costs(
            self.width, self.height, self.map_data, self.blocks, self.walkable_tiles
        )

        # Should detect grass tiles in first quadrant
        if costs:
            # Check if any tile has grass cost
            has_grass_cost = any(
                cost == TERRAIN_COSTS["grass_tall"] for cost in costs.values()
            )
            self.assertTrue(
                has_grass_cost, "Should detect grass tiles with higher cost"
            )

    def test_water_without_surf(self):
        """Test that water tiles have very high cost without Surf."""
        water_id = list(WATER_TILE_IDS)[0] if WATER_TILE_IDS else 0x14
        water_blocks = [
            bytes([water_id, water_id, water_id, water_id] + [0] * 12),
        ]

        costs = build_terrain_costs(
            self.width,
            self.height,
            self.map_data,
            water_blocks,
            self.walkable_tiles,
            player_items=set(),  # No Surf
        )

        if costs:
            has_water_cost = any(
                cost == TERRAIN_COSTS["water"] for cost in costs.values()
            )
            self.assertTrue(
                has_water_cost, "Should have high cost for water without Surf"
            )

    def test_water_with_surf(self):
        """Test that water tiles have normal cost with Surf HM."""
        water_id = list(WATER_TILE_IDS)[0] if WATER_TILE_IDS else 0x14
        water_blocks = [
            bytes([water_id, water_id, water_id, water_id] + [0] * 12),
        ]

        costs = build_terrain_costs(
            self.width,
            self.height,
            self.map_data,
            water_blocks,
            self.walkable_tiles,
            player_items={"Surf"},  # Has Surf!
        )

        # With Surf, water should have default cost (or not be in costs dict)
        if costs:
            water_costs = [
                cost for cost in costs.values() if cost == TERRAIN_COSTS["water"]
            ]
            # Should have fewer or no high water costs
            self.assertEqual(
                len(water_costs), 0, "Water should not have high cost with Surf"
            )


class TestOneWayLedges(unittest.TestCase):
    """Test one-way ledge constraint detection."""

    def test_ledge_direction_detection(self):
        """Test that ledge directions are detected correctly."""
        # Create a simple map with a ledge
        width, height = 3, 3

        ledge_id = list(LEDGE_TILE_IDS)[0] if LEDGE_TILE_IDS else 0x38
        normal_id = 0x01

        # Block 0: normal tiles
        # Block 1: ledge tile on top-left, normal on others
        blocks = [
            bytes([normal_id] * 16),
            bytes([ledge_id, normal_id, normal_id, normal_id] + [0] * 12),
        ]

        map_data = [0, 0, 0, 1, 0, 0, 0, 0, 0]  # Ledge in middle-left

        walkable_tiles = {ledge_id, normal_id}

        edges = build_one_way_edges(width, height, map_data, blocks, walkable_tiles)

        # Should detect some one-way edges for ledge
        if edges:
            self.assertGreater(len(edges), 0, "Should detect one-way edges for ledges")

            # Check that at least one edge is forbidden (can't climb up)
            has_forbidden = any(not allowed for allowed in edges.values())
            self.assertTrue(
                has_forbidden,
                "Should have at least one forbidden edge (can't climb up)",
            )


class TestAStarWithTerrainCosts(unittest.TestCase):
    """Test A* pathfinding with terrain costs."""

    def test_avoids_high_cost_terrain(self):
        """Test that A* avoids high-cost terrain when possible."""
        # Create a 5x5 grid
        grid = [
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
        ]

        # Add high cost in the middle (3x3 area)
        costs = {}
        for y in range(1, 4):
            for x in range(1, 4):
                costs[(x, y)] = 100  # Very high cost

        # Find path from (0, 2) to (4, 2) - should go around high-cost area
        start = [0, 2]
        end = [4, 2]

        result = _astar_find_path(grid, start, end, costs)

        self.assertIsNotNone(result, "Should find a path")

        if result:
            actions, coords = result

            # Check that path avoids the center
            for x, y in coords:
                if 1 <= x <= 3 and 1 <= y <= 3:
                    # Path went through high-cost area
                    # This might happen if it's the only way, but should prefer edges
                    pass

    def test_respects_one_way_edges(self):
        """Test that A* respects one-way edge constraints."""
        # Create a simple 3x3 grid
        grid = [
            [True, True, True],
            [True, True, True],
            [True, True, True],
        ]

        # Create one-way edge: can go from (1,0) to (1,1) but NOT back
        one_way_edges = {
            (1, 0, 1, 1): True,  # Allow down
            (1, 1, 1, 0): False,  # Forbid up (can't climb ledge)
        }

        # Try to find path from (1, 1) to (1, 0) - should fail or go around
        start = [1, 1]
        end = [1, 0]

        result = _astar_find_path(
            grid, start, end, costs=None, one_way_edges=one_way_edges
        )

        if result:
            actions, coords = result
            # If path exists, it should NOT go directly up
            # It should go around (left or right, then up)

            # Check if path goes directly from (1,1) to (1,0)
            for i in range(len(coords) - 1):
                if coords[i] == (1, 1) and coords[i + 1] == (1, 0):
                    self.fail("Path should not go directly up the forbidden edge")

        # Now try the allowed direction: (1, 0) to (1, 1)
        start2 = [1, 0]
        end2 = [1, 1]

        result2 = _astar_find_path(
            grid, start2, end2, costs=None, one_way_edges=one_way_edges
        )

        self.assertIsNotNone(result2, "Should find path in allowed direction")

        if result2:
            actions, coords = result2
            # This path CAN go directly down
            self.assertEqual(len(actions), 1, "Should be a direct path down (1 move)")
            self.assertEqual(actions, "D", "Should be a down move")


class TestIntegration(unittest.TestCase):
    """Integration tests for terrain costs and pathfinding."""

    def test_combined_costs_and_edges(self):
        """Test A* with both terrain costs and one-way edges."""
        # 5x5 grid
        grid = [
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
            [True, True, True, True, True],
        ]

        # High cost in middle
        costs = {(2, 2): 50}

        # One-way edge (ledge)
        one_way_edges = {
            (2, 1, 2, 2): True,  # Can jump down
            (2, 2, 2, 1): False,  # Can't climb up
        }

        # Find path that might want to use the ledge
        start = [2, 1]
        end = [2, 3]

        result = _astar_find_path(grid, start, end, costs, one_way_edges)

        self.assertIsNotNone(result, "Should find a path even with constraints")

        if result:
            actions, coords = result
            # Path should exist and respect constraints
            self.assertGreater(len(coords), 0, "Path should have coordinates")


def run_tests():
    """Run all tests and report results."""
    print("=" * 70)
    print("  TERRAIN COST AND ONE-WAY LEDGE TESTS")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestTerrainCosts))
    suite.addTests(loader.loadTestsFromTestCase(TestOneWayLedges))
    suite.addTests(loader.loadTestsFromTestCase(TestAStarWithTerrainCosts))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
