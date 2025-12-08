import os
import sys
import struct
import time
from pyAIAgent.game.graphics import dump_minimal_map, dump_minimap_map_array
from pyAIAgent.utils.socket_utils import readrange, send_command, _flush_socket
from pyAIAgent.utils.image_utils import capture
from pyAIAgent.game.data import get_species_map, get_location_name, decode_pokemon_text

DEFAULT_ROM = 'red.gb'

def get_rom_path():
    """Get ROM path from environment variable or default, relative to roms folder"""
    rom_name = os.getenv('POKEMON_ROM', DEFAULT_ROM)
    # If ROM path doesn't include a directory, assume it's in roms folder
    if os.path.sep not in rom_name and not os.path.isabs(rom_name):
        return os.path.join('roms', rom_name)
    return rom_name
MINI_MAP_SIZE = (21,21)

def get_state(sock) -> str:
    _flush_socket(sock)
    return send_command(sock, "state")

def get_party_text(sock) -> str:
    _flush_socket(sock)
    party = []
    try:
        header = readrange(sock, "0xD163", "8")
        count = header[0]
        species_map = get_species_map()

        # Limit party size to prevent index errors
        count = min(count, 6)  # Max party size is 6

        for slot in range(count):
            # Check if we have enough header bytes
            if len(header) <= 1 + slot:
                break

            data_addr = 0xD163 + 0x08 + slot * 44
            name_addr = 0xD163 + 0x152 + slot * 10
            d = readrange(sock, hex(data_addr), "44")
            raw_name = readrange(sock, hex(name_addr), "10")
            internal_id = header[1 + slot]

            # Now expect 4-tuple: (dex_no, mon_name, type1, type2)
            dex_no, mon_name, type1, type2 = species_map.get(
                internal_id,
                (None, f"ID 0x{internal_id:02X}", None, None)
            )

            hp_cur = struct.unpack(">H", d[1:3])[0]
            level = d[0x21]
            hp_max = struct.unpack(">H", d[0x22:0x24])[0]
            nickname = decode_pokemon_text(raw_name) or "(no nick)"

            # Build a types string, e.g. "Grass/Poison" or just "Fire"
            types = type1 if type1 else ""
            if type2:
                types += f"/{type2}"

            mon = {"name": mon_name, "level": level, "type": type1, "hp": hp_cur, "maxHp": hp_max, "nickname": nickname}
            party.append(mon)
    except Exception as e:
        log.warning(f"Error reading party data: {e}. Continuing with empty party.")
        return "Party: Unable to read party data"

    return party


def get_badges_text(sock) -> str:
    _flush_socket(sock)
    raw = readrange(sock, "0xD356", "1")
    flags = raw[0]
    names = ["Boulder","Cascade","Thunder","Rainbow","Soul","Marsh","Volcano","Earth"]
    have = [names[i] for i in range(8) if flags & (1 << i)]
    return have


def get_facing(sock) -> str:
    _flush_socket(sock)
    raw = readrange(sock, "0xC109", "1")[0]
    code = raw & 0xC
    if code == 0x0:
        return "down"
    elif code == 0x4:
        return "up"
    elif code == 0x8:
        return "left"
    elif code == 0xC:
        return "right"
    else:
        return f"unknown(0x{raw:02X})"


def get_location(sock) -> tuple[int, int, int, str] | None:
    _flush_socket(sock)
    mid = readrange(sock, "0xD35E", "1")[0]
    mapName = get_location_name(mid)
    tile_x = readrange(sock, "0xD362", "1")[0]
    tile_y = readrange(sock, "0xD361", "1")[0]
    map_w_blocks = readrange(sock, "0xD369", "1")[0]
    map_w_tiles = map_w_blocks * 2
    if map_w_tiles == 0:
        return None
    facing = get_facing(sock)
    return (mid, tile_x, tile_y, facing, mapName)





def get_sprites(sock) -> list[tuple[int, int]]:
    """
    Read Sprite Table from RAM (0xC100-0xC1FF) to get NPC coordinates.
    There are 16 slots, each 16 bytes.
    Offset +0: Picture ID (0 if inactive/hidden)
    Offset +4: Y Coordinate (Grid Y + 4)
    Offset +6: X Coordinate (Grid X + 4)
    """
    _flush_socket(sock)
    sprites = []
    try:
        # Read all 16 slots * 16 bytes = 256 bytes
        # Using 0xC100 (SpriteStateData1) which contains positions
        data = readrange(sock, "0xC100", "256")
        
        for i in range(16):
            offset = i * 16
            if offset + 6 >= len(data): 
                break
                
            picture_id = data[offset]
            # Offset 0 is picture ID. If 0, sprite is disabled/hidden.
            if picture_id != 0:
                # Valid sprite
                y_raw = data[offset + 4]
                x_raw = data[offset + 6] # X is at +6, not +5
                
                # Convert to 0-indexed grid coordinates
                # RAM stores value as Grid + 4
                idx_x = x_raw - 4
                idx_y = y_raw - 4
                
                # Simple sanity check for map bounds (0-30 roughly)
                if 0 <= idx_x < 80 and 0 <= idx_y < 80:
                    sprites.append((idx_x, idx_y))
                    print(f"DEBUG Sprite {i}: ID={picture_id} Raw=({x_raw},{y_raw}) -> ({idx_x},{idx_y})", file=sys.stderr)
        
        # Debug log to verify we are getting data
        if sprites:
            print(f"DEBUG: Found {len(sprites)} sprites at: {sprites}", file=sys.stderr)

    except Exception as e:
        log.warning(f"Error reading sprite data: {e}. continuing without sprites.")
        
    return sprites

# Updated prep_llm to include sprites
def prep_llm(sock) -> dict:
    import logging
    import socket
    log = logging.getLogger("prep_llm")
    
    # Log socket state before starting
    try:
        sock_fileno = sock.fileno()
        sock_timeout = sock.gettimeout()
        log.info(f"📡 prep_llm START: socket fd={sock_fileno}, timeout={sock_timeout}")
    except Exception as e:
        log.error(f"📡 prep_llm: Socket state check failed: {e}")
        return None
    
    try:
        t_start = time.time()
        log.debug("prep_llm: flushing socket...")
        _flush_socket(sock)
        
        log.debug("prep_llm: capturing screenshot...")
        t_cap = time.time()
        capture(sock, "latest.png")
        log.debug(f"prep_llm: capture took {time.time() - t_cap:.2f}s")
        
        time.sleep(0.5) # Increased wait to ensure FS sync
        _flush_socket(sock)
        
        log.debug("prep_llm: getting location...")
        t_loc = time.time()
        loc = get_location(sock)
        log.debug(f"prep_llm: get_location took {time.time() - t_loc:.2f}s")
        
        mid = None
        mapName = None
        map2D = ""

        if loc:
            mid, x, y, facing, mapName = loc
            log.debug(f"prep_llm: location = {mapName} ({mid}) at ({x},{y}) facing {facing}")
            
            rom_path = get_rom_path()
            log.debug("prep_llm: generating minimap...")
            t_map = time.time()
            minimap_img = dump_minimal_map(rom_path, mid, (x, y), grid_lines=True, crop=MINI_MAP_SIZE)
            if minimap_img:
                minimap_img.save("minimap.png")
            else:
                # Fallback if minimap generation failed (e.g., unknown tileset)
                from PIL import Image
                default_minimap = Image.new('RGB', (160, 160), color='gray')
                default_minimap.save("minimap.png")
            map2D = dump_minimap_map_array(rom_path, mid, (x, y), crop=MINI_MAP_SIZE)
            log.debug(f"prep_llm: minimap generation took {time.time() - t_map:.2f}s")
            position = (x, y)
        else:
            log.debug("prep_llm: no location data, creating default minimap")
            # no map data or in battle → create default white minimap
            from PIL import Image
            # Create a white square with same dimensions as typical minimap
            default_minimap = Image.new('RGB', (160, 160), color='white')
            default_minimap.save("minimap.png")
            position = None
            facing = None

        log.debug("prep_llm: getting party/badges...")
        t_party = time.time()
        party = get_party_text(sock)
        badges = get_badges_text(sock)
        log.debug(f"prep_llm: party/badges took {time.time() - t_party:.2f}s")

        total_time = time.time() - t_start
        log.info(f"📡 prep_llm DONE: total={total_time:.2f}s location={mapName}")
        
        return {
            "party":   party,
            "map_id": mid,
            "badges":  badges,
            "position": position,
            "facing":  facing,
            "map_name": mapName,
            "minimap_2d": map2D
        }
    except socket.timeout as e:
        log.error(f"📡 prep_llm: Socket TIMEOUT during operation: {e}")
        raise
    except socket.error as e:
        log.error(f"📡 prep_llm: Socket ERROR: {e} (errno={e.errno if hasattr(e, 'errno') else 'N/A'})")
        raise
    except Exception as e:
        log.error(f"📡 prep_llm: Unexpected error: {e}", exc_info=True)
        raise



def print_battle(sock) -> None:
    _flush_socket(sock)
    cur = readrange(sock, hex(0xD057), "1")[0]
    if cur == 0:
        print("Not currently in a battle.")
        return
    b = readrange(sock, hex(0xD05A), "1")[0]
    types = {
        0xF0: "Wild Battle",
        0xED: "Trainer Battle",
        0xEA: "Gym Leader Battle",
        0xF3: "Final Battle",
        0xF6: "Defeated Trainer",
        0xF9: "Defeated Wild Pokémon",
        0xFC: "Defeated Champion/Gym"
    }
    label = types.get(b, f"Unknown (0x{b:02X})")
    print(f"In battle: {label}")
