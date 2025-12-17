#!/usr/bin/env python3
"""
Test script for dev markers system
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.dev_markers import get_dev_marker_registry


def test_dev_markers():
    """Test the dev marker registry"""
    print("=" * 60)
    print("Testing Dev Marker Registry")
    print("=" * 60)

    # Get the registry
    registry = get_dev_marker_registry()

    # Test 1: Check Oak's Lab markers
    print("\n[TEST 1] Oak's Lab Markers")
    print("-" * 60)
    oak_lab_markers = registry.get_markers_for_map("OAKS_LAB")
    print(f"Found {len(oak_lab_markers)} markers in Oak's Lab")

    for marker in oak_lab_markers:
        print(f"  - {marker.label} at [{marker.world_x},{marker.world_y}]")
        print(f"    Type: {marker.marker_type}, Char: {marker.marker_char}")
        print(f"    {marker.description}")
        print()

    # Test 2: Check starter Pokémon specifically
    print("\n[TEST 2] Starter Pokémon Markers")
    print("-" * 60)
    starters = registry.get_starter_pokemon_choices("OAKS_LAB")
    print(f"Found {len(starters)} starter Pokémon")

    for starter in starters:
        print(f"  ⭐ {starter.label} at [{starter.world_x},{starter.world_y}]")

    # Verify positions match requirements
    expected_positions = {"Charmander": (6, 3), "Squirtle": (7, 3), "Bulbasaur": (8, 3)}

    for starter in starters:
        expected_pos = expected_positions.get(starter.label)
        actual_pos = (starter.world_x, starter.world_y)
        if expected_pos == actual_pos:
            print(f"  ✅ {starter.label} position correct: {actual_pos}")
        else:
            print(
                f"  ❌ {starter.label} position WRONG: expected {expected_pos}, got {actual_pos}"
            )

    # Test 3: Overlay markers (simulated player position)
    print("\n[TEST 3] Overlay Markers (Player at [5,4])")
    print("-" * 60)

    # Simulate player at [5,4] in Oak's Lab (near the starters)
    player_world_x, player_world_y = 5, 4
    player_grid_x, player_grid_y = 10, 10  # Center of minimap
    grid_width, grid_height = 21, 19

    overlay_markers = registry.get_overlay_markers_for_map(
        "OAKS_LAB",
        player_world_x,
        player_world_y,
        player_grid_x,
        player_grid_y,
        grid_width,
        grid_height,
    )

    print(f"Generated {len(overlay_markers)} overlay markers")
    for marker in overlay_markers:
        print(
            f"  - Grid[{marker['x']},{marker['y']}] = {marker['type']} ({marker['reason']})"
        )

    # Test 4: LLM Context
    print("\n[TEST 4] LLM Context String")
    print("-" * 60)

    llm_context = registry.get_llm_context_for_map(
        "OAKS_LAB", player_world_x, player_world_y
    )

    print(llm_context)

    # Test 5: Adjacent tile check
    print("\n[TEST 5] Adjacent Tile Requirements")
    print("-" * 60)
    print("To interact with Charmander at [6,3]:")
    print("  - Player must be at [6,4] facing NORTH")
    print("  - Or at [5,3] facing EAST")
    print("  - Or at [7,3] facing WEST")
    print("  - Then press A to interact")

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_dev_markers()
