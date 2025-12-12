from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

@dataclass
class Memory:
    """Base memory structure"""
    type: str
    location: Optional[str]
    description: str
    coordinates: Optional[List[int]]
    timestamp: str
    importance: float = 1.0
    context: Optional[Dict[str, Any]] = None


@dataclass
class SpatialMemory(Memory):
    """Spatial memory for map connections and locations"""
    destination: Optional[str] = None
    landmark_type: Optional[str] = None  # e.g., "door", "stairs", "pokemon_center"
    # Confidence scoring for memory reliability
    confidence: float = 0.5  # 0.0-1.0 scale
    verification_source: str = "unverified"  # "verified_transition", "vision", "llm_claim"
    failed_attempts: int = 0  # Track failures per-memory
    last_verified_at: Optional[str] = None  # Timestamp of last successful use


@dataclass
class GameplayMemory(Memory):
    """Gameplay memory for battles, items, events"""
    event_type: Optional[str] = None  # e.g., "battle", "item_found", "level_up"
    outcome: Optional[str] = None
    pokemon_involved: Optional[List[str]] = None


@dataclass
class QuestMemory(Memory):
    """Quest memory for tracking active quests and quest items.
    
    When the agent receives a quest item like Oak's Parcel, this creates:
    1. A QuestMemory to remember we have the item
    2. An associated Goal to complete the quest
    """
    quest_id: str = ""  # Unique ID like "oaks_parcel_delivery"
    quest_type: str = ""  # "delivery", "fetch", "defeat", "explore", "item_received"
    target_npc: Optional[str] = None  # Who to deliver to or talk to
    target_location: Optional[str] = None  # Where to go
    item_involved: Optional[str] = None  # What item is involved
    is_active: bool = True  # Is quest still pending
    completed_at: Optional[str] = None  # When completed


@dataclass
class NarrativeMemory(Memory):
    """Narrative memory for story events, dialogue, and player mistakes.
    
    Used for:
    - Remembering rival name choices ("Named rival AB")
    - Significant dialogue events ("Oak forgot grandson's name")
    - Funny mistakes ("I walked into a wall for 5 minutes")
    """
    event_type: str = "general"  # narrative, dialogue, mistake, milestone
    characters_involved: Optional[List[str]] = None
    emotional_tone: str = "neutral"  # happy, frustrated, confused, proud


@dataclass
class StrategyMemory:
    """
    Memory for learned strategies - discovered through experience, not hard-coded.
    Tracks situation → action → outcome patterns so agent can learn what works.
    """
    strategy_id: str  # Unique identifier
    situation: str  # What situation triggered this (e.g., "lost, low HP, far from Pokemon Center")
    action_taken: str  # What the agent did (e.g., "let Pokemon faint in wild battle")
    outcome: str  # What happened (e.g., "respawned at Pokemon Center, full heal")
    
    # Learning metrics
    times_used: int = 1  # How many times this strategy was used
    times_successful: int = 1  # How many times it worked
    effectiveness: float = 1.0  # success rate (0.0-1.0)
    
    # Context
    discovered_at: str = ""  # Timestamp when first discovered
    last_used_at: str = ""  # Timestamp of last use
    tags: Optional[List[str]] = None  # e.g., ["healing", "navigation", "shortcut"]
    notes: Optional[str] = None  # Additional context
    
    def update_effectiveness(self, success: bool):
        """Update strategy effectiveness after use"""
        self.times_used += 1
        if success:
            self.times_successful += 1
        self.effectiveness = self.times_successful / self.times_used


@dataclass
class VisionClaim:
    """
    Track unverified claims from vision analysis that need verification.
    These are things the vision model claims to see (doors, exits) that should
    be verified against minimap data before being trusted.
    """
    claim_type: str  # "door", "exit", "npc", "item"
    description: str
    location: str
    coordinates: Optional[List[int]]
    direction: Optional[str]  # Direction from player (north, south, etc.)
    timestamp: str
    verified: bool = False
    verification_result: Optional[bool] = None  # True=correct, False=wrong, None=unverified
    confidence: float = 0.5  # How confident we are in this claim
    context: Optional[Dict[str, Any]] = None
