"""
Memory Management System for Pokemon LLM Agent

This module provides comprehensive memory management for the Pokemon playing agent,
including spatial learning, gameplay memories, and persistent storage.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict

# Setup logger
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("memory_storage")


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



class MemoryManager:
    """Comprehensive memory management system for Pokemon LLM agent"""

    def __init__(self, storage_path: str = "data/pokemon_memories.json", reset_on_start: bool = True):
        self.storage_path = storage_path
        self.memories = {
            "spatial": [],
            "gameplay": [],
            "narrative": [],
            "tactical": [],
            "quests": []  # Quest items and active quests (Oak's Parcel, etc.)
        }
        # Track vision claims that need verification
        self.vision_claims: List[VisionClaim] = []
        # Track vision accuracy statistics
        self.vision_stats = {
            "total_claims": 0,
            "verified_correct": 0,
            "verified_wrong": 0,
            "unverified": 0
        }
        # Track failed exit attempts: key = (map_name, coords_tuple), value = failure count
        self.failed_exit_attempts: Dict[tuple, int] = {}
        # Track positions we've tried to exit from in recent cycles (for pattern detection)
        self.recent_exit_attempts: List[tuple] = []  # (map_name, coords, cycle)
        # Track NPC interactions: key = (map_name, coords_tuple), value = interaction count
        self.npc_interactions: Dict[tuple, int] = {}
        # Threshold for warning about repeated NPC interactions
        self.NPC_INTERACTION_THRESHOLD = 2
        
        # === NEW: Confidence-based memory system ===
        # Confidence decay rates per verification source (more trusted = slower decay)
        self.CONFIDENCE_DECAY_RATES = {
            "verified_transition": 0.1,   # Slow decay - we SAW this work
            "vision": 0.2,                # Medium decay - vision can hallucinate
            "llm_claim": 0.3,             # Fast decay - least trusted
            "unverified": 0.25
        }
        # Thresholds for memory lifecycle
        self.LOW_CONFIDENCE_THRESHOLD = 0.3  # Warn LLM this memory is questionable
        self.QUARANTINE_THRESHOLD = 0.15     # Move to quarantine below this
        self.DELETE_THRESHOLD = 0.05         # Delete if confirmed wrong at this level
        self.REVALIDATION_THRESHOLD = 0.6    # Restore from quarantine above this
        
        # Quarantine for suspect memories (not deleted, but not trusted)
        self.quarantined_memories: List[SpatialMemory] = []
        
        # Track which approach directions have been tried at each exit
        # Key: (map_name, coords_tuple), Value: set of directions tried
        self.tried_approach_directions: Dict[tuple, set] = {}
        
        # === LASS MARKINGS: Visual overlay markers for minimap ===
        # Key: (map_name, (x, y)), Value: {"type": "N"|"O", "timestamp": iso_str, "confidence": 0.0-1.0}
        # N = NPC (discovered via A-press dialogue)
        # O = Opening/Exit (verified transition or known exit)
        self.lass_markings: Dict[tuple, Dict] = {}
        
        # === Strategy Learning System ===
        # Stores learned strategies (discovered through experience)
        self.strategies: List[StrategyMemory] = []
        
        # Track pending outcomes - actions that might lead to learning
        # Key: action_id, Value: {situation, action, timestamp, context}
        self.pending_outcomes: Dict[str, Dict] = {}
        
        # Outcome tracking - recent significant events for reflection
        self.recent_outcomes: List[Dict] = []  # Last 10 outcomes
        
        if reset_on_start:
            # Clear memories for fresh start
            self._save_memories()
            log.info("🧹 Memories reset for fresh session")
        else:
            self.load_memories()

    def record_failed_exit_attempt(self, map_name: str, coordinates: List[int], 
                                     approach_direction: Optional[str] = None) -> dict:
        """
        Record that an exit attempt at these coordinates failed.
        Uses confidence decay instead of binary invalidation.
        
        Returns dict with:
        - status: "decayed", "low_confidence", "quarantined", "try_different_direction"
        - suggestion: Human-readable suggestion for LLM
        - untried_directions: List of approach directions not yet tried
        """
        if not coordinates or len(coordinates) < 2:
            return {"status": "error", "suggestion": "Invalid coordinates"}
        
        key = (map_name.upper(), tuple(coordinates))
        
        # Track which approach direction was tried
        if approach_direction:
            if key not in self.tried_approach_directions:
                self.tried_approach_directions[key] = set()
            self.tried_approach_directions[key].add(approach_direction.upper())
        
        # Find the memory for this exit
        matching_memory = self._find_exit_memory(map_name, coordinates)
        
        if not matching_memory:
            # No memory to decay - just track failure count
            self.failed_exit_attempts[key] = self.failed_exit_attempts.get(key, 0) + 1
            return {"status": "no_memory", "suggestion": "No exit memory at this location"}
        
        # Increment failure counter on the memory itself
        matching_memory.failed_attempts += 1
        
        # Calculate decay based on verification source
        decay_rate = self.CONFIDENCE_DECAY_RATES.get(
            matching_memory.verification_source, 
            self.CONFIDENCE_DECAY_RATES["unverified"]
        )
        old_confidence = matching_memory.confidence
        matching_memory.confidence = max(0.0, matching_memory.confidence - decay_rate)
        
        log.info(f"⚠️ Exit attempt failed at {map_name} {coordinates}: "
                f"confidence {old_confidence:.2f} → {matching_memory.confidence:.2f} "
                f"(source: {matching_memory.verification_source}, attempts: {matching_memory.failed_attempts})")
        
        # Check if we should suggest trying different approach directions
        all_directions = {"NORTH", "SOUTH", "EAST", "WEST"}
        tried = self.tried_approach_directions.get(key, set())
        untried = all_directions - tried
        
        # Before quarantining, suggest trying other directions
        if untried and matching_memory.confidence > self.QUARANTINE_THRESHOLD:
            return {
                "status": "try_different_direction",
                "suggestion": f"Exit at {coordinates} might work from a different direction. "
                             f"Tried: {sorted(tried)}. Try approaching from: {sorted(untried)[0]}",
                "untried_directions": sorted(untried),
                "memory": matching_memory
            }
        
        # Check thresholds
        if matching_memory.confidence <= self.DELETE_THRESHOLD:
            # Confirmed wrong - delete
            self._delete_exit_memory(map_name, coordinates)
            return {
                "status": "deleted",
                "suggestion": f"❌ Memory DELETED: Exit at {coordinates} confirmed false after {matching_memory.failed_attempts} attempts. "
                             f"This was likely a cutscene teleport. Explore for REAL exits!",
                "untried_directions": []
            }
        
        if matching_memory.confidence <= self.QUARANTINE_THRESHOLD:
            # Move to quarantine
            self._quarantine_exit_memory(map_name, coordinates, 
                                        reason=f"Failed {matching_memory.failed_attempts} times, tried directions: {sorted(tried)}")
            return {
                "status": "quarantined", 
                "suggestion": f"🔒 Memory QUARANTINED: Exit at {coordinates} is unreliable (confidence: {matching_memory.confidence:.2f}). "
                             f"It might be a false memory from a cutscene. Look for other exits on the minimap or in memory.",
                "untried_directions": sorted(untried)
            }
        
        if matching_memory.confidence <= self.LOW_CONFIDENCE_THRESHOLD:
            self._save_memories()
            return {
                "status": "low_confidence",
                "suggestion": f"⚠️ Low confidence ({matching_memory.confidence:.2f}) in exit at {coordinates}. "
                             f"This might be wrong. Consider exploring other areas first.",
                "untried_directions": sorted(untried)
            }
        
        self._save_memories()
        return {
            "status": "decayed",
            "suggestion": f"Exit at {coordinates} didn't work this time (confidence: {matching_memory.confidence:.2f}). "
                         f"Try again or approach from a different direction.",
            "untried_directions": sorted(untried)
        }
    
    def _find_exit_memory(self, map_name: str, coordinates: List[int]) -> Optional[SpatialMemory]:
        """Find a spatial memory matching these coordinates."""
        coords_tuple = tuple(coordinates)
        map_upper = map_name.upper()
        
        for mem in self.memories["spatial"]:
            if mem.coordinates and tuple(mem.coordinates) == coords_tuple:
                if mem.location and map_upper in mem.location.upper():
                    if mem.landmark_type in ("exit", "entrance", "door", "stairs", None):
                        return mem
        return None
    
    def _quarantine_exit_memory(self, map_name: str, coordinates: List[int], reason: str) -> None:
        """Move a suspect memory to quarantine instead of deleting."""
        coords_tuple = tuple(coordinates)
        map_upper = map_name.upper()
        
        to_quarantine = []
        for i, mem in enumerate(self.memories["spatial"]):
            if mem.coordinates and tuple(mem.coordinates) == coords_tuple:
                is_our_map = mem.location and map_upper in mem.location.upper()
                if is_our_map and mem.landmark_type in ("exit", "entrance", "door", "stairs", None):
                    to_quarantine.append(i)
        
        # Move to quarantine in reverse order
        to_quarantine.sort(reverse=True)
        for i in to_quarantine:
            mem = self.memories["spatial"].pop(i)
            mem.context = mem.context or {}
            mem.context["quarantine_reason"] = reason
            mem.context["quarantined_at"] = datetime.now().isoformat()
            self.quarantined_memories.append(mem)
            log.warning(f"🔒 QUARANTINED memory: {mem.description} (reason: {reason})")
        
        if to_quarantine:
            self._save_memories()
    
    def _delete_exit_memory(self, map_name: str, coordinates: List[int]) -> None:
        """Permanently delete a confirmed-false memory."""
        coords_tuple = tuple(coordinates)
        map_upper = map_name.upper()
        
        to_remove = []
        for i, mem in enumerate(self.memories["spatial"]):
            if mem.coordinates and tuple(mem.coordinates) == coords_tuple:
                is_our_map = mem.location and map_upper in mem.location.upper()
                if is_our_map:
                    to_remove.append(i)
        
        # Also remove from quarantine
        self.quarantined_memories = [
            m for m in self.quarantined_memories 
            if not (m.coordinates and tuple(m.coordinates) == coords_tuple and 
                   m.location and map_upper in m.location.upper())
        ]
        
        to_remove.sort(reverse=True)
        for i in to_remove:
            removed = self.memories["spatial"].pop(i)
            log.warning(f"🗑️ DELETED false memory: {removed.description}")
        
        if to_remove:
            self._save_memories()
    
    def reset_failed_attempts(self, map_name: str, coordinates: List[int]) -> None:
        """
        Reset failed attempt counter for a location when exit actually works.
        Also boosts confidence of the memory and attempts to rehabilitate quarantined memories.
        """
        key = (map_name.upper(), tuple(coordinates))
        
        # Reset failure tracking
        if key in self.failed_exit_attempts:
            del self.failed_exit_attempts[key]
        if key in self.tried_approach_directions:
            del self.tried_approach_directions[key]
        
        # Boost confidence of the memory that just worked
        memory = self._find_exit_memory(map_name, coordinates)
        if memory:
            old_confidence = memory.confidence
            # Boost confidence significantly - this exit WORKS
            memory.confidence = min(1.0, memory.confidence + 0.3)
            memory.verification_source = "verified_transition"
            memory.last_verified_at = datetime.now().isoformat()
            memory.failed_attempts = 0  # Reset failure count
            log.info(f"✅ Exit VERIFIED at {map_name} {coordinates}: "
                    f"confidence {old_confidence:.2f} → {memory.confidence:.2f}")
            self._save_memories()
        
        # Check if this exit was quarantined and should be rehabilitated
        self._attempt_revalidation(map_name, coordinates)
    
    def _attempt_revalidation(self, map_name: str, coordinates: List[int]) -> bool:
        """
        If a quarantined memory matches this location and it just worked,
        restore it with boosted confidence.
        """
        coords_tuple = tuple(coordinates)
        map_upper = map_name.upper()
        
        for i, mem in enumerate(self.quarantined_memories):
            if (mem.coordinates and tuple(mem.coordinates) == coords_tuple and
                mem.location and map_upper in mem.location.upper()):
                # Found a quarantined memory that just worked! Rehabilitate it.
                mem.confidence = self.REVALIDATION_THRESHOLD + 0.1
                mem.verification_source = "verified_transition"
                mem.last_verified_at = datetime.now().isoformat()
                mem.failed_attempts = 0
                mem.context = mem.context or {}
                mem.context["rehabilitated_at"] = datetime.now().isoformat()
                mem.context["quarantine_reason"] = None  # Clear quarantine reason
                
                # Move back to active memories
                self.quarantined_memories.pop(i)
                self.memories["spatial"].append(mem)
                log.info(f"♻️ REHABILITATED memory: {mem.description} at {coordinates} "
                        f"(confidence: {mem.confidence:.2f})")
                self._save_memories()
                return True
        
        return False

    def record_npc_interaction(self, map_name: str, coordinates: List[int], npc_name: str = "NPC") -> Optional[str]:
        """
        Record an NPC interaction at these coordinates.
        Returns a warning string if this NPC has been talked to too many times.
        """
        if not coordinates or len(coordinates) < 2:
            return None
        
        key = (map_name.upper(), tuple(coordinates))
        self.npc_interactions[key] = self.npc_interactions.get(key, 0) + 1
        count = self.npc_interactions[key]
        
        log.info(f"💬 NPC interaction #{count} at {map_name} {coordinates}")
        
        if count >= self.NPC_INTERACTION_THRESHOLD:
            warning = f"⚠️ You've already talked to {npc_name} at {coordinates} {count} times! STOP interacting with this NPC. Move away and explore elsewhere or find the actual exit."
            log.warning(warning)
            return warning
        
        return None
    
    def get_npc_interaction_context(self, map_name: str) -> str:
        """Get context about NPCs to avoid in the current map."""
        map_upper = map_name.upper()
        avoided = []
        
        for (stored_map, coords), count in self.npc_interactions.items():
            if stored_map == map_upper and count >= self.NPC_INTERACTION_THRESHOLD:
                avoided.append(f"NPC at {list(coords)} (talked {count}x - AVOID)")
        
        if avoided:
            return f"🚫 NPCs TO AVOID: {', '.join(avoided)}"
        return ""
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # LASS MARKINGS: Visual overlay markers for UI minimap
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def add_lass_marking(self, map_name: str, coords: List[int], marking_type: str, 
                         confidence: float = 1.0) -> bool:
        """
        Add a Lass marking for the minimap overlay.
        
        Args:
            map_name: Name of the map
            coords: [x, y] coordinates
            marking_type: "N" for NPC, "O" for Opening/Exit
            confidence: Initial confidence (0.0-1.0)
        
        Returns:
            True if marking was added/updated
        """
        if not map_name or not coords or len(coords) < 2:
            return False
        
        key = (map_name.upper(), tuple(coords))
        
        self.lass_markings[key] = {
            "type": marking_type,
            "timestamp": datetime.now().isoformat(),
            "confidence": min(1.0, max(0.0, confidence)),
            "x": coords[0],
            "y": coords[1]
        }
        
        log.info(f"📍 Lass marked {marking_type} at {map_name} {coords} (confidence: {confidence:.1f})")
        return True
    
    def get_lass_markings_for_map(self, map_name: str, decay_hours: float = 24.0) -> List[Dict]:
        """
        Get all Lass markings for a specific map with decay-adjusted confidence.
        
        Args:
            map_name: Name of the map to get markings for
            decay_hours: Hours after which marks fully decay (confidence → 0)
        
        Returns:
            List of marking dicts with opacity calculated from age
        """
        if not map_name:
            return []
        
        map_upper = map_name.upper()
        markings = []
        now = datetime.now()
        
        for (stored_map, coords), data in self.lass_markings.items():
            if stored_map == map_upper:
                # Calculate decay based on age
                try:
                    created = datetime.fromisoformat(data["timestamp"])
                    age_hours = (now - created).total_seconds() / 3600
                    decay_factor = max(0.0, 1.0 - (age_hours / decay_hours))
                    
                    # Apply decay to confidence for opacity
                    opacity = data["confidence"] * decay_factor
                    
                    if opacity > 0.1:  # Only include visible markers
                        markings.append({
                            "x": coords[0],
                            "y": coords[1],
                            "type": data["type"],
                            "opacity": round(opacity, 2),
                            "age_hours": round(age_hours, 1)
                        })
                except (ValueError, KeyError):
                    # If timestamp is invalid, include with base confidence
                    markings.append({
                        "x": coords[0],
                        "y": coords[1], 
                        "type": data["type"],
                        "opacity": data.get("confidence", 0.5),
                        "age_hours": 0
                    })
        
        return markings
    
    def mark_npc_discovered(self, map_name: str, coords: List[int]) -> None:
        """Convenience method to mark an NPC location (discovered via A-press dialogue)."""
        self.add_lass_marking(map_name, coords, "N", confidence=0.9)
    
    def mark_exit_discovered(self, map_name: str, coords: List[int], 
                              confidence: float = 0.8) -> None:
        """Convenience method to mark an exit/opening location."""
        self.add_lass_marking(map_name, coords, "O", confidence=confidence)
    
    def should_trust_transition(self, from_map: str, from_pos: List[int], 
                                 to_map: str, to_pos: List[int],
                                 was_on_o_tile: bool = False,
                                 minimap_had_exit: bool = False) -> tuple:
        """
        Determine if a map transition should be trusted as a real connection
        or might be a cutscene/teleport.
        
        Returns: (trust_score: float, reason: str)
        
        trust_score:
        - 0.9-1.0: High trust (natural transition, player walked through exit)
        - 0.5-0.8: Medium trust (unclear, might be real)
        - 0.1-0.4: Low trust (likely cutscene/teleport)
        
        Heuristics:
        1. If player was on 'O' tile before transition: HIGH trust
        2. If minimap showed an exit at player position: HIGH trust
        3. If transition is between adjacent maps (Route 1 <-> Viridian City): OK trust
        4. If transition is to a special location (OAKS_LAB, etc.): LOWER trust
        5. If position changed dramatically without walking: VERY LOW trust (teleport)
        """
        from_upper = from_map.upper() if from_map else ""
        to_upper = to_map.upper() if to_map else ""
        
        # Heuristic 1 & 2: Player was on an exit tile
        if was_on_o_tile or minimap_had_exit:
            return (0.95, "Player walked through a visible exit tile")
        
        # Heuristic 3: Check for known adjacent maps
        # These are pairs that should naturally connect
        adjacent_pairs = [
            ("PALLET_TOWN", "ROUTE_1"),
            ("ROUTE_1", "VIRIDIAN_CITY"),
            ("VIRIDIAN_CITY", "ROUTE_2"),
            ("VIRIDIAN_CITY", "ROUTE_22"),
            ("ROUTE_2", "PEWTER_CITY"),
            ("ROUTE_2", "VIRIDIAN_FOREST"),
            # Add more as needed
        ]
        
        for pair in adjacent_pairs:
            if (pair[0] in from_upper and pair[1] in to_upper) or \
               (pair[1] in from_upper and pair[0] in to_upper):
                return (0.7, f"Transition between adjacent maps {from_map} <-> {to_map}")
        
        # Heuristic 4: Suspicious destination maps (often reached via cutscene)
        # These are indoor locations that you typically enter via door, not open map edge
        suspicious_destinations = ["OAKS_LAB", "PLAYERS_HOUSE", "RIVAL", "POKEMON_CENTER", "MART"]
        for suspicious in suspicious_destinations:
            if suspicious in to_upper and not was_on_o_tile:
                # Entering a building without walking through a door? Suspicious.
                return (0.3, f"Sudden transition to indoor location {to_map} without visible exit - possible cutscene")
        
        # Heuristic 5: Position didn't change much before transition (likely cutscene)
        # If from_pos was on the edge of from_map, that's normal
        # But if from_pos was in the middle, might be a cutscene teleport
        if from_pos and len(from_pos) >= 2:
            x, y = from_pos
            # Edge detection (rough heuristic - map edges are typically at low/high coords)
            on_edge = (x <= 2 or x >= 15 or y <= 2 or y >= 15)
            if not on_edge:
                return (0.4, f"Transition occurred from middle of map ({from_pos}) - might be cutscene teleport")
        
        # Heuristic 6: We have no other info - medium trust
        # Check if we have any previous verified memories for this route
        existing_memory = self._find_exit_memory(from_map, from_pos) if from_pos else None
        if existing_memory and existing_memory.verification_source == "verified_transition":
            return (0.85, "Previously verified transition at this location")
        
        # Default: Medium-low trust
        return (0.5, "Unknown transition context - treating with moderate trust")

    def add_spatial_memory(
        self,
        location: str,
        description: str,
        coordinates: Optional[List[int]] = None,
        destination: Optional[str] = None,
        landmark_type: Optional[str] = None
    ) -> SpatialMemory:
        """Add a spatial memory (map connections, landmarks, etc.)"""

        memory = SpatialMemory(
            type="spatial",
            location=location,
            description=description,
            coordinates=coordinates,
            destination=destination,
            landmark_type=landmark_type,
            timestamp=datetime.now().isoformat(),
            importance=self._calculate_importance(description),
            context={
                "destination": destination,
                "landmark_type": landmark_type
            }
        )

        self.memories["spatial"].append(memory)
        self._save_memories()
        return memory

    def add_narrative_memory(
        self,
        location: str,
        description: str,
        event_type: str = "general",
        characters: Optional[List[str]] = None,
        emotional_tone: str = "neutral",
        importance: float = 1.0
    ) -> NarrativeMemory:
        """Add a narrative memory (story, dialogue, mistakes)"""
        
        memory = NarrativeMemory(
            type="narrative",
            location=location,
            description=description,
            coordinates=None,  # Narrative memories are less strictly bound to coords
            timestamp=datetime.now().isoformat(),
            importance=importance,
            event_type=event_type,
            characters_involved=characters,
            emotional_tone=emotional_tone,
            context={
                "event_type": event_type,
                "emotional_tone": emotional_tone,
                "characters": characters
            }
        )
        
        self.memories["narrative"].append(memory)
        self._save_memories()
        
        # Log it prominently
        log.info(f"📖 NARRATIVE MEMORY ADDED: {description} (Tone: {emotional_tone})")
        return memory

    def get_narrative_context(self, limit: int = 5) -> str:
        """Get summary of recent narrative events/memories for chat context."""
        mems = self.memories.get("narrative", [])
        if not mems:
            return ""
        
        # Get most recent ones
        recent = mems[-limit:]
        return "\n".join([f"- {m.description}" for m in recent])

    def add_gameplay_memory(
        self,
        location: str,
        description: str,
        event_type: str,
        outcome: Optional[str] = None,
        coordinates: Optional[List[int]] = None,
        pokemon_involved: Optional[List[str]] = None
    ) -> GameplayMemory:
        """Add a gameplay memory (battles, items, events)"""

        memory = GameplayMemory(
            type="gameplay",
            location=location,
            description=description,
            event_type=event_type,
            outcome=outcome,
            coordinates=coordinates,
            pokemon_involved=pokemon_involved,
            timestamp=datetime.now().isoformat(),
            importance=self._calculate_importance(description),
            context={
                "event_type": event_type,
                "outcome": outcome,
                "pokemon_involved": pokemon_involved
            }
        )

        self.memories["gameplay"].append(memory)
        self._save_memories()
        return memory

    def record_transition(
        self,
        from_map: str,
        from_pos: List[int],
        to_map: str,
        to_pos: List[int],
        was_on_o_tile: bool = False,
        minimap_had_exit: bool = False
    ) -> List[SpatialMemory]:
        """
        Record a transition between two maps.
        Uses trust heuristics to set confidence appropriately.
        Low-trust transitions (likely cutscenes) get lower confidence.
        """
        created = []
        if not from_map or not to_map or from_map == to_map:
            return created
        
        # Evaluate how much we should trust this transition
        trust_score, trust_reason = self.should_trust_transition(
            from_map, from_pos, to_map, to_pos,
            was_on_o_tile=was_on_o_tile,
            minimap_had_exit=minimap_had_exit
        )
        
        log.info(f"📍 Transition trust: {trust_score:.2f} - {trust_reason}")
        
        # Set verification source based on trust
        if trust_score >= 0.8:
            verification_source = "verified_transition"
        elif trust_score >= 0.5:
            verification_source = "unverified"
        else:
            verification_source = "llm_claim"  # Treat low-trust as claim that needs verification

        # Memory 1: Exit from A -> B
        mem1 = SpatialMemory(
            type="spatial",
            location=from_map,
            description=f"Exit: Path at {from_pos} leads to {to_map} at {to_pos}" + 
                       (" [VERIFIED]" if trust_score >= 0.8 else " [UNVERIFIED]"),
            coordinates=from_pos,
            destination=to_map,
            landmark_type="exit",
            timestamp=datetime.now().isoformat(),
            importance=3.0 if trust_score >= 0.8 else 2.0,
            confidence=trust_score,  # Set based on trust evaluation
            verification_source=verification_source,
            context={
                "source": verification_source, 
                "target_pos": to_pos,
                "trust_reason": trust_reason
            }
        )
        if not self._is_duplicate_memory(mem1, self.memories["spatial"]):
            self.memories["spatial"].append(mem1)
            created.append(mem1)

        # Memory 2: Entrance at B from A
        mem2 = SpatialMemory(
            type="spatial",
            location=to_map,
            description=f"Entrance: Arrived from {from_map} (via {from_pos}) at {to_pos}" +
                       (" [VERIFIED]" if trust_score >= 0.8 else " [UNVERIFIED]"),
            coordinates=to_pos,
            destination=from_map,
            landmark_type="entrance",
            timestamp=datetime.now().isoformat(),
            importance=3.0 if trust_score >= 0.8 else 2.0,
            confidence=trust_score,
            verification_source=verification_source,
            context={
                "source": verification_source, 
                "origin_pos": from_pos,
                "trust_reason": trust_reason
            }
        )
        if not self._is_duplicate_memory(mem2, self.memories["spatial"]):
            self.memories["spatial"].append(mem2)
            created.append(mem2)
        
        if created:
            self._save_memories()
            
        return created

    def record_vision_claim(
        self,
        claim_type: str,
        description: str,
        location: str,
        coordinates: Optional[List[int]] = None,
        direction: Optional[str] = None,
        confidence: float = 0.5
    ) -> VisionClaim:
        """
        Record a claim from vision analysis that needs verification.
        These are things like "I see a door to the north" that may or may not be accurate.
        """
        claim = VisionClaim(
            claim_type=claim_type,
            description=description,
            location=location,
            coordinates=coordinates,
            direction=direction,
            timestamp=datetime.now().isoformat(),
            verified=False,
            verification_result=None,
            confidence=confidence,
            context={}
        )
        self.vision_claims.append(claim)
        self.vision_stats["total_claims"] += 1
        self.vision_stats["unverified"] += 1
        return claim

    def verify_vision_claim(
        self,
        claim: VisionClaim,
        minimap_2d: str,
        player_pos: List[int],
        is_correct: Optional[bool] = None
    ) -> bool:
        """
        Verify a vision claim against minimap data.
        
        Args:
            claim: The vision claim to verify
            minimap_2d: The 2D minimap string from game state
            player_pos: Current player [x, y] position
            is_correct: Override for manual verification. If None, auto-check minimap.
        
        Returns:
            True if claim was verified, False otherwise
        """
        if claim.verified:
            return claim.verification_result
        
        # If manual verification provided
        if is_correct is not None:
            claim.verified = True
            claim.verification_result = is_correct
        else:
            # Auto-check: Look for exit tiles in the claimed direction
            result = self._check_minimap_for_exit(minimap_2d, player_pos, claim.direction)
            claim.verified = True
            claim.verification_result = result
        
        # Update stats
        self.vision_stats["unverified"] -= 1
        if claim.verification_result:
            self.vision_stats["verified_correct"] += 1
        else:
            self.vision_stats["verified_wrong"] += 1
        
        # If claim was correct, increase confidence for future similar claims
        # If wrong, decrease confidence
        claim.confidence = 0.8 if claim.verification_result else 0.2
        
        return claim.verification_result

    def _check_minimap_for_exit(
        self,
        minimap_2d: str,
        player_pos: List[int],
        claimed_direction: Optional[str]
    ) -> bool:
        """
        Check if there's an exit tile in the claimed direction on the minimap.
        
        Minimap 2D format uses characters like:
        - 'X' or '@' for player position
        - 'O' or 'o' for open tiles
        - '#' or similar for walls
        - 'D' for doors/exits
        """
        if not minimap_2d or not claimed_direction:
            return False  # Can't verify without data
        
        lines = minimap_2d.strip().split('\n')
        if not lines:
            return False
        
        # Find player position in minimap (usually center or marked with X/@)
        player_row, player_col = None, None
        for row_idx, line in enumerate(lines):
            for col_idx, char in enumerate(line):
                if char in ['X', '@', 'P']:
                    player_row, player_col = row_idx, col_idx
                    break
            if player_row is not None:
                break
        
        if player_row is None:
            # Assume center if not marked
            player_row = len(lines) // 2
            player_col = len(lines[0]) // 2 if lines else 0
        
        # Define direction offsets
        direction_offsets = {
            'north': (-1, 0), 'up': (-1, 0),
            'south': (1, 0), 'down': (1, 0),
            'west': (0, -1), 'left': (0, -1),
            'east': (0, 1), 'right': (0, 1),
        }
        
        direction_lower = claimed_direction.lower()
        if direction_lower not in direction_offsets:
            return False
        
        dr, dc = direction_offsets[direction_lower]
        
        # Check tiles in that direction (up to 3 tiles)
        for distance in range(1, 4):
            check_row = player_row + (dr * distance)
            check_col = player_col + (dc * distance)
            
            if 0 <= check_row < len(lines) and 0 <= check_col < len(lines[check_row]):
                tile = lines[check_row][check_col]
                # Exit tiles are typically 'D', 'E', '>', '<', 'v', '^' or similar
                if tile in ['D', 'E', '>', '<', 'v', '^', 'O', 'o']:
                    return True
                # Wall blocks further checking
                if tile in ['#', 'W', '█', '▓']:
                    return False
        
        return False

    def get_vision_accuracy(self) -> Dict[str, Any]:
        """Get vision accuracy statistics."""
        total = self.vision_stats["total_claims"]
        if total == 0:
            return {"accuracy": 0.0, "total": 0, "message": "No vision claims recorded yet"}
        
        verified = self.vision_stats["verified_correct"] + self.vision_stats["verified_wrong"]
        if verified == 0:
            return {"accuracy": 0.0, "total": total, "message": f"{total} claims pending verification"}
        
        accuracy = self.vision_stats["verified_correct"] / verified
        return {
            "accuracy": accuracy,
            "total": total,
            "verified": verified,
            "correct": self.vision_stats["verified_correct"],
            "wrong": self.vision_stats["verified_wrong"],
            "pending": self.vision_stats["unverified"],
            "message": f"Vision accuracy: {accuracy:.1%} ({self.vision_stats['verified_correct']}/{verified})"
        }

    def get_unverified_claims(self, limit: int = 5) -> List[VisionClaim]:
        """Get pending vision claims that need verification."""
        return [c for c in self.vision_claims if not c.verified][:limit]


    def extract_memories_from_response(
        self,
        analysis_text: str,
        game_state: Dict[str, Any],
        vision_analysis: Optional[str] = None
    ) -> List[Memory]:
        """Extract memories from LLM response and game state"""

        extracted_memories = []
        current_location = game_state.get('map_name', 'unknown')
        current_position = game_state.get('position', [])

        # Attempt to extract location from text if unknown
        if current_location == 'unknown' and analysis_text:
            loc_match = re.search(r'Location:\s*([A-Z][a-zA-Z\s]+?)(?:\sat|\n|$)', analysis_text)
            if loc_match:
                extracted_name = loc_match.group(1).strip()
                if self._is_valid_destination(extracted_name):
                    current_location = extracted_name

        # Extract spatial memories
        spatial_memories = self._extract_spatial_memories(
            analysis_text, current_location, current_position, vision_analysis
        )
        extracted_memories.extend(spatial_memories)

        # Extract gameplay memories
        gameplay_memories = self._extract_gameplay_memories(
            analysis_text, current_location, current_position, game_state, vision_analysis
        )
        extracted_memories.extend(gameplay_memories)
        
        # Extract narrative memories (story events, choices, mistakes)
        narrative_memories = self._extract_narrative_memories(analysis_text, current_location)
        extracted_memories.extend(narrative_memories)
        
        # NOTE: Fallback memories disabled - they create too many duplicates
        # Only record significant events like verified transitions, battles, items
        
        # Deduplicate before saving - check if similar memory already exists
        for memory in extracted_memories:
            # Check for duplicates
            is_duplicate = False
            existing_memories = self.memories.get(memory.type, [])
            
            for existing in existing_memories[-20:]:  # Only check recent memories
                # Consider duplicate if same location, same landmark_type/event_type, and similar coordinates
                if hasattr(memory, 'landmark_type') and hasattr(existing, 'landmark_type'):
                    if (existing.location == memory.location and 
                        existing.landmark_type == memory.landmark_type and
                        existing.landmark_type == "exploration"):  # Only dedupe exploration
                        is_duplicate = True
                        break
                elif hasattr(memory, 'event_type') and hasattr(existing, 'event_type'):
                    if (existing.location == memory.location and 
                        existing.event_type == memory.event_type and
                        existing.description == memory.description):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                self.memories[memory.type].append(memory)

        if extracted_memories:
            self._save_memories()

        return extracted_memories

    # Known Pokemon locations for validation
    KNOWN_LOCATIONS = {
        "pallet", "viridian", "pewter", "cerulean", "vermilion", "lavender",
        "celadon", "fuchsia", "saffron", "cinnabar", "indigo", "plateau",
        "route", "lab", "gym", "center", "mart", "tower", "cave", "forest",
        "house", "home", "oak", "pokemon", "pokecenter", "pokemart"
    }
    
    # Words to filter out - these are NOT valid destinations
    STOP_WORDS = {
        "the", "a", "an", "to", "of", "in", "on", "at", "for", "and", "or",
        "is", "it", "this", "that", "these", "those", "my", "your", "their",
        "i", "you", "we", "they", "he", "she", "what", "where", "when", "how",
        "any", "some", "through", "from", "with", "into", "onto", "up", "down",
        "left", "right", "north", "south", "east", "west", "here", "there",
        "area", "place", "space", "room", "building", "buildings", "current",
        "next", "other", "another", "environment", "furniture", "visible", "s"
    }

    def _is_valid_destination(self, destination: str) -> bool:
        """Check if a destination is meaningful (not a stop word or garbage)"""
        if not destination:
            return False
        dest_lower = destination.lower().strip()
        
        # Filter out stop words
        if dest_lower in self.STOP_WORDS:
            return False
        
        # Must be at least 3 characters
        if len(dest_lower) < 3:
            return False
        
        # Prefer known locations, but allow capitalized proper nouns
        is_known = any(loc in dest_lower for loc in self.KNOWN_LOCATIONS)
        is_proper_noun = destination[0].isupper() and len(destination) > 3
        
        return is_known or is_proper_noun

    def _is_duplicate_memory(self, new_memory: SpatialMemory, existing: List[SpatialMemory]) -> bool:
        """Check if this memory already exists (avoid duplicates)"""
        for mem in existing:
            # Same coordinates and destination = duplicate
            if (mem.coordinates == new_memory.coordinates and 
                mem.destination == new_memory.destination):
                return True
            # Same description = duplicate
            if mem.description == new_memory.description:
                return True
        return False

    def _extract_spatial_memories(
        self,
        analysis_text: str,
        current_location: str,
        current_position: List[int],
        vision_analysis: Optional[str] = None
    ) -> List[SpatialMemory]:
        """Extract spatial memories from analysis text with validation"""

        memories = []
        
        if not analysis_text:
            return memories

        # Look for coordinate patterns with proper location names
        # Pattern: coordinates [X,Y] lead to LocationName
        coord_dest_pattern = r'coordinates?\s*\[?(\d+)[,\s]+(\d+)\]?\s*(?:leads?|connects?|goes?)\s+to\s+([A-Z][a-zA-Z\s]+(?:Town|City|Route|Lab|Gym|Center|Mart|Cave|Forest|Tower)?)'
        
        matches = re.finditer(coord_dest_pattern, analysis_text, re.IGNORECASE)
        for match in matches:
            x, y = int(match.group(1)), int(match.group(2))
            destination = match.group(3).strip()
            
            if not self._is_valid_destination(destination):
                continue
                
            landmark_type = self._determine_landmark_type(analysis_text, destination)
            
            memory = SpatialMemory(
                type="spatial",
                location=current_location,
                description=f"Exit at [{x},{y}] leads to {destination}",
                coordinates=[x, y],
                destination=destination,
                landmark_type=landmark_type,
                timestamp=datetime.now().isoformat(),
                importance=2.0,
                context={"source": "analysis_extraction"}
            )
            
            if not self._is_duplicate_memory(memory, memories):
                memories.append(memory)

        # Extract known landmark types from vision (Pokemon Center, Gym, etc.)
        if vision_analysis:
            landmark_patterns = [
                r'(Pokemon\s+Center)',
                r'(Poke\s*mart)',
                r'(Gym)',
                r"(Oak'?s?\s+Lab)",
                r'(Route\s+\d+)',
                r'([A-Z][a-z]+\s+(?:Town|City))'
            ]
            
            for pattern in landmark_patterns:
                matches = re.finditer(pattern, vision_analysis, re.IGNORECASE)
                for match in matches:
                    landmark = match.group(1).strip()
                    
                    if not self._is_valid_destination(landmark):
                        continue
                    
                    memory = SpatialMemory(
                        type="spatial",
                        location=current_location,
                        description=f"Spotted {landmark} nearby",
                        coordinates=current_position if current_position else None,
                        landmark_type=self._determine_landmark_type(vision_analysis, landmark),
                        timestamp=datetime.now().isoformat(),
                        importance=1.5,
                        context={"source": "vision_analysis"}
                    )
                    
                    if not self._is_duplicate_memory(memory, memories):
                        memories.append(memory)
            
            # Extract door/exit vision claims for verification
            # These are claims that should be verified against minimap before trusting
            door_exit_patterns = [
                (r'(?:see|spot|notice|visible)\s+(?:a\s+)?(?:door|exit|entrance)\s+(?:to\s+the\s+)?(\w+)', 'door'),
                (r'(\w+)\s+(?:door|exit|entrance)', 'door'),
                (r'(?:door|exit)\s+(?:on\s+the\s+)?(\w+)', 'door'),
                (r'(?:path|route|way)\s+(?:leads?|goes?)\s+(\w+)', 'path'),
            ]
            
            for pattern, claim_type in door_exit_patterns:
                matches = re.finditer(pattern, vision_analysis, re.IGNORECASE)
                for match in matches:
                    direction = match.group(1).strip().lower()
                    # Filter out non-direction words
                    if direction in ['north', 'south', 'east', 'west', 'up', 'down', 'left', 'right']:
                        self.record_vision_claim(
                            claim_type=claim_type,
                            description=f"Vision claims {claim_type} to the {direction}",
                            location=current_location,
                            coordinates=current_position if current_position else None,
                            direction=direction,
                            confidence=0.5  # Start with low confidence
                        )

        return memories

    def _extract_narrative_memories(
        self,
        analysis_text: str,
        current_location: str
    ) -> List[NarrativeMemory]:
        """Extract value from 10. MEMORY_WRITE section in analysis text"""
        memories = []
        if not analysis_text:
            return memories
            
        # Look for section 10
        # Matches: 10. **MEMORY_WRITE**: content... (until next section or end)
        # Handle optional bolding: 10. MEMORY_WRITE: or 10. **MEMORY_WRITE**:
        match = re.search(r'10\.\s*(?:\*\*)?MEMORY_WRITE(?:\*\*)?:\s*(.*?)(?:\n\d+\.|\n<|<|\Z)', analysis_text, re.DOTALL | re.IGNORECASE)
        
        if match:
            content = match.group(1).strip()
            # Ignore "None", "Nothing", etc.
            if content and content.lower() not in ["none", "nothing", "n/a", "no", "no new memories", "no changes", "none."]:
                # Clean up lines - handle bullet points
                lines = [line.strip().lstrip('-').lstrip('*').strip() for line in content.split('\n') if line.strip()]
                
                for line in lines:
                    if len(line) > 5 and line.lower() != "none":  # Ignore very short junk
                         # Add memory and track it
                         log.info(f"🧠 Parsed Narrative Memory: {line}")
                         memories.append(self.add_narrative_memory(
                             location=current_location,
                             description=line,
                             event_type="narrative_choice",
                             importance=2.0  # High default importance for explicitly written memories
                         ))
                         
        return memories


    def _extract_gameplay_memories(
        self,
        analysis_text: str,
        current_location: str,
        current_position: List[int],
        game_state: Dict[str, Any],
        vision_analysis: Optional[str] = None
    ) -> List[GameplayMemory]:
        """Extract gameplay memories from analysis text and vision analysis.
        
        NOTE: Quest items are ONLY detected from vision_analysis (actual in-game dialogue)
        to prevent false positives from goal/planning text in analysis_text.
        """

        memories = []
        
        # Known Pokemon items (must match these specifically)
        KNOWN_ITEMS = {
            "potion", "super_potion", "hyper_potion", "max_potion", "revive", "max_revive",
            "pokeball", "great_ball", "ultra_ball", "master_ball", "antidote", "paralyze_heal",
            "awakening", "burn_heal", "ice_heal", "full_heal", "ether", "max_ether", "elixir",
            "max_elixir", "escape_rope", "repel", "super_repel", "max_repel", "rare_candy",
            "pp_up", "tm", "hm", "moon_stone", "fire_stone", "thunder_stone", "water_stone",
            "leaf_stone", "nugget", "pearl", "big_pearl", "stardust", "star_piece",
            "bicycle", "town_map", "pokedex", "old_rod", "good_rod", "super_rod",
        }
        
        # Words that should NEVER be extracted as items
        ITEM_STOP_WORDS = {
            "stuck", "it", "a", "the", "this", "that", "here", "there", "up", "down",
            "left", "right", "one", "two", "nothing", "something", "anything", "position",
            "movement", "door", "exit", "wall", "path", "route", "s", "t", "d", "m",
            "access", "control", "ability", "permission", "victory", "defeat", "battle",
        }

        # Battle patterns - only if very clear
        battle_patterns = [
            r'(defeated|beat)\s+(?:wild\s+)?([A-Z][a-z]+)(?:\s|,|\.)',  # "defeated Rattata"
            r'won\s+(?:the\s+)?battle\s+against\s+([A-Z][a-z]+)',  # "won battle against Trainer"
        ]

        # Extract clear battle memories only
        for pattern in battle_patterns:
            matches = re.finditer(pattern, analysis_text)
            for match in matches:
                pokemon_name = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                if pokemon_name and len(pokemon_name) > 2:
                    memory = GameplayMemory(
                        type="gameplay",
                        location=current_location,
                        description=f"Defeated {pokemon_name}",
                        event_type="battle",
                        outcome="victory",
                        coordinates=current_position,
                        pokemon_involved=[pokemon_name],
                        timestamp=datetime.now().isoformat(),
                        importance=2.0,
                        context={"source": "analysis_extraction"}
                    )
                    memories.append(memory)

        # Item patterns - very strict, only match known items
        item_pattern = r'(?:found|obtained|got|received|picked\s+up)\s+(?:a\s+)?(\w+(?:\s+\w+)?)'
        matches = re.finditer(item_pattern, analysis_text, re.IGNORECASE)
        
        for match in matches:
            item_name = match.group(1).lower().strip()
            
            # Skip short words and stop words
            if len(item_name) < 3 or item_name in ITEM_STOP_WORDS:
                continue
            
            # Only record if it looks like a real item
            item_normalized = item_name.replace(" ", "_").replace("-", "_")
            if item_normalized in KNOWN_ITEMS or any(known in item_name for known in ["potion", "ball", "tm", "hm"]):
                memory = GameplayMemory(
                    type="gameplay",
                    location=current_location,
                    description=f"Found {item_name.title()}",
                    event_type="item_found",
                    outcome="obtained",
                    coordinates=current_position,
                    timestamp=datetime.now().isoformat(),
                    importance=1.5,
                    context={"source": "analysis_extraction", "item": item_name}
                )
                memories.append(memory)

        # ═══════════════════════════════════════════════════════════════════════════════
        # QUEST ITEM DETECTION - Pokemon Red specific quest items
        # These create QuestMemory entries that should trigger goal creation
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # Quest items with their associated quest details
        QUEST_ITEMS = {
            "oak's parcel": {
                "quest_id": "oaks_parcel_delivery",
                "quest_type": "delivery",
                "description": "Deliver Oak's Parcel to Professor Oak in Pallet Town",
                "target_npc": "Professor Oak",
                "target_location": "OAKS_LAB"
            },
            "parcel": {  # Alternate match
                "quest_id": "oaks_parcel_delivery",
                "quest_type": "delivery",
                "description": "Deliver Oak's Parcel to Professor Oak in Pallet Town",
                "target_npc": "Professor Oak",
                "target_location": "OAKS_LAB"
            },
            "pokedex": {
                "quest_id": "fill_pokedex",
                "quest_type": "collection",
                "description": "Fill the Pokédex by catching all Pokemon",
                "target_npc": None,
                "target_location": None
            },
            "town map": {
                "quest_id": "received_town_map",
                "quest_type": "item_received",
                "description": "Received Town Map from Daisy",
                "target_npc": None,
                "target_location": None
            },
            "old amber": {
                "quest_id": "revive_aerodactyl", 
                "quest_type": "delivery",
                "description": "Take Old Amber to Cinnabar Lab to revive Aerodactyl",
                "target_npc": "Lab Scientist",
                "target_location": "CINNABAR_LAB"
            },
            "helix fossil": {
                "quest_id": "revive_omanyte",
                "quest_type": "delivery", 
                "description": "Take Helix Fossil to Cinnabar Lab to revive Omanyte",
                "target_npc": "Lab Scientist",
                "target_location": "CINNABAR_LAB"
            },
            "dome fossil": {
                "quest_id": "revive_kabuto",
                "quest_type": "delivery",
                "description": "Take Dome Fossil to Cinnabar Lab to revive Kabuto", 
                "target_npc": "Lab Scientist",
                "target_location": "CINNABAR_LAB"
            },
            "secret key": {
                "quest_id": "unlock_cinnabar_gym",
                "quest_type": "unlock",
                "description": "Use Secret Key to unlock Cinnabar Gym",
                "target_npc": None,
                "target_location": "CINNABAR_GYM"
            },
            "ss ticket": {
                "quest_id": "board_ss_anne",
                "quest_type": "access",
                "description": "Use S.S. Ticket to board the S.S. Anne in Vermilion City",
                "target_npc": None,
                "target_location": "SS_ANNE"
            },
            "silph scope": {
                "quest_id": "identify_ghosts",
                "quest_type": "item_received",
                "description": "Use Silph Scope to identify Ghost Pokemon in Pokemon Tower",
                "target_npc": None,
                "target_location": "POKEMON_TOWER"
            },
            "poke flute": {
                "quest_id": "wake_snorlax",
                "quest_type": "item_received",
                "description": "Use Poke Flute to wake sleeping Snorlax blocking routes",
                "target_npc": None,
                "target_location": None
            },
            "lift key": {
                "quest_id": "access_rocket_hideout",
                "quest_type": "unlock",
                "description": "Use Lift Key to access Team Rocket Hideout elevator",
                "target_npc": None,
                "target_location": "ROCKET_HIDEOUT"
            },
            "card key": {
                "quest_id": "access_silph_floors",
                "quest_type": "unlock",
                "description": "Use Card Key to access all floors in Silph Co.",
                "target_npc": None,
                "target_location": "SILPH_CO"
            }
        }
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # QUEST ITEM DETECTION - ONLY from vision_analysis (actual in-game dialogue)
        # DO NOT search analysis_text as it contains goal descriptions that cause false matches
        # e.g., "deliver Oak's Parcel" in goals was matching as if we received the parcel
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # Only check vision_analysis for quest items - NOT analysis_text
        if not vision_analysis:
            return memories  # Skip quest detection if no vision analysis available
        
        # Patterns for detecting quest item acquisition in vision/dialogue
        # Matches: "Red Got Oak's Parcel!", "Got Pokedex!", "Received Town Map!", etc.
        quest_patterns = [
            r"(?:Red\s+)?Got\s+([^!]+?)!",  # "Red Got Oak's Parcel!"
            r"(?:Red\s+)?Received\s+([^!]+?)!",  # "Received Town Map!"
            r"(?:Red\s+)?Obtained\s+([^!]+?)!",  # "Obtained Pokedex!"
        ]
        
        for pattern in quest_patterns:
            matches = re.finditer(pattern, vision_analysis, re.IGNORECASE)
            for match in matches:
                item_found = match.group(1).strip().lower()
                
                # Check if this matches any quest item
                for quest_key, quest_info in QUEST_ITEMS.items():
                    if quest_key in item_found or item_found in quest_key:
                        # Check if we already have this quest
                        existing_quest = self._find_active_quest(quest_info["quest_id"])
                        if existing_quest:
                            log.info(f"🎯 Quest already exists: {quest_info['quest_id']}")
                            continue
                        
                        # Create new quest memory
                        quest_memory = QuestMemory(
                            type="quests",
                            location=current_location,
                            description=quest_info["description"],
                            coordinates=current_position,
                            timestamp=datetime.now().isoformat(),
                            importance=3.0,  # High importance for quests
                            context={
                                "source": "dialogue_extraction",
                                "raw_match": match.group(0)
                            },
                            quest_id=quest_info["quest_id"],
                            quest_type=quest_info["quest_type"],
                            target_npc=quest_info["target_npc"],
                            target_location=quest_info["target_location"],
                            item_involved=quest_key,
                            is_active=True
                        )
                        
                        # Add to quests list
                        self.memories["quests"].append(quest_memory)
                        self._save_memories()
                        log.info(f"🎯 NEW QUEST DETECTED: {quest_info['description']}")
                        log.info(f"   Item: {quest_key} | Target: {quest_info['target_location']}")
                        
                        # Add to return list with quest_id attribute for goal creation
                        memories.append(quest_memory)
                        break  # Found a match, no need to check other quest keys

        return memories

    def _determine_landmark_type(self, text: str, landmark: str) -> Optional[str]:
        """Determine the type of landmark based on text analysis"""
        text_lower = text.lower()
        landmark_lower = landmark.lower() if landmark else ""

        if any(word in text_lower for word in ['door', 'entrance', 'exit']):
            return "door"
        elif any(word in text_lower for word in ['stairs', 'staircase']):
            return "stairs"
        elif any(word in text_lower for word in ['ladder']):
            return "ladder"
        elif any(word in text_lower for word in ['orange', 'o tile', 'special']):
            return "special_tile"
        elif any(word in text_lower for word in ['pokemon center', 'pokecenter']):
            return "pokemon_center"
        elif any(word in text_lower for word in ['gym', 'building']):
            return "building"

        return "landmark"

    def _find_active_quest(self, quest_id: str) -> Optional[QuestMemory]:
        """Find an active quest by its ID."""
        for quest in self.memories.get("quests", []):
            if hasattr(quest, 'quest_id') and quest.quest_id == quest_id and quest.is_active:
                return quest
        return None
    
    def get_active_quests(self) -> List[QuestMemory]:
        """Get all active quests."""
        return [q for q in self.memories.get("quests", []) if hasattr(q, 'is_active') and q.is_active]
    
    def complete_quest(self, quest_id: str) -> bool:
        """Mark a quest as completed."""
        for quest in self.memories.get("quests", []):
            if hasattr(quest, 'quest_id') and quest.quest_id == quest_id:
                quest.is_active = False
                quest.completed_at = datetime.now().isoformat()
                self._save_memories()
                log.info(f"✅ Quest completed: {quest_id}")
                return True
        return False

    def _calculate_importance(self, description: str) -> float:
        """Calculate importance score based on description content"""

        importance = 1.0
        desc_lower = description.lower()

        # High importance keywords
        high_importance = ['orange', 'door', 'stairs', 'exit', 'entrance', 'legendary', 'rare']
        for keyword in high_importance:
            if keyword in desc_lower:
                importance += 0.5

        # Medium importance keywords
        medium_importance = ['pokemon', 'battle', 'item', 'found', 'obtained']
        for keyword in medium_importance:
            if keyword in desc_lower:
                importance += 0.2

        # Coordinates increase importance
        if re.search(r'\[\d+,\s*\d+\]', description):
            importance += 0.3

        return min(importance, 3.0)  # Cap at 3.0

    def get_latest_memory(self) -> Optional[Memory]:
        """Get the most recent memory across all types"""

        all_memories = []
        for memory_list in self.memories.values():
            all_memories.extend(memory_list)

        if not all_memories:
            return None

        return max(all_memories, key=lambda m: m.timestamp)

    def get_relevant_memories(
        self,
        query: str,
        location: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5
    ) -> List[Memory]:
        """Get memories relevant to a query"""

        all_memories = []

        # Filter by memory type if specified
        if memory_type:
            if memory_type in self.memories:
                all_memories = self.memories[memory_type]
        else:
            for memory_list in self.memories.values():
                all_memories.extend(memory_list)

        # Filter by location if specified
        if location:
            all_memories = [m for m in all_memories if m.location == location]

        # Simple relevance scoring based on keyword matching
        query_words = query.lower().split()
        scored_memories = []

        for memory in all_memories:
            memory_text = f"{memory.description} {memory.location}".lower()
            score = sum(1 for word in query_words if word in memory_text)

            if score > 0:
                scored_memories.append((memory, score * memory.importance))

        # Sort by score and return top results
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [memory for memory, _ in scored_memories[:limit]]

    def get_spatial_connections(self, location: str) -> List[SpatialMemory]:
        """Get all spatial connections for a specific location"""

        return [
            memory for memory in self.memories["spatial"]
            if memory.location == location and memory.destination
        ]

    def save_memories(self) -> None:
        """Save memories to persistent storage"""
        self._save_memories()

    def _save_memories(self) -> None:
        """Internal method to save memories to file"""

        try:
            # Convert memories to dictionaries for JSON serialization
            serializable_memories = {}
            for memory_type, memory_list in self.memories.items():
                serializable_memories[memory_type] = [
                    asdict(memory) for memory in memory_list
                ]

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_memories, f, indent=2, ensure_ascii=False)

        except Exception as e:
            import logging
            logging.error(f"Error saving memories: {e}")

    def load_memories(self) -> None:
        """Load memories from persistent storage"""

        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Convert dictionaries back to Memory objects
            for memory_type, memory_list in data.items():
                if memory_type not in self.memories:
                    continue

                self.memories[memory_type] = []
                for memory_dict in memory_list:
                    if memory_type == "spatial":
                        memory = SpatialMemory(**memory_dict)
                    elif memory_type == "gameplay":
                        memory = GameplayMemory(**memory_dict)
                    else:
                        memory = Memory(**memory_dict)

                    self.memories[memory_type].append(memory)

        except Exception as e:
            print(f"Error loading memories: {e}")
            # Continue with empty memories if loading fails

    def get_memory_summary(self) -> str:
        """Get a summary of current memories"""

        total_memories = sum(len(memory_list) for memory_list in self.memories.values())
        latest_memory = self.get_latest_memory()

        summary = f"Memory System: {total_memories} total memories stored\n"

        for memory_type, memory_list in self.memories.items():
            summary += f"  {memory_type.capitalize()}: {len(memory_list)} memories\n"

        if latest_memory:
            summary += f"\nLatest: {latest_memory.description[:100]}..."

        return summary

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATEGY LEARNING SYSTEM
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record_outcome(self, event_type: str, details: Dict, context: Dict = None) -> None:
        """
        Record a significant outcome for potential strategy learning.
        Call this when something notable happens (heal, faint, goal complete, etc.)
        
        Args:
            event_type: Type of outcome (e.g., "healed", "blacked_out", "goal_complete", "found_exit")
            details: Event details (e.g., {"hp_restored": 100, "location": "Pokemon Center"})
            context: What was happening before (e.g., {"was_lost": True, "hp_before": 5})
        """
        outcome = {
            "event_type": event_type,
            "details": details,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "pending_actions": list(self.pending_outcomes.keys())
        }
        
        self.recent_outcomes.append(outcome)
        self.recent_outcomes = self.recent_outcomes[-10:]  # Keep last 10
        
        log.info(f"📊 Outcome recorded: {event_type} - {details}")
        
        # Check if this outcome completes any pending action
        self._check_for_strategy_discovery(outcome)
    
    def start_tracking_action(self, action_id: str, situation: str, action: str, context: Dict = None) -> None:
        """
        Start tracking an action to see what outcome it leads to.
        Call this when the agent takes a notable action.
        
        Args:
            action_id: Unique ID for this action
            situation: What situation triggered this (e.g., "lost, low HP")
            action: What action is being taken (e.g., "walking into wild battle")
            context: Additional context
        """
        self.pending_outcomes[action_id] = {
            "situation": situation,
            "action": action,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        log.info(f"🔬 Tracking action: {action_id} - {action}")
    
    def _check_for_strategy_discovery(self, outcome: Dict) -> None:
        """Check if an outcome reveals a new or existing strategy."""
        # Look for patterns that might indicate a learnable strategy
        event_type = outcome.get("event_type", "")
        details = outcome.get("details", {})
        context = outcome.get("context", {})
        
        # Pattern: Blackout led to healing
        if event_type == "blacked_out":
            # This is a potential "faint to heal" strategy discovery!
            self._maybe_discover_strategy(
                situation="Team fainted in battle",
                action="Let Pokemon faint",
                outcome="Respawned at Pokemon Center, full heal",
                tags=["healing", "shortcut", "recovery"]
            )
        
        # Pattern: Found a shortcut or new path
        if event_type == "found_exit" and context.get("was_exploring"):
            self._maybe_discover_strategy(
                situation=f"Exploring {details.get('from_location', 'unknown')}",
                action=f"Checked coordinates {details.get('coordinates', '?')}",
                outcome=f"Found exit to {details.get('to_location', 'unknown')}",
                tags=["navigation", "exploration"]
            )
    
    def _maybe_discover_strategy(self, situation: str, action: str, outcome: str, tags: List[str] = None) -> Optional[StrategyMemory]:
        """
        Check if this is a new strategy or update an existing one.
        Returns the strategy if created/updated, None if duplicate.
        """
        # Check for similar existing strategy
        for existing in self.strategies:
            if self._strategies_similar(existing, situation, action):
                # Update existing strategy
                existing.update_effectiveness(True)
                existing.last_used_at = datetime.now().isoformat()
                log.info(f"📈 Strategy reinforced: {existing.strategy_id} (effectiveness: {existing.effectiveness:.0%})")
                return existing
        
        # Create new strategy
        strategy_id = f"strategy_{len(self.strategies) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        strategy = StrategyMemory(
            strategy_id=strategy_id,
            situation=situation,
            action_taken=action,
            outcome=outcome,
            discovered_at=datetime.now().isoformat(),
            last_used_at=datetime.now().isoformat(),
            tags=tags or []
        )
        
        self.strategies.append(strategy)
        log.info(f"💡 NEW STRATEGY DISCOVERED: {strategy_id}")
        log.info(f"   Situation: {situation}")
        log.info(f"   Action: {action}")
        log.info(f"   Outcome: {outcome}")
        
        return strategy
    
    def _strategies_similar(self, existing: StrategyMemory, situation: str, action: str) -> bool:
        """Check if a situation/action combo matches an existing strategy."""
        # Simple keyword matching for now
        situation_words = set(situation.lower().split())
        action_words = set(action.lower().split())
        
        existing_situation_words = set(existing.situation.lower().split())
        existing_action_words = set(existing.action_taken.lower().split())
        
        situation_overlap = len(situation_words & existing_situation_words) / max(len(situation_words), 1)
        action_overlap = len(action_words & existing_action_words) / max(len(action_words), 1)
        
        return situation_overlap > 0.5 and action_overlap > 0.5
    
    def get_relevant_strategies(self, current_situation: str, limit: int = 3) -> List[StrategyMemory]:
        """
        Get strategies relevant to the current situation.
        Used to surface learned strategies to the LLM.
        """
        if not self.strategies:
            return []
        
        # Score strategies by relevance to current situation
        situation_words = set(current_situation.lower().split())
        scored = []
        
        for strategy in self.strategies:
            strategy_words = set(strategy.situation.lower().split())
            strategy_words.update(strategy.tags or [])
            
            overlap = len(situation_words & strategy_words)
            # Weight by effectiveness
            score = overlap * strategy.effectiveness
            
            if score > 0:
                scored.append((strategy, score))
        
        # Sort by score and return top matches
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:limit]]
    
    def get_strategy_context_for_llm(self, current_situation: str = "") -> str:
        """Generate LLM context string for learned strategies."""
        if not self.strategies:
            return ""
        
        context_parts = []
        
        # Get relevant strategies
        relevant = self.get_relevant_strategies(current_situation, limit=3) if current_situation else self.strategies[:3]
        
        if relevant:
            context_parts.append("💡 LEARNED STRATEGIES (from experience):")
            for s in relevant:
                effectiveness_str = f"{s.effectiveness:.0%}" if s.times_used > 1 else "new"
                context_parts.append(
                    f"  • When: {s.situation[:50]}... → "
                    f"Try: {s.action_taken[:40]}... "
                    f"({effectiveness_str} effective, used {s.times_used}x)"
                )
        
        # Recent outcomes for reflection
        if self.recent_outcomes:
            recent = self.recent_outcomes[-3:]
            context_parts.append("\n📊 RECENT OUTCOMES (reflect on what worked):")
            for o in recent:
                details_str = str(o.get('details', {}))[:50]
                context_parts.append(f"  • {o['event_type']}: {details_str}")
        
        return "\n".join(context_parts) if context_parts else ""

    def get_context_for_llm(self, current_location: str, limit: int = 5) -> str:
        """
        Generate a compact context string for LLM injection.
        Returns relevant memories for the current location with confidence information.
        """
        if not current_location:
            return ""
        
        context_parts = []
        
        # Get spatial memories for this location
        spatial_here = [m for m in self.memories["spatial"] 
                       if m.location and current_location.lower() in m.location.lower()]
        
        if spatial_here:
            # Separate by confidence level
            high_conf = [m for m in spatial_here 
                        if getattr(m, 'confidence', 0.5) >= 0.7 
                        and m.landmark_type in ("exit", "entrance")]
            medium_conf = [m for m in spatial_here 
                         if 0.3 <= getattr(m, 'confidence', 0.5) < 0.7 
                         and m.landmark_type in ("exit", "entrance")]
            low_conf = [m for m in spatial_here 
                       if getattr(m, 'confidence', 0.5) < 0.3 
                       and m.landmark_type in ("exit", "entrance")]
            others = [m for m in spatial_here if m not in high_conf + medium_conf + low_conf]
            
            # Show high-confidence exits (verified)
            if high_conf:
                exits = []
                for m in high_conf:
                    conf = getattr(m, 'confidence', 0.5)
                    source = getattr(m, 'verification_source', 'unverified')
                    tag = "[VERIFIED]" if source == "verified_transition" else f"[{conf:.0%}]"
                    exits.append(f"{tag} {m.coordinates} -> {m.destination}")
                context_parts.append(f"✅ TRUSTED EXITS: {', '.join(exits)}")
            
            # Show medium-confidence exits with warning
            if medium_conf:
                exits = []
                for m in medium_conf:
                    conf = getattr(m, 'confidence', 0.5)
                    exits.append(f"[{conf:.0%}] {m.coordinates} -> {m.destination}")
                context_parts.append(f"⚠️ UNVERIFIED EXITS (try multiple directions): {', '.join(exits)}")
            
            # Show low-confidence exits strongly warned
            if low_conf:
                exits = []
                for m in low_conf:
                    conf = getattr(m, 'confidence', 0.5)
                    exits.append(f"[{conf:.0%}] {m.coordinates}")
                context_parts.append(f"❌ LOW CONFIDENCE (may be false): {', '.join(exits)}")
            
            if others:
                landmarks = [f"{m.description}" for m in others[-limit:]]
                context_parts.append(f"Notes: {'; '.join(landmarks)}")
        
        # Show quarantined memories for this location (so agent knows what to avoid)
        quarantined_here = [m for m in self.quarantined_memories 
                          if m.location and current_location.lower() in m.location.lower()]
        if quarantined_here:
            qlist = [f"{m.coordinates} (was: {m.destination})" for m in quarantined_here[:3]]
            context_parts.append(f"🔒 QUARANTINED (don't trust): {', '.join(qlist)}")
        
        # Get recent gameplay events  
        gameplay = self.memories["gameplay"][-3:]
        if gameplay:
            events = [m.description for m in gameplay]
            context_parts.append(f"Recent events: {'; '.join(events)}")
        
        return "\n".join(context_parts) if context_parts else ""

    def detect_stuck(self, position_history: List[tuple], threshold: int = 3) -> dict:
        """
        Detect if agent is stuck based on position history.
        Returns dict with is_stuck bool, suggestion string, and stuck_position if stuck.
        
        Detection methods:
        1. Same position for threshold consecutive cycles
        2. Oscillating between 2 positions
        3. Returning to the same position frequently (new)
        """
        if len(position_history) < threshold:
            return {"is_stuck": False, "suggestion": "", "stuck_position": None}
        
        recent = position_history[-threshold:]
        
        # Check if position unchanged for threshold cycles (consecutive)
        if len(set(recent)) == 1:
            stuck_pos = recent[0]
            return {
                "is_stuck": True,
                "suggestion": f"Position unchanged for {threshold}+ cycles at {stuck_pos}. This might be a FALSE EXIT from a cutscene. Try: 1) Walk in different directions 2) Look for REAL doors 3) Explore unexplored areas",
                "stuck_position": stuck_pos
            }
        
        # Check for oscillation (back and forth between 2 positions)
        if len(set(recent)) == 2:
            positions = list(set(recent))
            return {
                "is_stuck": True, 
                "suggestion": f"Oscillating between {positions[0]} and {positions[1]}. Break the loop - explore a completely different area.",
                "stuck_position": positions[0]
            }
        
        # NEW: Check for repeated returns to same position (pattern detection)
        # If we've been to the same spot 3+ times in last 8 moves, we're probably stuck on a false exit
        extended = position_history[-8:] if len(position_history) >= 8 else position_history
        from collections import Counter
        pos_counts = Counter(extended)
        most_common = pos_counts.most_common(1)
        if most_common and most_common[0][1] >= 3:
            frequent_pos = most_common[0][0]
            return {
                "is_stuck": True,
                "suggestion": f"Repeatedly returning to {frequent_pos} ({most_common[0][1]} times in last 8 moves). This position may be a FALSE MEMORY created by a cutscene. IGNORE any 'verified exit' at this location and explore elsewhere!",
                "stuck_position": frequent_pos
            }
        
        return {"is_stuck": False, "suggestion": "", "stuck_position": None}