#!/usr/bin/env python3
"""
Pathfinding Performance Benchmark

Compares BFS vs A* pathfinding across various scenarios:
- Short paths (5-10 tiles)
- Medium paths (10-20 tiles)
- Long paths (20+ tiles)
- With/without terrain costs
- Cache performance

Usage:
    python scripts/pathfinding_benchmark.py
"""

import sys
import os
import time
import statistics
from typing import List, Tuple, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from pyAIAgent.navigation import (
        find_path,
        get_rom_path,
        _astar_find_path,
        _bfs_find_path,
    )
    from pyAIAgent.game.rom import (
        load_map,
        load_tileset_header,
        load_collision_data,
        load_block_data,
    )
    from pyAIAgent.game.graphics import build_quadrant_walkability
    from core.path_cache import get_path_cache

    HAS_NAVIGATION = True
except ImportError as e:
    print(f"Error importing navigation modules: {e}")
    HAS_NAVIGATION = False


# Test scenarios: (map_id, start, end, description)
TEST_SCENARIOS = [
    # Pallet Town - Short paths
    (1, [5, 5], [8, 5], "Short horizontal (3 tiles)"),
    (1, [5, 5], [5, 8], "Short vertical (3 tiles)"),
    (1, [5, 5], [8, 8], "Short diagonal (6 tiles)"),
    # Pallet Town - Medium paths
    (1, [3, 3], [10, 10], "Medium path (14 tiles)"),
    (1, [2, 2], [12, 12], "Medium with obstacles"),
    # Viridian Forest - Long paths with obstacles
    (51, [5, 5], [15, 25], "Long path (30+ tiles)"),
    (51, [3, 3], [20, 30], "Very long path (50+ tiles)"),
    # Route 1 - Vertical navigation
    (12, [5, 5], [5, 20], "Long vertical path"),
    # Oak's Lab - Indoor navigation
    (37, [5, 4], [6, 3], "Indoor short path"),
]


def measure_time(func, *args, **kwargs) -> Tuple[Optional[any], float]:
    """Measure execution time of a function in milliseconds."""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return result, (end - start) * 1000  # Convert to ms


def load_map_grid(rom_path: str, map_id: int):
    """Load map grid for testing."""
    try:
        with open(rom_path, "rb") as f:
            rom = f.read()

        tileset_id, width, height, map_data = load_map(rom, map_id)
        bank, blocks_ptr, _, collision_ptr, _ = load_tileset_header(rom, tileset_id)
        walkable_tiles = load_collision_data(rom, collision_ptr, bank)
        blocks = load_block_data(rom, blocks_ptr, bank, map_data)
        grid = build_quadrant_walkability(
            width, height, map_data, blocks, walkable_tiles
        )

        return grid
    except Exception as e:
        print(f"  Error loading map {map_id}: {e}")
        return None


def benchmark_path(
    rom_path: str,
    map_id: int,
    start: List[int],
    end: List[int],
    description: str,
    runs: int = 5,
):
    """Benchmark a single pathfinding scenario."""
    print(f"\n{'=' * 70}")
    print(f"Scenario: {description}")
    print(f"  Map: {map_id}, Start: {start}, End: {end}")
    print(f"{'=' * 70}")

    # Load grid once
    grid = load_map_grid(rom_path, map_id)
    if grid is None:
        print("  ❌ Failed to load map grid")
        return

    # Test BFS
    bfs_times = []
    bfs_result = None
    print(f"\n🔍 Testing BFS ({runs} runs)...")
    for i in range(runs):
        result, elapsed = measure_time(_bfs_find_path, grid, start, end)
        bfs_times.append(elapsed)
        if i == 0:
            bfs_result = result
        print(f"  Run {i + 1}: {elapsed:.2f}ms")

    if bfs_result is None:
        print("  ❌ BFS found no path")
        bfs_path_length = 0
    else:
        bfs_path_length = len(bfs_result[0])
        print(f"  ✅ Path found: {bfs_path_length} moves")

    # Test A* without terrain costs
    astar_times = []
    astar_result = None
    print(f"\n⚡ Testing A* without costs ({runs} runs)...")
    for i in range(runs):
        result, elapsed = measure_time(_astar_find_path, grid, start, end, costs=None)
        astar_times.append(elapsed)
        if i == 0:
            astar_result = result
        print(f"  Run {i + 1}: {elapsed:.2f}ms")

    if astar_result is None:
        print("  ❌ A* found no path")
        astar_path_length = 0
    else:
        astar_path_length = len(astar_result[0])
        print(f"  ✅ Path found: {astar_path_length} moves")

    # Verify same path length
    if bfs_result and astar_result:
        if bfs_path_length == astar_path_length:
            print(f"  ✅ Path lengths match: {bfs_path_length} moves")
        else:
            print(
                f"  ⚠️  Path length mismatch: BFS={bfs_path_length}, A*={astar_path_length}"
            )

    # Statistics
    print(f"\n📊 Performance Comparison:")
    if bfs_times and astar_times:
        bfs_avg = statistics.mean(bfs_times)
        astar_avg = statistics.mean(astar_times)
        speedup = bfs_avg / astar_avg if astar_avg > 0 else 0

        print(
            f"  BFS:  {bfs_avg:.2f}ms avg, {min(bfs_times):.2f}ms min, {max(bfs_times):.2f}ms max"
        )
        print(
            f"  A*:   {astar_avg:.2f}ms avg, {min(astar_times):.2f}ms min, {max(astar_times):.2f}ms max"
        )
        print(f"  🚀 Speedup: {speedup:.2f}x faster with A*")

        return {
            "description": description,
            "path_length": bfs_path_length,
            "bfs_avg": bfs_avg,
            "astar_avg": astar_avg,
            "speedup": speedup,
        }

    return None


def benchmark_cache(rom_path: str, runs: int = 10):
    """Benchmark path cache performance."""
    print(f"\n{'=' * 70}")
    print(f"Path Cache Benchmark")
    print(f"{'=' * 70}")

    cache = get_path_cache(max_size=100, ttl=300)
    cache.clear()  # Start fresh

    # Use a test scenario
    map_id, start, end, _ = TEST_SCENARIOS[0]

    print(f"\n📦 Testing cache with Map {map_id}, {start} -> {end}")

    # First call - should miss cache
    print(f"\n🔍 First call (cache miss expected)...")
    result1, time1 = measure_time(find_path, rom_path, map_id, start, end)
    print(f"  Time: {time1:.2f}ms")
    print(f"  Result: {result1[:30] if result1 else None}...")

    # Second call - should hit cache
    print(f"\n⚡ Second call (cache hit expected)...")
    result2, time2 = measure_time(find_path, rom_path, map_id, start, end)
    print(f"  Time: {time2:.2f}ms")
    print(f"  Result: {result2[:30] if result2 else None}...")

    # Multiple cached calls
    print(f"\n🔥 Running {runs} cached calls...")
    cached_times = []
    for i in range(runs):
        _, elapsed = measure_time(find_path, rom_path, map_id, start, end)
        cached_times.append(elapsed)

    cached_avg = statistics.mean(cached_times)
    print(f"  Average cached time: {cached_avg:.4f}ms")
    print(f"  🚀 Cache speedup: {time1 / cached_avg:.0f}x faster")

    # Cache stats
    stats = cache.get_stats()
    print(f"\n📊 Cache Statistics:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit rate: {stats['hit_rate']:.1f}%")
    print(f"  Size: {stats['size']}/{stats['max_size']}")


def main():
    """Run comprehensive pathfinding benchmarks."""
    if not HAS_NAVIGATION:
        print("❌ Navigation modules not available. Install dependencies:")
        print("   pip install Pillow")
        sys.exit(1)

    rom_path = get_rom_path()
    if not os.path.exists(rom_path):
        print(f"❌ ROM not found: {rom_path}")
        print("   Set POKEMON_ROM environment variable or place red.gb in roms/")
        sys.exit(1)

    print("=" * 70)
    print("  PATHFINDING PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"ROM: {rom_path}")
    print(f"Scenarios: {len(TEST_SCENARIOS)}")
    print(f"Runs per scenario: 5")

    # Run all scenarios
    results = []
    for map_id, start, end, description in TEST_SCENARIOS:
        result = benchmark_path(rom_path, map_id, start, end, description, runs=5)
        if result:
            results.append(result)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  SUMMARY")
    print(f"{'=' * 70}")

    if results:
        avg_speedup = statistics.mean([r["speedup"] for r in results])
        print(f"\n📊 Overall Performance:")
        print(f"  Scenarios tested: {len(results)}")
        print(f"  Average speedup: {avg_speedup:.2f}x")

        print(f"\n📈 By Path Length:")
        results.sort(key=lambda r: r["path_length"])
        for r in results:
            print(
                f"  {r['description']:30s} ({r['path_length']:2d} moves): {r['speedup']:.2f}x"
            )

    # Cache benchmark
    benchmark_cache(rom_path, runs=10)

    print(f"\n{'=' * 70}")
    print(f"  ✅ BENCHMARK COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
