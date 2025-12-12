import json
import logging
import os
from dataclasses import asdict
from typing import Dict, List, Any
from .models import (
    Memory, SpatialMemory, GameplayMemory, QuestMemory, 
    NarrativeMemory, StrategyMemory, VisionClaim
)

log = logging.getLogger("memory_persistence")

class MemoryPersistence:
    """Handles storage and retrieval of memory objects."""
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path

    def save(self, memories: Dict[str, List[Memory]]) -> None:
        """Save memories dict to JSON file."""
        try:
            # Create a serializable dictionary
            serializable_memories = {}
            for memory_type, memory_list in memories.items():
                serializable_memories[memory_type] = [
                    asdict(memory) for memory in memory_list
                ]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_memories, f, indent=2, ensure_ascii=False)
            
            # log.info(f"Saved memories to {self.storage_path}")
                
        except Exception as e:
            log.error(f"Error saving memories to {self.storage_path}: {e}")

    def load(self) -> Dict[str, List[Memory]]:
        """Load memories from JSON file into Memory objects."""
        if not os.path.exists(self.storage_path):
            log.info(f"No memory file found at {self.storage_path}, starting fresh.")
            return {}

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            loaded_memories: Dict[str, List[Memory]] = {}
            
            for memory_type, memory_list in data.items():
                loaded_memories[memory_type] = []
                for memory_dict in memory_list:
                    try:
                        if memory_type == "spatial":
                            memory = SpatialMemory(**memory_dict)
                        elif memory_type == "gameplay":
                            memory = GameplayMemory(**memory_dict)
                        elif memory_type == "narrative":
                            memory = NarrativeMemory(**memory_dict)
                        elif memory_type == "quests":
                            memory = QuestMemory(**memory_dict)
                        elif memory_type == "tactical":
                            # If tactical uses StrategyMemory, handle it, but currently 
                            # StrategyMemory structure implies it might be separate.
                            # Assuming tactical stores Memory or similar.
                            # If StrategyMemory is not inheriting from Memory, we can't put it in a List[Memory] safely
                            # without Union types, but Python is flexible.
                            # However, original code put everything in self.memories which was generic.
                            # Let's try Memory first, or log warning.
                            memory = Memory(**memory_dict)
                        else:
                            memory = Memory(**memory_dict)
                        
                        loaded_memories[memory_type].append(memory)
                    except TypeError as e:
                        log.warning(f"Failed to load memory of type {memory_type}: {e}. Data: {memory_dict}")
            
            return loaded_memories
            
        except Exception as e:
            log.error(f"Error loading memories from {self.storage_path}: {e}")
            return {}
