# --- screenshot_manager.py ---
"""
Screenshot Manager for Zora Gallery Posts.

Maintains a rolling buffer of recent screenshots for creating gallery posts
on the LLMLetsPlay Zora account. Unlike the ScreenshotHistoryTracker (which
keeps only 2 screenshots for UI diff checking), this manager keeps 5 screenshots
for creating rich gallery posts.

Screenshots are NOT deleted - they're just rotated out of the buffer.
The actual cleanup is handled elsewhere.
"""

import os
import shutil
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from collections import deque
from pathlib import Path

log = logging.getLogger("screenshot_manager")


@dataclass
class ScreenshotEntry:
    """A single screenshot with context metadata."""

    path: str
    timestamp: float
    cycle_number: int
    action_number: int
    map_name: str = ""
    location_description: str = ""

    def exists(self) -> bool:
        """Check if the screenshot file still exists."""
        return os.path.exists(self.path)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "path": self.path,
            "timestamp": self.timestamp,
            "cycle_number": self.cycle_number,
            "action_number": self.action_number,
            "map_name": self.map_name,
            "location_description": self.location_description,
        }


class ScreenshotManager:
    """
    Manages a rolling buffer of recent screenshots for Zora gallery posts.

    This is separate from ScreenshotHistoryTracker which handles UI diff checking.
    The ScreenshotManager:
    - Keeps up to 5 most recent screenshots
    - Copies screenshots to a dedicated gallery directory
    - Provides methods for creating gallery posts
    - Does NOT delete screenshots (just rotates buffer)

    Usage:
        manager = ScreenshotManager(gallery_dir="data/zora_gallery")

        # Every cycle, capture the screenshot
        manager.capture(
            source_path="/path/to/current_screenshot.png",
            cycle_number=42,
            action_number=123,
            map_name="PALLET_TOWN"
        )

        # When creating a Zora post
        screenshots = manager.get_gallery_paths()  # Returns up to 5 paths
    """

    def __init__(
        self,
        gallery_dir: str = "data/zora_gallery",
        max_screenshots: int = 5,
    ):
        """
        Initialize the screenshot manager.

        Args:
            gallery_dir: Directory to store gallery screenshots
            max_screenshots: Maximum screenshots to keep in buffer (default 5)
        """
        self.gallery_dir = Path(gallery_dir)
        self.max_screenshots = max_screenshots
        self._buffer: deque[ScreenshotEntry] = deque(maxlen=max_screenshots)

        # Ensure gallery directory exists
        self.gallery_dir.mkdir(parents=True, exist_ok=True)

        # Stats
        self._total_captures = 0

        log.info(
            f"Screenshot Manager initialized "
            f"(dir: {gallery_dir}, max: {max_screenshots})"
        )

    def capture(
        self,
        source_path: str,
        cycle_number: int,
        action_number: int,
        map_name: str = "",
        location_description: str = "",
    ) -> Optional[ScreenshotEntry]:
        """
        Capture a screenshot by copying it to the gallery directory.

        Args:
            source_path: Path to the source screenshot file
            cycle_number: Current game cycle number
            action_number: Current action number
            map_name: Current map/location name
            location_description: Human-readable location description

        Returns:
            ScreenshotEntry if successful, None if source doesn't exist
        """
        if not source_path or not os.path.exists(source_path):
            log.warning(f"Source screenshot not found: {source_path}")
            return None

        # Generate unique filename with context
        timestamp = time.time()
        filename = f"gallery_{cycle_number:06d}_{action_number:06d}.png"
        dest_path = self.gallery_dir / filename

        try:
            # Copy the screenshot to gallery directory
            shutil.copy2(source_path, dest_path)

            entry = ScreenshotEntry(
                path=str(dest_path),
                timestamp=timestamp,
                cycle_number=cycle_number,
                action_number=action_number,
                map_name=map_name,
                location_description=location_description,
            )

            # Add to buffer (automatically rotates out oldest if at max)
            self._buffer.append(entry)
            self._total_captures += 1

            log.debug(
                f"Captured screenshot: cycle {cycle_number}, "
                f"action {action_number}, map: {map_name}"
            )

            return entry

        except Exception as e:
            log.error(f"Failed to capture screenshot: {e}")
            return None

    def get_recent(self, count: int = 5) -> List[ScreenshotEntry]:
        """
        Get the N most recent screenshot entries.

        Args:
            count: Maximum number of screenshots to return

        Returns:
            List of ScreenshotEntry objects (oldest to newest)
        """
        # Return as list, limited to count, filtering for existing files
        entries = [e for e in self._buffer if e.exists()]
        return entries[-count:] if len(entries) > count else entries

    def get_gallery_paths(self, count: int = 5) -> List[str]:
        """
        Get paths to recent screenshots for a gallery post.

        Args:
            count: Maximum number of paths to return

        Returns:
            List of file paths (oldest to newest)
        """
        entries = self.get_recent(count)
        return [e.path for e in entries]

    def get_latest(self) -> Optional[ScreenshotEntry]:
        """
        Get the most recent screenshot entry.

        Returns:
            ScreenshotEntry if available, None otherwise
        """
        if self._buffer:
            entry = self._buffer[-1]
            if entry.exists():
                return entry
        return None

    def get_latest_path(self) -> Optional[str]:
        """
        Get path to the most recent screenshot.

        Returns:
            Path string if available, None otherwise
        """
        entry = self.get_latest()
        return entry.path if entry else None

    def get_journey_summary(self) -> dict:
        """
        Get a summary of the screenshots in the buffer for progress posts.

        Returns:
            Dictionary with journey metadata
        """
        entries = self.get_recent()

        if not entries:
            return {
                "has_screenshots": False,
                "count": 0,
            }

        # Get unique locations visited
        locations = []
        seen_maps = set()
        for entry in entries:
            if entry.map_name and entry.map_name not in seen_maps:
                seen_maps.add(entry.map_name)
                locations.append(entry.map_name)

        return {
            "has_screenshots": True,
            "count": len(entries),
            "paths": [e.path for e in entries],
            "first_cycle": entries[0].cycle_number,
            "last_cycle": entries[-1].cycle_number,
            "first_action": entries[0].action_number,
            "last_action": entries[-1].action_number,
            "locations_visited": locations,
            "timespan_seconds": entries[-1].timestamp - entries[0].timestamp,
        }

    def clear(self):
        """Clear the buffer (does not delete files)."""
        self._buffer.clear()
        log.info("Screenshot buffer cleared")

    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Clean up old gallery files beyond a certain age.

        Args:
            max_age_hours: Maximum age in hours before files are deleted
        """
        if not self.gallery_dir.exists():
            return

        cutoff = time.time() - (max_age_hours * 3600)
        deleted = 0

        for file in self.gallery_dir.glob("gallery_*.png"):
            try:
                if file.stat().st_mtime < cutoff:
                    # Don't delete if it's in our current buffer
                    buffer_paths = {e.path for e in self._buffer}
                    if str(file) not in buffer_paths:
                        file.unlink()
                        deleted += 1
            except Exception as e:
                log.warning(f"Failed to cleanup {file}: {e}")

        if deleted > 0:
            log.info(f"Cleaned up {deleted} old gallery screenshots")

    def get_stats(self) -> dict:
        """Get manager statistics."""
        return {
            "buffer_size": len(self._buffer),
            "max_screenshots": self.max_screenshots,
            "total_captures": self._total_captures,
            "gallery_dir": str(self.gallery_dir),
        }


# Singleton instance
_screenshot_manager: Optional[ScreenshotManager] = None


def get_screenshot_manager(
    gallery_dir: str = "data/zora_gallery",
    max_screenshots: int = 5,
) -> ScreenshotManager:
    """
    Get or create the singleton screenshot manager instance.

    Args:
        gallery_dir: Directory for gallery screenshots
        max_screenshots: Maximum screenshots to retain

    Returns:
        ScreenshotManager instance
    """
    global _screenshot_manager
    if _screenshot_manager is None:
        _screenshot_manager = ScreenshotManager(
            gallery_dir=gallery_dir,
            max_screenshots=max_screenshots,
        )
    return _screenshot_manager
