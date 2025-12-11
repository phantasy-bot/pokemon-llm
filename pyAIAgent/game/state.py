import os
import sys
import struct
import time
import logging
from pyAIAgent.game.graphics import dump_minimal_map, dump_minimap_map_array
from pyAIAgent.utils.socket_utils import readrange, send_command, _flush_socket
from pyAIAgent.utils.image_utils import capture
from pyAIAgent.game.data import get_species_map, get_location_name, decode_pokemon_text, get_item_map, get_move_map

log = logging.getLogger(__name__)

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


def get_text_state(sock) -> dict:
    """
    Read text/dialog related memory flags.
    
    Returns:
        dict with:
        - text_speed: Current text speed setting (0xD355)
        - text_printing: Text printing flags (0xD358)
        - is_printing: True if text is currently being printed
    """
    _flush_socket(sock)
    try:
        text_speed = readrange(sock, "0xD355", "1")[0]
        text_flags = readrange(sock, "0xD358", "1")[0]
        
        # Bit 0 = 0 means delay limited to 1 frame
        # Bit 1 = 0 means no delay (instant text)
        is_printing = (text_flags & 0x03) != 0x03  # Either bit cleared = text active
        
        return {
            "text_speed": text_speed,
            "text_flags": text_flags,
            "is_printing": is_printing
        }
    except Exception as e:
        log.warning(f"Error reading text state: {e}")
        return {"text_speed": 0, "text_flags": 0, "is_printing": False}


def get_dialog_text(sock) -> str | None:
    """
    Read the tile screen buffer to extract dialog text.
    
    The dialog box in Pokemon Red occupies the bottom 4 rows of the screen.
    Screen buffer is at 0xC3A0-C507 (360 bytes for 20x18 tiles).
    
    Returns the decoded dialog text, or None if no dialog detected.
    """
    _flush_socket(sock)
    try:
        # Read the tile buffer (360 bytes = 20 columns x 18 rows)
        tiles = readrange(sock, "0xC3A0", "360")
        
        # Dialog box is typically in the bottom 4 rows (rows 14-17)
        # Each row is 20 tiles
        dialog_rows = []
        for row in range(14, 18):  # Bottom 4 rows
            start = row * 20
            end = start + 20
            row_tiles = tiles[start:end]
            row_text = decode_pokemon_text(bytes(row_tiles))
            if row_text.strip():
                dialog_rows.append(row_text.strip())
        
        if dialog_rows:
            return ' '.join(dialog_rows)
        return None
    except Exception as e:
        log.warning(f"Error reading dialog text: {e}")
        return None


def get_battle_state(sock) -> dict:
    """
    Read battle-related memory.
    
    Returns:
        dict with:
        - in_battle: True if in a battle
        - battle_type: Type of battle (wild, trainer, gym, etc.)
        - turn_count: Number of turns in current battle
        - move_menu_type: 0 = regular, 1 = mimic, other = text boxes
    """
    _flush_socket(sock)
    try:
        battle_flag = readrange(sock, "0xD057", "1")[0]
        battle_type = readrange(sock, "0xD05A", "1")[0] if battle_flag else 0
        turn_count = readrange(sock, "0xCCD5", "1")[0] if battle_flag else 0
        move_menu = readrange(sock, "0xCCDB", "1")[0] if battle_flag else 0
        
        # Decode battle type
        battle_types = {
            0xF0: "wild",
            0xED: "trainer", 
            0xEA: "gym_leader",
            0xF3: "final",
            0xF6: "defeated_trainer",
            0xF9: "defeated_wild",
            0xFC: "defeated_champion"
        }
        
        return {
            "in_battle": battle_flag != 0,
            "battle_type": battle_types.get(battle_type, f"unknown_{battle_type:02X}"),
            "turn_count": turn_count,
            "move_menu_type": move_menu
        }
    except Exception as e:
        log.warning(f"Error reading battle state: {e}")
        return {"in_battle": False, "battle_type": None, "turn_count": 0, "move_menu_type": 0}


def get_menu_state(sock) -> dict:
    """
    Read menu-related memory for tracking menu interactions.
    
    Returns:
        dict with:
        - selected_item: Currently selected menu item (0 = topmost)
        - last_selected: Previously selected item
        - menu_item_count: Total items in current menu
    """
    _flush_socket(sock)
    try:
        selected = readrange(sock, "0xCC26", "1")[0]
        last_item = readrange(sock, "0xCC28", "1")[0]
        prev_selected = readrange(sock, "0xCC2A", "1")[0]
        
        return {
            "selected_item": selected,
            "menu_item_count": last_item + 1,  # Last item ID + 1 = count
            "last_selected": prev_selected
        }
    except Exception as e:
        log.warning(f"Error reading menu state: {e}")
        return {"selected_item": 0, "menu_item_count": 0, "last_selected": 0}


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


def get_map_state(sock) -> dict:
    """
    Read map-specific state (Phase 2).
    0xD365: Last Map ID (for warp handling)
    0xD887: Wild Encounter Rate
    """
    _flush_socket(sock)
    try:
        last_map = readrange(sock, "0xD365", "1")[0]
        encounter_rate = readrange(sock, "0xD887", "1")[0]
        
        return {
            "last_map_id": last_map,
            "encounter_rate": encounter_rate
        }
    except Exception as e:
        log.warning(f"Error reading map state: {e}")
        return {"last_map_id": 0, "encounter_rate": 0}


def get_battle_status_flags(sock) -> dict:
    """
    Read detailed battle status flags (Phase 3).
    Player: 0xD062-D064 (3 bytes) (Wait, map says D062..D064)
    Enemy: 0xD067-D069 (3 bytes)
    
    Status bits (approximate):
    Byte 0: Sleep (0-2), Poison (3), Burn (4), Freeze (5), Paralyze (6)
    Byte 1-2: Volatile statuses (Confusion, Leech Seed, etc)
    """
    _flush_socket(sock)
    try:
        # Check battle flag first
        if readrange(sock, "0xD057", "1")[0] == 0:
            return None
            
        p_status = readrange(sock, "0xD062", "3")
        e_status = readrange(sock, "0xD067", "3") # Assuming +5 offset for enemy? Need to verify distance
        # Standard Red RAM: Enemy is usually after Player data.
        # Player Battle Status: D062-D064? 
        # Actually standard main status (SLP/PSN/etc) is D16F for active pokemon?
        # D062 is "Player Pokemon Status" in battle RAM usually.
        
        def parse_main_status(byte_val):
            if byte_val == 0: return "OK"
            statuses = []
            if byte_val & 0x07: statuses.append(f"Sleep({byte_val & 0x07})")
            if byte_val & 0x08: statuses.append("Poison")
            if byte_val & 0x10: statuses.append("Burn")
            if byte_val & 0x20: statuses.append("Freeze")
            if byte_val & 0x40: statuses.append("Paralyze")
            return ", ".join(statuses)
            
        return {
            "player_status_raw": [f"{b:02X}" for b in p_status],
            "enemy_status_raw": [f"{b:02X}" for b in e_status],
            "player_main_status": parse_main_status(p_status[0]),
            "enemy_main_status": parse_main_status(e_status[0])
        }
    except Exception as e:
        log.warning(f"Error reading battle status: {e}")
        return None

def get_stat_modifiers(sock) -> dict:
    """
    Read battle stat modifiers (Phase 3).
    Player: 0xCD1A-CD20 (7 bytes? Atk, Def, Spd, Spc, Acc, Eva?)
    Enemy: 0xCD2E-CD34
    
    Values: 7 = Neutral. >7 = Buffed. <7 = Debuffed.
    """
    _flush_socket(sock)
    try:
         # Check battle flag first
        if readrange(sock, "0xD057", "1")[0] == 0:
            return None
            
        # Reading 6 bytes: Atk, Def, Spd, Spc, Acc, Eva
        p_stats = readrange(sock, "0xCD1A", "6") 
        e_stats = readrange(sock, "0xCD2E", "6")
        
        stat_names = ["Atk", "Def", "Spd", "Spc", "Acc", "Eva"]
        
        def parse_stats(data):
            mods = {}
            for i, val in enumerate(data):
                if i < len(stat_names):
                    # 7 is neutral (stage 0)
                    # 1-6 are debuffs (-6 to -1)
                    # 8-13 are buffs (+1 to +6)
                    stage = val - 7
                    if stage != 0:
                        mods[stat_names[i]] = stage
            return mods
            
        return {
            "player_mods": parse_stats(p_stats),
            "enemy_mods": parse_stats(e_stats)
        }
    except Exception as e:
        log.warning(f"Error reading stat modifiers: {e}")
        return None


def get_money(sock) -> int:
    """
    Read player money (BCD encoded, 3 bytes at 0xD347).
    """
    _flush_socket(sock)
    try:
        data = readrange(sock, "0xD347", "3")
        # Money is stored as BCD (Binary Coded Decimal)
        # e.g., 0x12 0x34 0x56 = 123456
        money_str = "".join(f"{b:02X}" for b in data)
        return int(money_str)
    except Exception as e:
        log.warning(f"Error reading money: {e}")
        return 0


def get_inventory(sock) -> list[dict]:
    """
    Read player inventory.
    0xD31D: Item count
    0xD31E + (i*2): Item ID
    0xD31E + (i*2) + 1: Quantity
    """
    _flush_socket(sock)
    inventory = []
    try:
        item_map = get_item_map()
        count_data = readrange(sock, "0xD31D", "1")
        count = count_data[0]
        
        # Limit count to avoid reading garbage if memory value is weird
        count = min(count, 20) 
        
        if count > 0:
            # Read item list (count * 2 bytes)
            # 0xD31E is start of item list
            item_data = readrange(sock, "0xD31E", str(count * 2))
            
            for i in range(count):
                item_id = item_data[i * 2]
                quantity = item_data[i * 2 + 1]
                item_name = item_map.get(item_id, f"Unknown(0x{item_id:02X})")
                inventory.append({
                    "item_id": item_id,
                    "name": item_name,
                    "count": quantity
                })
    except Exception as e:
        log.warning(f"Error reading inventory: {e}")
        
    return inventory


def get_enemy_pokemon(sock) -> dict | None:
    """
    Get current enemy Pokemon in battle.
    """
    _flush_socket(sock)
    try:
        # Check if in battle first
        battle_flag = readrange(sock, "0xD057", "1")[0]
        if battle_flag == 0:
            return None
            
        species_id = readrange(sock, "0xCFE5", "1")[0]
        hp_data = readrange(sock, "0xCFE6", "2")
        level = readrange(sock, "0xCFE8", "1")[0]
        # Moves: 4 bytes at 0xCFED
        moves_data = readrange(sock, "0xCFED", "4")
        
        hp = struct.unpack(">H", hp_data)[0]
        
        species_map = get_species_map()
        move_map = get_move_map()
        
        dex, name, type1, type2 = species_map.get(species_id, (0, "Unknown", "Normal", None))
        
        moves = []
        for mid in moves_data:
            if mid != 0:
                moves.append(move_map.get(mid, f"Move(0x{mid:02X})"))
                
        return {
            "name": name,
            "level": level,
            "hp": hp,
            "types": [t for t in [type1, type2] if t],
            "moves": moves,
            "species_id": species_id
        }
    except Exception as e:
        log.warning(f"Error reading enemy pokemon: {e}")
        return None

def get_active_battle_pokemon(sock) -> dict | None:
    """
    Get current active player Pokemon in battle.
    """
    _flush_socket(sock)
    try:
        battle_flag = readrange(sock, "0xD057", "1")[0]
        if battle_flag == 0:
            return None
            
        party_idx = readrange(sock, "0xD014", "1")[0]
        hp_data = readrange(sock, "0xD015", "2") # Current HP in battle
        level = readrange(sock, "0xD022", "1")[0] # Current level in battle
        moves_data = readrange(sock, "0xD01C", "4")
        
        current_hp = struct.unpack(">H", hp_data)[0]
        
        # Get max HP from party data to calculating percentage
        # Party struct is 44 bytes, starts at 0xD163 + 8
        # Max HP is at offset 0x22 (34)
        party_start = 0xD163 + 0x08 + (party_idx * 44)
        max_hp_addr = party_start + 0x22
        max_hp_data = readrange(sock, hex(max_hp_addr), "2")
        max_hp = struct.unpack(">H", max_hp_data)[0]

        move_map = get_move_map()
        moves = []
        for mid in moves_data:
            if mid != 0:
                moves.append(move_map.get(mid, f"Move(0x{mid:02X})"))

        return {
            "index": party_idx,
            "level": level,
            "hp": current_hp,
            "max_hp": max_hp,
            "moves": moves
        }
    except Exception as e:
        log.warning(f"Error reading active battle pokemon: {e}")
        return None

def get_event_flags(sock) -> dict:
    """
    Read key story event flags.
    """
    _flush_socket(sock)
    flags = {}
    try:
        # Single byte reads for simplicity
        # SS Anne: 0xD803 (bit 0?) - checking non-zero for now
        # Actually D803 bit 0 is SS Anne Here
        ss_anne = readrange(sock, "0xD803", "1")[0]
        flags["ss_anne_here"] = (ss_anne & 1) != 0
        
        town_map = readrange(sock, "0xD5F3", "1")[0]
        flags["have_town_map"] = (town_map & 1) != 0 # Often bit 0 or non-zero
        
        oaks_parcel = readrange(sock, "0xD60D", "1")[0]
        flags["have_oaks_parcel"] = (oaks_parcel & 2) != 0 # Usually bit 1 for "delivered"? Checking non-zero.
        # Actually docs say: D60D - Have Oak's Parcel? (Bit 1?) - let's assume boolean byte for now or check map
        
        lapras = readrange(sock, "0xD72E", "1")[0]
        flags["got_lapras"] = (lapras & 1) != 0

        # Flash ability (HM05) - usually check badge or HM in bag, but map palette 0xD35D can indicate flash usage
        
    except Exception as e:
        log.warning(f"Error reading event flags: {e}")
        
    return flags

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
        
        # Don't override socket timeout - trust the driver (llmdriver.py) to set it correctly
        # This prevents prep_llm from timing out prematurely (e.g. at 8s instead of 15s)
        
        log.info("prep_llm: flushing socket...")
        _flush_socket(sock)
        
        log.info("prep_llm: capturing screenshot...")
        t_cap = time.time()
        capture(sock, "latest.png")
        log.info(f"prep_llm: capture took {time.time() - t_cap:.2f}s")
        
        # Removed sleep(1.0) - capture is synchronous and complete, no need to wait
        # This saves 1s of timeout budget
        _flush_socket(sock)
        
        log.info("prep_llm: getting location...")
        t_loc = time.time()
        loc = get_location(sock)

        log.info(f"prep_llm: get_location took {time.time() - t_loc:.2f}s")
        
        mid = None
        mapName = None
        map2D = ""

        if loc:
            mid, x, y, facing, mapName = loc
            log.info(f"prep_llm: location = {mapName} ({mid}) at ({x},{y}) facing {facing}")
            
            rom_path = get_rom_path()
            log.info("prep_llm: generating minimap...")
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
            log.info(f"prep_llm: minimap generation took {time.time() - t_map:.2f}s")
            position = (x, y)
        else:
            log.info("prep_llm: no location data, creating default minimap")
            # no map data or in battle → create default white minimap
            from PIL import Image
            # Create a white square with same dimensions as typical minimap
            default_minimap = Image.new('RGB', (160, 160), color='white')
            default_minimap.save("minimap.png")
            position = None
            facing = None

        log.info("prep_llm: getting party/badges...")
        t_party = time.time()
        party = get_party_text(sock)
        badges = get_badges_text(sock)
        log.info(f"prep_llm: party/badges took {time.time() - t_party:.2f}s")

        # New memory reads for dialog/battle/menu state
        log.info("prep_llm: getting extended game state...")
        t_ext = time.time()
        text_state = get_text_state(sock)
        battle_state = get_battle_state(sock)
        menu_state = get_menu_state(sock)
        
        log.info("prep_llm: getting money/inventory/events...")
        t_misc = time.time()
        money = get_money(sock)
        inventory = get_inventory(sock)
        event_flags = get_event_flags(sock)
        map_state = get_map_state(sock)
        
        # Battle extra data
        enemy_mon = None
        active_mon = None
        battle_status = None
        stat_mods = None
        
        if battle_state.get("in_battle"):
            enemy_mon = get_enemy_pokemon(sock)
            active_mon = get_active_battle_pokemon(sock)
            battle_status = get_battle_status_flags(sock)
            stat_mods = get_stat_modifiers(sock)
            
        log.info(f"prep_llm: misc data took {time.time() - t_misc:.2f}s")
        
        # Try to extract dialog text if text appears to be printing
        dialog_text = None
        if text_state.get("is_printing") or battle_state.get("in_battle"):
            dialog_text = get_dialog_text(sock)
        log.info(f"prep_llm: extended state took {time.time() - t_ext:.2f}s")

        total_time = time.time() - t_start
        log.info(f"📡 prep_llm DONE: total={total_time:.2f}s location={mapName}")
        
        return {
            "party":   party,
            "map_id": mid,
            "badges":  badges,
            "position": position,
            "facing":  facing,
            "map_name": mapName,
            "minimap_2d": map2D,
            # New extended state
            "dialog_text": dialog_text,
            "text_state": text_state,
            "battle_state": battle_state,
            "menu_state": menu_state,
            "money": money,
            "inventory": inventory,
            "event_flags": event_flags,
            "map_state": map_state,
            "enemy_pokemon": enemy_mon,
            "active_pokemon": active_mon,
            "battle_status": battle_status,
            "stat_modifiers": stat_mods
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
