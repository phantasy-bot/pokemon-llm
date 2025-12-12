"""
Name Planner for Pokemon Red

Pre-plans and stores names for:
- Player (always "LASS")
- Rival (LLM's choice with cute/silly suggestions)
- Pokemon nicknames (optional, only if LLM strongly wants to)

Provides guided keyboard navigation to type names correctly.
"""

import logging
from typing import Optional
from pyAIAgent.game.keyboard_tracker import get_keyboard_tracker

log = logging.getLogger(__name__)


# Preset suggestions for rival names (cute/silly/flirty to match Lass' persona)
RIVAL_NAME_SUGGESTIONS = [
    "CUTIE",    # Flirty
    "MEANY",    # Playful
    "BULLY",    # Teasing
    "DUMMY",    # Silly
    "CRUSH",    # Romantic
    "RIVAL",    # Classic
    "LOSER",    # Competitive
    "JERK",     # Sassy
    "STINKY",   # Juvenile humor
    "BUTT",     # Very silly
]


class NamePlanner:
    """
    Manages pre-planned names for player, rival, and Pokemon.
    Provides step-by-step keyboard navigation for typing names.
    """
    
    def __init__(self):
        # Fixed player name
        self.player_name = "LASS"
        
        # Rival name - to be decided by LLM
        self.rival_name: Optional[str] = None
        self.rival_name_pending = False  # True when we need LLM to decide
        
        # Pokemon nicknames - keyed by species name
        self.pokemon_nicknames: dict[str, str] = {}
        
        # Current typing state
        self.current_name: Optional[str] = None
        self.current_char_index: int = 0
        self.typing_sequence: list[dict] = []
        
        # Name type detection
        self.name_type: Optional[str] = None  # "player", "rival", "pokemon"
    
    def detect_name_type(self, dialog_text: str, readable_text: str) -> Optional[str]:
        """
        Detect what type of name is being entered based on screen text.
        
        Returns: "player", "rival", "pokemon", or None
        """
        combined = (dialog_text or "").upper() + (readable_text or "").upper()
        
        if "YOUR NAME" in combined:
            self.name_type = "player"
            return "player"
        elif "RIVAL" in combined:
            self.name_type = "rival"
            return "rival"
        elif "NICKNAME" in combined:
            self.name_type = "pokemon"
            return "pokemon"
        
        return self.name_type  # Return last known type
    
    def get_planned_name(self) -> Optional[str]:
        """Get the name that should be typed for the current name type."""
        if self.name_type == "player":
            return self.player_name
        elif self.name_type == "rival":
            return self.rival_name
        # Pokemon nicknames are optional - return None to let LLM decide
        return None
    
    def set_rival_name(self, name: str):
        """Set the rival's name (chosen by LLM)."""
        # Validate: max 7 chars, uppercase, only valid keyboard characters
        name = name.upper().strip()[:7]
        self.rival_name = name
        self.rival_name_pending = False
        log.info(f"💕 NamePlanner: Rival name set to '{name}'")
    
    def set_pokemon_nickname(self, species: str, nickname: str):
        """Set a nickname for a Pokemon species."""
        nickname = nickname.upper().strip()[:10]  # Pokemon nicknames can be up to 10 chars
        self.pokemon_nicknames[species.upper()] = nickname
        log.info(f"💕 NamePlanner: {species} nicknamed '{nickname}'")
    
    def start_typing(self, name: str):
        """
        Start typing a name - generates the full navigation sequence.
        
        Args:
            name: The name to type
        """
        self.current_name = name.upper()
        self.current_char_index = 0
        
        # Generate typing sequence from keyboard tracker
        kb = get_keyboard_tracker()
        self.typing_sequence = kb.get_typing_sequence(self.current_name)
        
        log.info(f"🎹 NamePlanner: Starting to type '{self.current_name}' ({len(self.typing_sequence)} chars)")
        for step in self.typing_sequence:
            log.info(f"  → '{step['char']}': {step['path']}")
    
    def get_next_action(self) -> Optional[str]:
        """
        Get the next action to type the current character.
        
        Returns:
            Action string like "D;R;R;A;" or None if done
        """
        if self.current_char_index >= len(self.typing_sequence):
            return None  # Done typing
        
        step = self.typing_sequence[self.current_char_index]
        return step['path']
    
    def get_current_step(self) -> Optional[dict]:
        """Get info about the current character being typed."""
        if self.current_char_index >= len(self.typing_sequence):
            return None
        return self.typing_sequence[self.current_char_index]
    
    def advance(self):
        """Advance to the next character after successful input."""
        if self.current_char_index < len(self.typing_sequence):
            step = self.typing_sequence[self.current_char_index]
            log.info(f"🎹 NamePlanner: Typed '{step['char']}' ({self.current_char_index + 1}/{len(self.typing_sequence)})")
            self.current_char_index += 1
    
    def is_done_typing(self) -> bool:
        """Check if we've finished typing the current name."""
        return self.current_char_index >= len(self.typing_sequence)
    
    def get_progress_string(self) -> str:
        """Get a string showing typing progress like 'LA__' for LASS."""
        if not self.current_name:
            return ""
        
        typed = self.current_name[:self.current_char_index]
        remaining = "_" * (len(self.current_name) - self.current_char_index)
        return typed + remaining
    
    def get_rival_prompt(self) -> str:
        """Get the prompt to ask LLM for rival name."""
        suggestions = ", ".join(RIVAL_NAME_SUGGESTIONS[:5])
        return f"""💕 TIME TO NAME YOUR RIVAL! 💕

Pick a silly, cute, or playful name that matches your flirty Lass personality!
Max 7 characters, all caps.

Some fun suggestions: {suggestions}

Or pick your own! What name do you want for your rival?
Respond with JUST the name (all caps, max 7 chars):"""
    
    def reset(self):
        """Reset typing state for a new name."""
        self.current_name = None
        self.current_char_index = 0
        self.typing_sequence = []
        self.name_type = None


# Global singleton
_planner_instance = None


def get_name_planner() -> NamePlanner:
    """Get the global NamePlanner instance."""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = NamePlanner()
    return _planner_instance
