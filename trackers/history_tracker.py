"""
Screenshot History Tracker

Tracks screenshot history between cycles.
Maintains history for cleanup and reference.
"""

import os
import logging
from typing import Optional, List, Tuple
from pathlib import Path

log = logging.getLogger("history_tracker")


class ScreenshotHistoryTracker:
    """
    Tracks screenshot paths across agent cycles.
    """

    def __init__(self, snapshot_dir: str = "snapshots", max_history: int = 2):
        """
        Initialize the tracker.

        Args:
            snapshot_dir: Directory where snapshots are stored
            max_history: Number of cycles to keep (default 2)
        """
        self.snapshot_dir = snapshot_dir
        self.max_history = max_history
        # List of (cycle_num, path) tuples, newest first
        self.history: List[Tuple[int, str]] = []

        # Ensure snapshot directory exists
        os.makedirs(snapshot_dir, exist_ok=True)
        log.info(
            f"📸 Screenshot history tracker initialized (dir: {snapshot_dir}, max: {max_history})"
        )

    def add_screenshot(self, cycle_num: int, path: str) -> None:
        """
        Register a new screenshot for the given cycle.

        Adds to front of history, trims to max_history, and cleans up old files.

        Args:
            cycle_num: Current cycle number
            path: Path to the screenshot file
        """
        # Add new entry at front
        self.history.insert(0, (cycle_num, path))

        log.debug(f"📸 Registered screenshot: cycle {cycle_num} -> {path}")

        # Cleanup entries beyond max_history
        while len(self.history) > self.max_history:
            old_cycle, old_path = self.history.pop()
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                    # Also clean up any combined versions
                    combined_path = old_path.replace(".png", "_with_minimap.png")
                    if os.path.exists(combined_path):
                        os.remove(combined_path)
                    log.debug(
                        f"🧹 Cleaned up old snapshot: {old_path} (cycle {old_cycle})"
                    )
                except OSError as e:
                    log.warning(f"Failed to cleanup old snapshot {old_path}: {e}")

    def get_current_screenshot(self) -> Optional[str]:
        """
        Get the path to the current cycle's screenshot (N).

        Returns:
            Path to current screenshot if available and exists, None otherwise
        """
        if self.history and os.path.exists(self.history[0][1]):
            return self.history[0][1]
        return None

    def get_previous_screenshot(self) -> Optional[str]:
        """
        Get the path to the previous cycle's screenshot (N-1).

        Returns:
            Path to previous screenshot if available and exists, None otherwise
        """
        if len(self.history) >= 2 and os.path.exists(self.history[1][1]):
            return self.history[1][1]
        return None
