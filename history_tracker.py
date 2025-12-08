"""
Screenshot History Tracker for Enhanced Vision Flow

Tracks screenshot history between cycles to enable ui_diff_check comparisons.
Maintains cycle N (current) and N-1 (previous) screenshots for temporal analysis.
"""

import os
import logging
from typing import Optional, Tuple
from pathlib import Path

log = logging.getLogger('history_tracker')


class ScreenshotHistoryTracker:
    """
    Tracks screenshot paths across agent cycles.
    
    Keeps references to current (N) and previous (N-1) cycle screenshots
    to enable UI diff analysis while managing disk cleanup.
    """
    
    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = snapshot_dir
        self.current_cycle: Optional[int] = None
        self.current_path: Optional[str] = None
        self.previous_cycle: Optional[int] = None
        self.previous_path: Optional[str] = None
        
        # Ensure snapshot directory exists
        os.makedirs(snapshot_dir, exist_ok=True)
        log.info(f"📸 Screenshot history tracker initialized (dir: {snapshot_dir})")
    
    def add_screenshot(self, cycle_num: int, path: str) -> None:
        """
        Register a new screenshot for the given cycle.
        
        Shifts current → previous, then sets new current.
        Cleans up cycle N-2 and older to prevent disk bloat.
        
        Args:
            cycle_num: Current cycle number
            path: Path to the screenshot file
        """
        # Shift current to previous
        old_previous_path = self.previous_path
        self.previous_cycle = self.current_cycle
        self.previous_path = self.current_path
        
        # Set new current
        self.current_cycle = cycle_num
        self.current_path = path
        
        log.debug(f"📸 Registered screenshot: cycle {cycle_num} -> {path}")
        
        # Cleanup N-2 (the old previous) to keep only N and N-1
        if old_previous_path and os.path.exists(old_previous_path):
            try:
                os.remove(old_previous_path)
                # Also clean up any combined versions
                combined_path = old_previous_path.replace('.png', '_with_minimap.png')
                if os.path.exists(combined_path):
                    os.remove(combined_path)
                log.debug(f"🧹 Cleaned up old snapshot: {old_previous_path}")
            except OSError as e:
                log.warning(f"Failed to cleanup old snapshot {old_previous_path}: {e}")
    
    def get_previous_screenshot(self) -> Optional[str]:
        """
        Get the path to the previous cycle's screenshot.
        
        Returns:
            Path to previous screenshot if available and exists, None otherwise
        """
        if self.previous_path and os.path.exists(self.previous_path):
            return self.previous_path
        return None
    
    def get_current_screenshot(self) -> Optional[str]:
        """
        Get the path to the current cycle's screenshot.
        
        Returns:
            Path to current screenshot if available and exists, None otherwise
        """
        if self.current_path and os.path.exists(self.current_path):
            return self.current_path
        return None
    
    def get_diff_pair(self) -> Optional[Tuple[str, str]]:
        """
        Get both screenshots for diff comparison.
        
        Returns:
            Tuple of (previous_path, current_path) if both exist, None otherwise
        """
        prev = self.get_previous_screenshot()
        curr = self.get_current_screenshot()
        
        if prev and curr:
            return (prev, curr)
        return None
    
    def has_previous(self) -> bool:
        """Check if a previous screenshot is available for diff."""
        return self.get_previous_screenshot() is not None
    
    def get_cycle_info(self) -> dict:
        """Get current tracking state for debugging."""
        return {
            "current_cycle": self.current_cycle,
            "current_path": self.current_path,
            "previous_cycle": self.previous_cycle,
            "previous_path": self.previous_path,
            "has_diff_pair": self.has_previous()
        }
