"""
Keyboard Cursor Tracker for Pokemon Red Name Entry Screen

Since the game's memory addresses for keyboard cursor position are not reliably
accessible (CC24-CC26 work for menus but not for the name entry keyboard grid),
this module provides a simulated cursor tracker that:

1. Starts at 'A' (row=0, col=0) when name entry is detected
2. Parses LLM actions (D/U/L/R) to update simulated position  
3. Provides accurate position to the LLM context

This is used as a fallback when memory-based cursor detection fails.
"""

import logging

log = logging.getLogger(__name__)


class KeyboardCursorTracker:
    """
    Tracks cursor position on the name entry keyboard by simulating button presses.
    
    The Pokemon Red name entry keyboard layout is:
    Row 0: A B C D E F G H I  (indices 0-8)
    Row 1: J K L M N O P Q R  (indices 9-17)
    Row 2: S T U V W X Y Z _  (indices 18-26, _ = space)
    Row 3: × ( ) : ; [ ] pk mn (indices 27-35)
    Row 4: - ? ! ♂ ♀ / . , ED  (indices 36-44)
    
    Cursor starts at 'A' when entering the keyboard.
    """
    
    # Keyboard layout - each row has 9 characters
    KEYBOARD_LAYOUT = [
        "ABCDEFGHI",   # Row 0
        "JKLMNOPQR",   # Row 1
        "STUVWXYZ ",   # Row 2 (space at end)
        "×():;[]PM",   # Row 3 (pk mn simplified as P M)
        "-?!♂♀/.,E",   # Row 4 (ED simplified as E)
    ]
    
    ROWS = 5
    COLS = 9
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset cursor to initial position (A) at row=0, col=0"""
        self.row = 0
        self.col = 0
        self.active = False
        self._last_logged_position = None
        log.info("🎹 KeyboardTracker: Reset to initial position 'A' (row=0, col=0)")
    
    def activate(self):
        """Activate tracking when name entry screen is detected"""
        if not self.active:
            self.reset()
            self.active = True
            log.info("🎹 KeyboardTracker: Activated - tracking name entry keyboard")
    
    def deactivate(self):
        """Deactivate tracking when leaving name entry screen"""
        if self.active:
            self.active = False
            log.info("🎹 KeyboardTracker: Deactivated")
    
    def apply_action(self, action: str) -> None:
        """
        Parse action string and update cursor position.
        
        Handles D (down), U (up), L (left), R (right) movements.
        A button selects a character but doesn't move cursor.
        B button deletes but doesn't move cursor.
        
        Args:
            action: Action string like "D;R;R;A" or "DRRA"
        """
        if not self.active:
            return
        
        old_row, old_col = self.row, self.col
        
        # Parse each character, ignoring semicolons and spaces
        for char in action.upper():
            if char == 'D':  # Down
                self.row = min(self.row + 1, self.ROWS - 1)
            elif char == 'U':  # Up
                self.row = max(self.row - 1, 0)
            elif char == 'R':  # Right
                self.col = min(self.col + 1, self.COLS - 1)
            elif char == 'L':  # Left
                self.col = max(self.col - 1, 0)
            # A, B, S, T, etc. don't affect cursor position
        
        # Log if position changed
        if (self.row, self.col) != (old_row, old_col):
            new_char = self.get_char()
            log.info(f"🎹 KeyboardTracker: Moved ({old_row},{old_col}) -> ({self.row},{self.col}) = '{new_char}'")
    
    def get_position(self) -> tuple[int, int]:
        """Get current cursor position as (row, col) tuple (0-indexed)"""
        return (self.row, self.col)
    
    def get_char(self) -> str:
        """Get the character at current cursor position"""
        if 0 <= self.row < len(self.KEYBOARD_LAYOUT):
            row_str = self.KEYBOARD_LAYOUT[self.row]
            if 0 <= self.col < len(row_str):
                return row_str[self.col]
        return "?"
    
    def get_index(self) -> int:
        """Get linear index (0-44) of current position"""
        return self.row * self.COLS + self.col
    
    def get_state_dict(self) -> dict:
        """Get current state as a dictionary for use in name_entry_state"""
        char = self.get_char()
        return {
            "cursor_index": self.get_index(),
            "tracked_row": self.row,
            "tracked_col": self.col,
            "selected_char": char,
            "row": self.row + 1,  # 1-indexed for human readability
            "col": self.col + 1,  # 1-indexed for human readability
            "is_tracked": True,
            "is_name_entry": True
        }
    
    def __repr__(self):
        return f"KeyboardCursorTracker(row={self.row}, col={self.col}, char='{self.get_char()}')"


# Global singleton instance for use across the application
_tracker_instance = None


def get_keyboard_tracker() -> KeyboardCursorTracker:
    """Get the global KeyboardCursorTracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = KeyboardCursorTracker()
    return _tracker_instance
