import logging
from typing import Tuple, Optional

log = logging.getLogger("game_state_manager")


def grid_to_world(
    grid_x: int,
    grid_y: int,
    player_grid_x: int,
    player_grid_y: int,
    player_world_x: int,
    player_world_y: int
) -> Tuple[int, int]:
    """
    Convert minimap grid coordinates to world coordinates.
    
    Args:
        grid_x, grid_y: Position in minimap grid
        player_grid_x, player_grid_y: Player's position in grid (usually center)
        player_world_x, player_world_y: Player's world coordinates
        
    Returns:
        (world_x, world_y) tuple
    """
    # Offset from player in grid space
    dx = grid_x - player_grid_x
    dy = grid_y - player_grid_y
    # Apply to world space
    return (player_world_x + dx, player_world_y + dy)


def world_to_grid(
    world_x: int,
    world_y: int,
    player_grid_x: int,
    player_grid_y: int,
    player_world_x: int,
    player_world_y: int
) -> Tuple[int, int]:
    """
    Convert world coordinates to minimap grid coordinates.
    
    Args:
        world_x, world_y: Position in world coordinates
        player_grid_x, player_grid_y: Player's position in grid (usually center)
        player_world_x, player_world_y: Player's world coordinates
        
    Returns:
        (grid_x, grid_y) tuple
    """
    # Offset from player in world space
    dx = world_x - player_world_x
    dy = world_y - player_world_y
    # Apply to grid space
    return (player_grid_x + dx, player_grid_y + dy)

def parse_minimap(minimap_2d: str, world_position: list = None) -> dict:
    """
    Pre-compute minimap analysis to reduce LLM hallucination.
    
    Args:
        minimap_2d: The raw minimap string
        world_position: Player's world coordinates [x, y] - used to convert grid coords to world coords
    
    Returns a dict with player position, grid dimensions, adjacent tiles, blocked directions,
    and world coordinate mappings for exits.
    """
    if not minimap_2d:
        return {}
    
    # Parse rows (split by semicolon, strip whitespace)
    rows = [row.strip() for row in minimap_2d.split(';') if row.strip()]
    if not rows:
        return {}
    
    num_rows = len(rows)
    num_cols = len(rows[0]) if rows else 0
    
    # Find player position (look for 'P' in the grid)
    player_row = -1
    player_col = -1
    for r_idx, row in enumerate(rows):
        p_idx = row.find('P')
        if p_idx >= 0:
            player_row = r_idx
            player_col = p_idx
            break
    
    if player_row < 0 or player_col < 0:
        return {"error": "Player 'P' not found in minimap"}
    
    # World coordinate conversion function
    # Grid is centered on player, so player's grid position maps to world position
    world_x = world_position[0] if world_position and len(world_position) >= 2 else None
    world_y = world_position[1] if world_position and len(world_position) >= 2 else None
    
    def grid_to_world(grid_col, grid_row):
        """Convert grid coordinates to world coordinates"""
        if world_x is None or world_y is None:
            return None
        # Offset from player's grid position
        dx = grid_col - player_col
        dy = grid_row - player_row
        return [world_x + dx, world_y + dy]
    
    # Get adjacent tiles
    def get_tile(row, col):
        if 0 <= row < num_rows and 0 <= col < len(rows[row]):
            return rows[row][col]
        return '?'  # Out of bounds
    
    north_tile = get_tile(player_row - 1, player_col)
    south_tile = get_tile(player_row + 1, player_col)
    east_tile = get_tile(player_row, player_col + 1)
    west_tile = get_tile(player_row, player_col - 1)
    
    # Determine blocked directions (B = blocked, W = walkable, O = exit)
    def is_blocked(tile):
        return tile == 'B'
    
    def is_exit(tile):
        return tile in ('O', 'D', 'E', '>', '<', '^', 'v')

    def is_walkable(tile):
        return tile in ('W', 'P', 'O', 'D', 'E', '>', '<', '^', 'v')
    
    blocked = []
    walkable = []
    exits = []
    
    if is_blocked(north_tile):
        blocked.append("NORTH (U)")
    elif is_exit(north_tile):
        exits.append(f"NORTH at [{player_col},{player_row-1}]")
        walkable.append("NORTH (U)")
    else:
        # Assuming ? or W is walkable-ish or at least not strictly blocked
        if north_tile != '?':
            walkable.append("NORTH (U)")
    
    if is_blocked(south_tile):
        blocked.append("SOUTH (D)")
    elif is_exit(south_tile):
        exits.append(f"SOUTH at [{player_col},{player_row+1}]")
        walkable.append("SOUTH (D)")
    else:
        if south_tile != '?':
            walkable.append("SOUTH (D)")
    
    if is_blocked(east_tile):
        blocked.append("EAST (R)")
    elif is_exit(east_tile):
        exits.append(f"EAST at [{player_col+1},{player_row}]")
        walkable.append("EAST (R)")
    else:
        if east_tile != '?':
            walkable.append("EAST (R)")
    
    if is_blocked(west_tile):
        blocked.append("WEST (L)")
    elif is_exit(west_tile):
        exits.append(f"WEST at [{player_col-1},{player_row}]")
        walkable.append("WEST (L)")
    else:
        if west_tile != '?':
            walkable.append("WEST (L)")
    
    # Find all O tiles in the minimap (with world coordinates and direction hints)
    o_tiles = []
    for r_idx, row in enumerate(rows):
        for c_idx, char in enumerate(row):
            if char in ('O', 'D', 'E', '>', '<', '^', 'v'):
                world_coords = grid_to_world(c_idx, r_idx)
                
                # Add direction hint based on position relative to grid
                dir_hint = ""
                if r_idx >= num_rows - 2:  # Bottom edge
                    dir_hint = " (SOUTH EXIT - step DOWN)"
                elif r_idx <= 1:  # Top edge
                    dir_hint = " (NORTH - step UP to enter)"
                elif c_idx >= num_cols - 2:  # Right edge
                    dir_hint = " (EAST EXIT)"
                elif c_idx <= 1:  # Left edge
                    dir_hint = " (WEST EXIT)"
                
                if world_coords:
                    o_tiles.append(f"Grid[{c_idx},{r_idx}] = World[{world_coords[0]},{world_coords[1]}]{dir_hint}")
                else:
                    o_tiles.append(f"Grid[{c_idx},{r_idx}]{dir_hint}")
    
    # Find all NPC tiles ('N') in the minimap
    npc_tiles = []
    for r_idx, row in enumerate(rows):
        for c_idx, char in enumerate(row):
            if char == 'N':
                world_coords = grid_to_world(c_idx, r_idx)
                if world_coords:
                    npc_tiles.append(f"Grid[{c_idx},{r_idx}] = World[{world_coords[0]},{world_coords[1]}]")
                else:
                    npc_tiles.append(f"Grid[{c_idx},{r_idx}]")

    # PASSAGE/CHOKEPOINT DETECTION
    passages = []  # List of detected passages/chokepoints
    
    # Scan for horizontal passages (W surrounded by B above and below)
    for r_idx in range(1, num_rows - 1):
        row = rows[r_idx]
        for c_idx in range(len(row)):
            tile = row[c_idx]
            if is_walkable(tile):
                above = get_tile(r_idx - 1, c_idx)
                below = get_tile(r_idx + 1, c_idx)
                
                # Horizontal passage: walkable with blocked above AND below
                if above == 'B' and below == 'B':
                    # Check if this is part of a longer passage
                    passage_width = 1
                    for check_col in range(c_idx + 1, min(c_idx + 10, len(row))):
                        if (is_walkable(get_tile(r_idx, check_col)) and
                            get_tile(r_idx - 1, check_col) == 'B' and
                            get_tile(r_idx + 1, check_col) == 'B'):
                            passage_width += 1
                        else:
                            break
                    
                    if passage_width >= 2:  # At least 2 tiles wide to be notable
                        # Calculate direction from player
                        dy = r_idx - player_row
                        dx = c_idx - player_col
                        direction = []
                        if dy < 0: direction.append("NORTH")
                        elif dy > 0: direction.append("SOUTH")
                        if dx < 0: direction.append("WEST")
                        elif dx > 0: direction.append("EAST")
                        dir_str = "-".join(direction) if direction else "HERE"
                        
                        passages.append({
                            "type": "horizontal_passage",
                            "start": f"[{c_idx},{r_idx}]",
                            "width": passage_width,
                            "direction": dir_str,
                            "distance": abs(dy) + abs(dx)
                        })
                        # Skip tiles we've already counted
                        break
    
    # Scan for vertical passages (W surrounded by B left and right)
    for c_idx in range(1, num_cols - 1):
        for r_idx in range(num_rows):
            if c_idx >= len(rows[r_idx]):
                continue
            tile = rows[r_idx][c_idx]
            if is_walkable(tile):
                left = get_tile(r_idx, c_idx - 1)
                right = get_tile(r_idx, c_idx + 1)
                
                # Vertical passage: walkable with blocked left AND right
                if left == 'B' and right == 'B':
                    # Check if this is part of a longer passage
                    passage_height = 1
                    for check_row in range(r_idx + 1, min(r_idx + 10, num_rows)):
                        if (check_row < num_rows and c_idx < len(rows[check_row]) and
                            is_walkable(get_tile(check_row, c_idx)) and
                            get_tile(check_row, c_idx - 1) == 'B' and
                            get_tile(check_row, c_idx + 1) == 'B'):
                            passage_height += 1
                        else:
                            break
                    
                    if passage_height >= 2:  # At least 2 tiles tall to be notable
                        # Calculate direction from player
                        dy = r_idx - player_row
                        dx = c_idx - player_col
                        direction = []
                        if dy < 0: direction.append("NORTH")
                        elif dy > 0: direction.append("SOUTH")
                        if dx < 0: direction.append("WEST")
                        elif dx > 0: direction.append("EAST")
                        dir_str = "-".join(direction) if direction else "HERE"
                        
                        passages.append({
                            "type": "vertical_passage",
                            "start": f"[{c_idx},{r_idx}]",
                            "height": passage_height,
                            "direction": dir_str,
                            "distance": abs(dy) + abs(dx)
                        })
                        break
    
    # Sort passages by distance from player
    passages.sort(key=lambda p: p.get("distance", 999))
    
    # Format passages for output (top 3 closest)
    passage_strs = []
    for p in passages[:3]:
        if p["type"] == "horizontal_passage":
            passage_strs.append(f"🌉 Horizontal path at {p['start']} ({p['width']} tiles wide) - go {p['direction']}")
        else:
            passage_strs.append(f"🚶 Vertical path at {p['start']} ({p['height']} tiles tall) - go {p['direction']}")

    return {
        "grid_size": f"{num_cols}x{num_rows}",
        "player_position": f"[{player_col},{player_row}]",
        "player_row": player_row,
        "player_col": player_col,
        "adjacent_tiles": {
            "north": f"[{player_col},{player_row-1}] = '{north_tile}'",
            "south": f"[{player_col},{player_row+1}] = '{south_tile}'",
            "east": f"[{player_col+1},{player_row}] = '{east_tile}'",
            "west": f"[{player_col-1},{player_row}] = '{west_tile}'"
        },
        "blocked_directions": blocked,
        "walkable_directions": walkable,
        "adjacent_exits": exits,
        "all_exit_tiles": o_tiles,
        "npc_tiles": npc_tiles,
        "passages": passage_strs
    }
