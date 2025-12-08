"""
Screenshot History Tracker for Enhanced Vision Flow

Tracks screenshot history between cycles to enable ui_diff_check comparisons.
Maintains up to 5 cycles (N through N-4) for multi-diff temporal analysis.
"""

import os
import logging
from typing import Optional, List, Tuple
from pathlib import Path

log = logging.getLogger('history_tracker')


class ScreenshotHistoryTracker:
    """
    Tracks screenshot paths across agent cycles.
    
    Keeps references to the last N cycles (configurable, default 5) to enable
    multi-diff UI analysis for detecting movement patterns and loops.
    """
    
    def __init__(self, snapshot_dir: str = "snapshots", max_history: int = 5):
        """
        Initialize the tracker.
        
        Args:
            snapshot_dir: Directory where snapshots are stored
            max_history: Number of cycles to keep (default 5 for N through N-4)
        """
        self.snapshot_dir = snapshot_dir
        self.max_history = max_history
        # List of (cycle_num, path) tuples, newest first
        self.history: List[Tuple[int, str]] = []
        
        # Ensure snapshot directory exists
        os.makedirs(snapshot_dir, exist_ok=True)
        log.info(f"📸 Screenshot history tracker initialized (dir: {snapshot_dir}, max: {max_history})")
    
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
                    combined_path = old_path.replace('.png', '_with_minimap.png')
                    if os.path.exists(combined_path):
                        os.remove(combined_path)
                    log.debug(f"🧹 Cleaned up old snapshot: {old_path} (cycle {old_cycle})")
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
    
    def get_all_previous(self) -> List[Tuple[int, str]]:
        """
        Get all previous screenshots (N-1 through N-4).
        
        Returns:
            List of (cycle_num, path) tuples for all available previous screenshots
        """
        result = []
        for i in range(1, len(self.history)):
            cycle_num, path = self.history[i]
            if os.path.exists(path):
                result.append((cycle_num, path))
        return result
    
    def get_diff_pairs(self) -> List[Tuple[int, str, str]]:
        """
        Get all screenshot pairs for diff analysis.
        
        Returns:
            List of (prev_cycle, prev_path, curr_path) tuples for all available diffs
        """
        if not self.history:
            return []
        
        curr_path = self.history[0][1]
        if not os.path.exists(curr_path):
            return []
        
        pairs = []
        for prev_cycle, prev_path in self.get_all_previous():
            pairs.append((prev_cycle, prev_path, curr_path))
        
        return pairs
    
    def has_previous(self) -> bool:
        """Check if a previous screenshot is available for diff."""
        return len(self.history) >= 2 and os.path.exists(self.history[1][1])
    
    def get_history_depth(self) -> int:
        """Get how many cycles of history are available."""
        return len(self.history)
    
    def get_cycle_info(self) -> dict:
        """Get current tracking state for debugging."""
        return {
            "history_depth": len(self.history),
            "cycles": [c for c, _ in self.history],
            "current_cycle": self.history[0][0] if self.history else None,
            "has_diffs": self.has_previous()
        }
