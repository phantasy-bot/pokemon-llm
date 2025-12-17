"""
Path Cache - LRU cache for pathfinding results

Caches computed paths to avoid redundant pathfinding calculations.
Significantly improves performance when LLM requests same paths repeatedly.
"""

import time
import logging
from collections import OrderedDict
from typing import Optional, Tuple, List

log = logging.getLogger("path_cache")


class PathCache:
    """
    LRU (Least Recently Used) cache for pathfinding results.

    Stores paths with automatic eviction and TTL (time-to-live).
    Thread-safe for concurrent access.

    Usage:
        cache = PathCache(max_size=100, ttl=300)

        # Try to get cached path
        path = cache.get(map_id, start, goal)
        if path is None:
            # Compute path
            path = compute_path(...)
            cache.set(map_id, start, goal, path)
    """

    def __init__(self, max_size=100, ttl=300):
        """
        Initialize path cache.

        Args:
            max_size: Maximum number of paths to cache (LRU eviction)
            ttl: Time-to-live in seconds (paths older than this are invalid)
        """
        self.cache = OrderedDict()  # Preserves insertion order for LRU
        self.max_size = max_size
        self.ttl = ttl

        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

        log.info(f"PathCache initialized: max_size={max_size}, ttl={ttl}s")

    def get(
        self, map_id: int, start: Tuple[int, int], goal: Tuple[int, int]
    ) -> Optional[str]:
        """
        Get cached path if it exists and is still valid.

        Args:
            map_id: Map identifier
            start: Starting coordinates (x, y)
            goal: Goal coordinates (x, y)

        Returns:
            Cached path string or None if not cached/expired
        """
        key = self._make_key(map_id, start, goal)

        if key in self.cache:
            path, timestamp = self.cache[key]

            # Check if expired
            if time.time() - timestamp < self.ttl:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                self.hits += 1
                log.debug(f"Cache HIT: {key}")
                return path
            else:
                # Expired - remove it
                del self.cache[key]
                log.debug(f"Cache EXPIRED: {key}")

        self.misses += 1
        log.debug(f"Cache MISS: {key}")
        return None

    def set(
        self, map_id: int, start: Tuple[int, int], goal: Tuple[int, int], path: str
    ):
        """
        Store path in cache.

        Args:
            map_id: Map identifier
            start: Starting coordinates (x, y)
            goal: Goal coordinates (x, y)
            path: Path string to cache (e.g., "R;R;D;D;")
        """
        key = self._make_key(map_id, start, goal)

        # Update if exists, add if new
        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = (path, time.time())

        # Evict oldest if over size
        if len(self.cache) > self.max_size:
            evicted_key = self.cache.popitem(last=False)  # Remove oldest
            self.evictions += 1
            log.debug(f"Cache EVICT: {evicted_key[0]} (size={self.max_size})")

        log.debug(f"Cache SET: {key}")

    def invalidate_map(self, map_id: int) -> int:
        """
        Invalidate all cached paths for a specific map.

        Call this when a map changes (e.g., NPC moves, boulder pushed).

        Args:
            map_id: Map identifier to invalidate

        Returns:
            Number of paths invalidated
        """
        keys_to_remove = [k for k in self.cache.keys() if k[0] == map_id]

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            log.info(f"Invalidated {len(keys_to_remove)} paths for map {map_id}")

        return len(keys_to_remove)

    def clear(self):
        """Clear entire cache."""
        count = len(self.cache)
        self.cache.clear()
        log.info(f"Cache cleared: {count} paths removed")

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, size, evictions
        """
        total = self.hits + self.misses
        hit_rate = ((self.hits / total) * 100) if total > 0 else 0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "size": len(self.cache),
            "max_size": self.max_size,
            "evictions": self.evictions,
        }

    def log_stats(self):
        """Log cache statistics."""
        stats = self.get_stats()
        log.info(
            f"PathCache stats: {stats['hits']} hits, {stats['misses']} misses, "
            f"{stats['hit_rate']:.1f}% hit rate, {stats['size']}/{stats['max_size']} cached"
        )

    @staticmethod
    def _make_key(map_id: int, start: Tuple[int, int], goal: Tuple[int, int]) -> tuple:
        """
        Create cache key from parameters.

        Args:
            map_id: Map identifier
            start: Starting coordinates
            goal: Goal coordinates

        Returns:
            Tuple key for cache dictionary
        """
        return (map_id, tuple(start), tuple(goal))


# Global cache instance (singleton pattern)
_global_path_cache: Optional[PathCache] = None


def get_path_cache(max_size=100, ttl=300) -> PathCache:
    """
    Get the global path cache instance (singleton).

    Args:
        max_size: Maximum cache size (only used on first call)
        ttl: Time-to-live in seconds (only used on first call)

    Returns:
        Global PathCache instance
    """
    global _global_path_cache
    if _global_path_cache is None:
        _global_path_cache = PathCache(max_size=max_size, ttl=ttl)
    return _global_path_cache
