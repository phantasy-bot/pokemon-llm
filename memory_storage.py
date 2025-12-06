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


@dataclass
class GameplayMemory(Memory):
    """Gameplay memory for battles, items, events"""
    event_type: Optional[str] = None  # e.g., "battle", "item_found", "level_up"
    outcome: Optional[str] = None
    pokemon_involved: Optional[List[str]] = None


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

    def __init__(self, storage_path: str = "pokemon_memories.json", reset_on_start: bool = True):
        self.storage_path = storage_path
        self.memories = {
            "spatial": [],
            "gameplay": [],
            "narrative": [],
            "tactical": []
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
        
        if reset_on_start:
            # Clear memories for fresh start
            self._save_memories()
            log.info("🧹 Memories reset for fresh session")
        else:
            self.load_memories()

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
        to_pos: List[int]
    ) -> List[SpatialMemory]:
        """
        Record a verified transition between two maps.
        Creates bidirectional memories with high importance.
        """
        created = []
        if not from_map or not to_map or from_map == to_map:
            return created

        # Memory 1: Exit from A -> B
        mem1 = SpatialMemory(
            type="spatial",
            location=from_map,
            description=f"Verified Exit: Path at {from_pos} leads to {to_map}",
            coordinates=from_pos,
            destination=to_map,
            landmark_type="exit",
            timestamp=datetime.now().isoformat(),
            importance=3.0, # High importance for verified transitions
            context={"source": "verified_transition", "target_pos": to_pos}
        )
        if not self._is_duplicate_memory(mem1, self.memories["spatial"]):
            self.memories["spatial"].append(mem1)
            created.append(mem1)

        # Memory 2: Entrance at B from A
        mem2 = SpatialMemory(
            type="spatial",
            location=to_map,
            description=f"Verified Entrance: Arrived from {from_map} at {to_pos}",
            coordinates=to_pos,
            destination=from_map, # Logic implies going back leads to A
            landmark_type="entrance",
            timestamp=datetime.now().isoformat(),
            importance=3.0,
            context={"source": "verified_transition", "origin_pos": from_pos}
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
            analysis_text, current_location, current_position, game_state
        )
        extracted_memories.extend(gameplay_memories)
        
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

    def _extract_gameplay_memories(
        self,
        analysis_text: str,
        current_location: str,
        current_position: List[int],
        game_state: Dict[str, Any]
    ) -> List[GameplayMemory]:
        """Extract gameplay memories from analysis text"""

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

    def get_context_for_llm(self, current_location: str, limit: int = 5) -> str:
        """
        Generate a compact context string for LLM injection.
        Returns relevant memories for the current location.
        """
        if not current_location:
            return ""
        
        context_parts = []
        
        # Get spatial memories for this location
        spatial_here = [m for m in self.memories["spatial"] 
                       if m.location and current_location.lower() in m.location.lower()]
        if spatial_here:
            # Prioritize verified exits
            verified = [m for m in spatial_here if m.importance >= 3.0 and m.landmark_type in ("exit", "entrance")]
            others = [m for m in spatial_here if m not in verified]
            
            if verified:
                exits = [f"[Verified Exit] {m.coordinates} -> {m.destination}" for m in verified]
                context_parts.append(f"MAP CONNECTIONS: {', '.join(exits)}")
            
            if others:
                # Show other landmarks
                landmarks = [f"{m.description}" for m in others[-limit:]]
                context_parts.append(f"Notes: {'; '.join(landmarks)}")
        
        # Get recent gameplay events  
        gameplay = self.memories["gameplay"][-3:]
        if gameplay:
            events = [m.description for m in gameplay]
            context_parts.append(f"Recent events: {'; '.join(events)}")
        
        return "\n".join(context_parts) if context_parts else ""

    def detect_stuck(self, position_history: List[tuple], threshold: int = 5) -> dict:
        """
        Detect if agent is stuck based on position history.
        Returns dict with is_stuck bool and suggestion string.
        """
        if len(position_history) < threshold:
            return {"is_stuck": False, "suggestion": ""}
        
        recent = position_history[-threshold:]
        
        # Check if position unchanged for threshold cycles
        if len(set(recent)) == 1:
            return {
                "is_stuck": True,
                "suggestion": "Position unchanged for 5+ cycles. Try: 1) Different direction 2) Touch navigation 3) Check for blocking NPCs"
            }
        
        # Check for oscillation (back and forth between 2 positions)
        if len(set(recent)) == 2:
            return {
                "is_stuck": True, 
                "suggestion": "Oscillating between 2 positions. Break the loop - try a completely different route."
            }
        
        return {"is_stuck": False, "suggestion": ""}