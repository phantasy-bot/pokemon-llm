"""
Dev Markers - Static developer-defined markers for special locations

This module defines permanent markers for important game locations that aren't
automatically detected by the game state (e.g., Pokémon starter positions in Oak's lab).

These markers are separate from:
- Game state markers (automatically detected NPCs, exits)
- Lass markings (player-created markers during exploration)

Dev markers are intended to help the LLM agent with specific, known locations
that are crucial for game progress but hard to detect automatically.
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

log = logging.getLogger("dev_markers")


@dataclass
class DevMarker:
    """A developer-defined marker for a special location."""

    # World coordinates (absolute map position)
    world_x: int
    world_y: int

    # Map this marker belongs to
    map_name: str
    map_id: int  # Map ID for validation

    # Marker type and metadata
    marker_type: str  # "STARTER_POKEMON", "ITEM", "OBJECTIVE", "HINT"
    label: str  # Short label (e.g., "Charmander", "Pokedex", "Exit")
    description: str  # Longer description for LLM context

    # Visual marker character for minimap overlay
    # 'S' = Starter Pokémon, 'I' = Item, 'O' = Objective, 'H' = Hint
    marker_char: str = "S"

    # Interaction requirements
    requires_facing: bool = True  # Must face this tile to interact?
    facing_direction: Optional[str] = None  # Required facing direction if any

    def to_overlay_marker(self, grid_x: int, grid_y: int, opacity: float = 1.0) -> dict:
        """
        Convert to overlay marker format for minimap display.

        Args:
            grid_x, grid_y: Grid coordinates (calculated from world coords)
            opacity: Marker opacity (default 1.0)

        Returns:
            Dict compatible with lassMarkings format
        """
        return {
            "x": grid_x,
            "y": grid_y,
            "type": self.marker_char,
            "opacity": opacity,
            "reason": self.label,
            "description": self.description,
        }

    def get_llm_context(self) -> str:
        """Get formatted description for LLM prompts."""
        facing_hint = ""
        if self.requires_facing:
            if self.facing_direction:
                facing_hint = f" (face {self.facing_direction})"
            else:
                facing_hint = " (must be adjacent and facing)"

        return f"[{self.world_x},{self.world_y}] {self.label}{facing_hint} - {self.description}"


class DevMarkerRegistry:
    """
    Registry of all developer-defined markers.

    Organizes markers by map for efficient lookup and provides
    integration with the game state system.
    """

    def __init__(self):
        self._markers: Dict[str, List[DevMarker]] = {}
        self._register_default_markers()

    def _register_default_markers(self):
        """Register all default dev markers for the game."""

        # === OAK'S LAB - STARTER POKEMON ===
        # Map: "OAKS_LAB" (assuming this is the map name, adjust if needed)
        # The three Poké Balls containing starter Pokémon

        oak_lab_map_id = 0x28  # Map ID for Oak's Lab (40 decimal, 0x28 hex - matches MapLocation.OAKS_LAB)
        oak_lab_name = "OAKS_LAB"

        # CRITICAL: Player must be adjacent and facing the Poké Ball to interact
        # From your description: facing north at [4,6] [4,7] [4,8] would mean
        # the player is at [4,7] facing north [0,-1] to interact with [4,6]

        self.add_marker(
            DevMarker(
                world_x=6,
                world_y=3,
                map_name=oak_lab_name,
                map_id=oak_lab_map_id,
                marker_type="STARTER_POKEMON",
                label="Charmander",
                description="Fire-type starter Pokémon - Choose by facing this tile from adjacent square and pressing A",
                marker_char="C",  # C for Charmander
                requires_facing=True,
                facing_direction="north",  # Stand south of it, face north
            )
        )

        self.add_marker(
            DevMarker(
                world_x=7,
                world_y=3,
                map_name=oak_lab_name,
                map_id=oak_lab_map_id,
                marker_type="STARTER_POKEMON",
                label="Squirtle",
                description="Water-type starter Pokémon - Choose by facing this tile from adjacent square and pressing A",
                marker_char="S",  # S for Squirtle
                requires_facing=True,
                facing_direction="north",
            )
        )

        self.add_marker(
            DevMarker(
                world_x=8,
                world_y=3,
                map_name=oak_lab_name,
                map_id=oak_lab_map_id,
                marker_type="STARTER_POKEMON",
                label="Bulbasaur",
                description="Grass/Poison-type starter Pokémon - Choose by facing this tile from adjacent square and pressing A",
                marker_char="B",  # B for Bulbasaur
                requires_facing=True,
                facing_direction="north",
            )
        )

        # Oak's position for reference
        self.add_marker(
            DevMarker(
                world_x=5,
                world_y=2,
                map_name=oak_lab_name,
                map_id=oak_lab_map_id,
                marker_type="OBJECTIVE",
                label="Professor Oak",
                description="Professor Oak - usually stands here after intro sequence",
                marker_char="O",  # O for Oak/Objective
                requires_facing=True,
            )
        )

        log.info(
            f"📍 Registered {len(self._markers.get(oak_lab_name, []))} dev markers for {oak_lab_name}"
        )

    def add_marker(self, marker: DevMarker):
        """Add a marker to the registry."""
        map_name = marker.map_name
        if map_name not in self._markers:
            self._markers[map_name] = []
        self._markers[map_name].append(marker)
        log.debug(
            f"📍 Dev marker registered: {marker.label} at [{marker.world_x},{marker.world_y}] on {map_name}"
        )

    def get_markers_for_map(
        self, map_name: str, marker_type: Optional[str] = None
    ) -> List[DevMarker]:
        """
        Get all dev markers for a specific map.

        Args:
            map_name: Map name to filter by
            marker_type: Optional marker type filter (e.g., "STARTER_POKEMON")

        Returns:
            List of DevMarker objects for this map
        """
        markers = self._markers.get(map_name, [])

        if marker_type:
            markers = [m for m in markers if m.marker_type == marker_type]

        return markers

    def get_overlay_markers_for_map(
        self,
        map_name: str,
        player_world_x: int,
        player_world_y: int,
        player_grid_x: int,
        player_grid_y: int,
        grid_width: int = 21,
        grid_height: int = 19,
    ) -> List[dict]:
        """
        Get dev markers formatted for minimap overlay display.

        Converts world coordinates to grid coordinates and filters
        to only include markers visible in the current minimap viewport.

        Args:
            map_name: Current map name
            player_world_x, player_world_y: Player's world coordinates
            player_grid_x, player_grid_y: Player's grid position (usually center)
            grid_width, grid_height: Minimap grid dimensions

        Returns:
            List of marker dicts compatible with lassMarkings format
        """
        markers = self.get_markers_for_map(map_name)
        overlay_markers = []

        for marker in markers:
            # Convert world coords to grid coords relative to player
            world_dx = marker.world_x - player_world_x
            world_dy = marker.world_y - player_world_y

            grid_x = player_grid_x + world_dx
            grid_y = player_grid_y + world_dy

            # Only include if visible in viewport
            if 0 <= grid_x < grid_width and 0 <= grid_y < grid_height:
                overlay_marker = marker.to_overlay_marker(grid_x, grid_y)
                overlay_markers.append(overlay_marker)
                log.debug(
                    f"📍 Dev marker visible: {marker.label} at grid [{grid_x},{grid_y}]"
                )

        return overlay_markers

    def get_llm_context_for_map(
        self,
        map_name: str,
        current_world_x: int,
        current_world_y: int,
        marker_type: Optional[str] = None,
    ) -> str:
        """
        Get formatted dev marker context for LLM prompts.

        Args:
            map_name: Current map name
            current_world_x, current_world_y: Player's current position
            marker_type: Optional filter for specific marker types

        Returns:
            Formatted string describing dev markers on this map
        """
        markers = self.get_markers_for_map(map_name, marker_type)

        if not markers:
            return ""

        lines = [
            "═══════════════════════════════════════",
            "📍 SPECIAL LOCATIONS (Dev Markers)",
            "═══════════════════════════════════════",
        ]

        # Group by marker type
        by_type: Dict[str, List[DevMarker]] = {}
        for marker in markers:
            if marker.marker_type not in by_type:
                by_type[marker.marker_type] = []
            by_type[marker.marker_type].append(marker)

        # Format by type
        for mtype, mlist in by_type.items():
            lines.append(f"\n{mtype}:")
            for marker in mlist:
                # Calculate distance
                dx = abs(marker.world_x - current_world_x)
                dy = abs(marker.world_y - current_world_y)
                distance = dx + dy

                # Direction hint
                directions = []
                if marker.world_y < current_world_y:
                    directions.append("NORTH")
                elif marker.world_y > current_world_y:
                    directions.append("SOUTH")
                if marker.world_x > current_world_x:
                    directions.append("EAST")
                elif marker.world_x < current_world_x:
                    directions.append("WEST")

                dir_str = "-".join(directions) if directions else "HERE"

                lines.append(f"  • {marker.get_llm_context()}")
                lines.append(f"    Distance: {distance} tiles {dir_str}")

        lines.append("═══════════════════════════════════════")

        return "\n".join(lines)

    def get_starter_pokemon_choices(self, map_name: str) -> List[DevMarker]:
        """
        Get starter Pokémon markers for LLM to choose from.

        Returns:
            List of STARTER_POKEMON markers
        """
        return self.get_markers_for_map(map_name, marker_type="STARTER_POKEMON")


# Global registry instance
_dev_marker_registry: Optional[DevMarkerRegistry] = None


def get_dev_marker_registry() -> DevMarkerRegistry:
    """Get the global dev marker registry (singleton)."""
    global _dev_marker_registry
    if _dev_marker_registry is None:
        _dev_marker_registry = DevMarkerRegistry()
        log.info("📍 Dev marker registry initialized")
    return _dev_marker_registry
