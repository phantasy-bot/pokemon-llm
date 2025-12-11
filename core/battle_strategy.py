"""
Battle Strategy Module for Pokemon LLM

Uses game memory reads for accurate battle decisions without relying on LLM vision.
Implements type effectiveness chart and rule-based combat logic.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pyAIAgent.utils.socket_utils import readrange, _flush_socket
from pyAIAgent.game.data import get_species_map

# Pokemon Type Effectiveness Chart
# Format: (attacker_type, defender_type): multiplier
TYPE_CHART = {
    # Super effective (2x)
    ("Fire", "Grass"): 2.0, ("Fire", "Ice"): 2.0, ("Fire", "Bug"): 2.0,
    ("Water", "Fire"): 2.0, ("Water", "Ground"): 2.0, ("Water", "Rock"): 2.0,
    ("Electric", "Water"): 2.0, ("Electric", "Flying"): 2.0,
    ("Grass", "Water"): 2.0, ("Grass", "Ground"): 2.0, ("Grass", "Rock"): 2.0,
    ("Ice", "Grass"): 2.0, ("Ice", "Ground"): 2.0, ("Ice", "Flying"): 2.0, ("Ice", "Dragon"): 2.0,
    ("Fighting", "Normal"): 2.0, ("Fighting", "Ice"): 2.0, ("Fighting", "Rock"): 2.0,
    ("Poison", "Grass"): 2.0, ("Poison", "Bug"): 2.0,
    ("Ground", "Fire"): 2.0, ("Ground", "Electric"): 2.0, ("Ground", "Poison"): 2.0, ("Ground", "Rock"): 2.0,
    ("Flying", "Grass"): 2.0, ("Flying", "Fighting"): 2.0, ("Flying", "Bug"): 2.0,
    ("Psychic", "Fighting"): 2.0, ("Psychic", "Poison"): 2.0,
    ("Bug", "Grass"): 2.0, ("Bug", "Psychic"): 2.0, ("Bug", "Poison"): 2.0,
    ("Rock", "Fire"): 2.0, ("Rock", "Ice"): 2.0, ("Rock", "Flying"): 2.0, ("Rock", "Bug"): 2.0,
    ("Ghost", "Ghost"): 2.0, ("Ghost", "Psychic"): 2.0,
    ("Dragon", "Dragon"): 2.0,
    
    # Not very effective (0.5x)
    ("Fire", "Fire"): 0.5, ("Fire", "Water"): 0.5, ("Fire", "Rock"): 0.5, ("Fire", "Dragon"): 0.5,
    ("Water", "Water"): 0.5, ("Water", "Grass"): 0.5, ("Water", "Dragon"): 0.5,
    ("Electric", "Electric"): 0.5, ("Electric", "Grass"): 0.5, ("Electric", "Dragon"): 0.5,
    ("Grass", "Fire"): 0.5, ("Grass", "Grass"): 0.5, ("Grass", "Poison"): 0.5, 
    ("Grass", "Flying"): 0.5, ("Grass", "Bug"): 0.5, ("Grass", "Dragon"): 0.5,
    ("Ice", "Fire"): 0.5, ("Ice", "Water"): 0.5, ("Ice", "Ice"): 0.5,
    ("Fighting", "Poison"): 0.5, ("Fighting", "Flying"): 0.5, ("Fighting", "Psychic"): 0.5, ("Fighting", "Bug"): 0.5,
    ("Poison", "Poison"): 0.5, ("Poison", "Ground"): 0.5, ("Poison", "Rock"): 0.5, ("Poison", "Ghost"): 0.5,
    ("Ground", "Grass"): 0.5, ("Ground", "Bug"): 0.5,
    ("Flying", "Electric"): 0.5, ("Flying", "Rock"): 0.5,
    ("Psychic", "Psychic"): 0.5,
    ("Bug", "Fire"): 0.5, ("Bug", "Fighting"): 0.5, ("Bug", "Flying"): 0.5, ("Bug", "Ghost"): 0.5,
    ("Rock", "Fighting"): 0.5, ("Rock", "Ground"): 0.5,
    ("Ghost", "Normal"): 0.0, ("Ghost", "Psychic"): 0.0,  # Gen 1 ghost bug
    ("Normal", "Rock"): 0.5,
    
    # No effect (0x)
    ("Normal", "Ghost"): 0.0,
    ("Electric", "Ground"): 0.0,
    ("Fighting", "Ghost"): 0.0,
    ("Poison", "Ghost"): 0.0,  # Gen 1
    ("Ground", "Flying"): 0.0,
}

# Move data (power, type, PP, effect_type)
# effect_type: "damage", "status", "stat", "special"
MOVES = {
    0x01: ("Pound", 40, "Normal", 35, "damage"),
    0x02: ("Karate Chop", 50, "Normal", 25, "damage"),
    0x03: ("Double Slap", 15, "Normal", 10, "damage"),
    0x04: ("Comet Punch", 18, "Normal", 15, "damage"),
    0x05: ("Mega Punch", 80, "Normal", 20, "damage"),
    0x06: ("Pay Day", 40, "Normal", 20, "damage"),
    0x07: ("Fire Punch", 75, "Fire", 15, "damage"),
    0x08: ("Ice Punch", 75, "Ice", 15, "damage"),
    0x09: ("Thunder Punch", 75, "Electric", 15, "damage"),
    0x0A: ("Scratch", 40, "Normal", 35, "damage"),
    0x0B: ("Vice Grip", 55, "Normal", 30, "damage"),
    0x0C: ("Guillotine", 0, "Normal", 5, "special"),
    0x0D: ("Razor Wind", 80, "Normal", 10, "damage"),
    0x21: ("Tackle", 35, "Normal", 35, "damage"),
    0x22: ("Body Slam", 85, "Normal", 15, "damage"),
    0x23: ("Wrap", 15, "Normal", 20, "damage"),
    0x24: ("Take Down", 90, "Normal", 20, "damage"),
    0x25: ("Thrash", 90, "Normal", 20, "damage"),
    0x26: ("Double-Edge", 100, "Normal", 15, "damage"),
    0x33: ("Ember", 40, "Fire", 25, "damage"),
    0x34: ("Flamethrower", 95, "Fire", 15, "damage"),
    0x37: ("Water Gun", 40, "Water", 25, "damage"),
    0x38: ("Hydro Pump", 120, "Water", 5, "damage"),
    0x39: ("Surf", 95, "Water", 15, "damage"),
    0x3A: ("Ice Beam", 95, "Ice", 10, "damage"),
    0x3B: ("Blizzard", 120, "Ice", 5, "damage"),
    0x4F: ("Sleep Powder", 0, "Grass", 15, "status"),
    0x4E: ("Stun Spore", 0, "Grass", 30, "status"), 
    0x55: ("Thunderbolt", 95, "Electric", 15, "damage"),
    0x57: ("Thunder", 120, "Electric", 10, "damage"),
    0x59: ("Earthquake", 100, "Ground", 10, "damage"),
    0x5B: ("Psychic", 90, "Psychic", 10, "damage"),
    0x56: ("Thunder Wave", 0, "Electric", 20, "status"),
    0x60: ("Hypnosis", 0, "Psychic", 20, "status"),
}


@dataclass
class BattleState:
    """Current battle state from memory reads"""
    in_battle: bool
    battle_type: str  # "wild", "trainer", "gym"
    
    # Player's active Pokemon
    player_pokemon: str
    player_hp: int
    player_max_hp: int
    player_level: int
    player_types: tuple
    player_status: str  # "OK", "SLP", "PSN", etc.
    
    # Enemy Pokemon
    enemy_pokemon: str
    enemy_hp_percent: int  # 0-100 estimated from bar
    enemy_types: tuple
    enemy_level: int
    enemy_status: str   # "OK", "SLP", "PSN", etc.
    
    # Available moves with PP
    moves: List[Dict]  # [{"name": "Tackle", "power": 35, "type": "Normal", "pp": 20}, ...]
    
    # Menu cursor position
    cursor_position: int


def get_type_effectiveness(move_type: str, defender_types: tuple) -> float:
    """Calculate type effectiveness multiplier"""
    multiplier = 1.0
    for def_type in defender_types:
        if def_type:
            mult = TYPE_CHART.get((move_type, def_type), 1.0)
            multiplier *= mult
    return multiplier

def decode_status(status_byte: int) -> str:
    """Decode Gen 1 status byte"""
    if status_byte == 0:
        return "OK"
    if status_byte & 0x40: return "PAR" # Paralysis
    if status_byte & 0x20: return "FRZ" # Freeze
    if status_byte & 0x10: return "BRN" # Burn
    if status_byte & 0x08: return "PSN" # Poison
    if status_byte & 0x07: return "SLP" # Sleep
    return "BAD"

def read_battle_state(sock) -> Optional[BattleState]:
    """Read current battle state from game memory"""
    _flush_socket(sock)
    
    # Check if in battle
    battle_flag = readrange(sock, "0xD057", "1")[0]
    if battle_flag == 0:
        return None
    
    # Battle type
    battle_type_byte = readrange(sock, "0xD05A", "1")[0]
    battle_types = {
        0xF0: "wild",
        0xED: "trainer", 
        0xEA: "gym",
        0xF3: "elite4",
    }
    battle_type = battle_types.get(battle_type_byte, "unknown")
    
    # Player's active Pokemon data (from party slot 0 for simplicity, actually from battle struct)
    species_map = get_species_map()
    
    # Read player Pokemon species and stats
    player_species = readrange(sock, "0xD014", "1")[0]
    player_hp = int.from_bytes(readrange(sock, "0xD015", "2"), 'big')
    player_max_hp = int.from_bytes(readrange(sock, "0xD023", "2"), 'big')
    player_level = readrange(sock, "0xD022", "1")[0]
    player_status_byte = readrange(sock, "0xD018", "1")[0] # wBattleMonStatus
    
    player_info = species_map.get(player_species, (None, "Unknown", "Normal", None))
    player_name = player_info[1]
    player_types = (player_info[2], player_info[3])
    
    # Enemy Pokemon data
    enemy_species = readrange(sock, "0xCFE5", "1")[0]
    enemy_level = readrange(sock, "0xCFF3", "1")[0]
    enemy_status_byte = readrange(sock, "0xCFE9", "1")[0] # wEnemyMonStatus (verified 0xCFE9 is standard)
    
    # Enemy HP is tricky - read the bar position (0xCF93-0xCF94)
    enemy_hp_current = int.from_bytes(readrange(sock, "0xCFE6", "2"), 'big')
    enemy_hp_max = int.from_bytes(readrange(sock, "0xCFF4", "2"), 'big')
    enemy_hp_percent = int((enemy_hp_current / max(enemy_hp_max, 1)) * 100) if enemy_hp_max > 0 else 50
    
    enemy_info = species_map.get(enemy_species, (None, "Unknown", "Normal", None))
    enemy_name = enemy_info[1]
    enemy_types = (enemy_info[2], enemy_info[3])
    
    # Read player's moves (4 moves starting at 0xD01C)
    moves = []
    move_bytes = readrange(sock, "0xD01C", "4")
    pp_bytes = readrange(sock, "0xD02D", "4")
    
    for i, (move_id, pp) in enumerate(zip(move_bytes, pp_bytes)):
        if move_id == 0:
            continue
        move_data = MOVES.get(move_id, (f"Move#{move_id}", 40, "Normal", 20, "damage"))
        moves.append({
            "index": i,
            "id": move_id,
            "name": move_data[0],
            "power": move_data[1],
            "type": move_data[2],
            "pp": pp & 0x3F,  # Lower 6 bits
            "max_pp": move_data[3],
            "effect": move_data[4] if len(move_data) > 4 else "damage"
        })
    
    # Menu cursor (0xCC26)
    cursor = readrange(sock, "0xCC26", "1")[0]
    
    return BattleState(
        in_battle=True,
        battle_type=battle_type,
        player_pokemon=player_name,
        player_hp=player_hp,
        player_max_hp=player_max_hp,
        player_level=player_level,
        player_types=player_types,
        player_status=decode_status(player_status_byte),
        enemy_pokemon=enemy_name,
        enemy_hp_percent=enemy_hp_percent,
        enemy_types=enemy_types,
        enemy_level=enemy_level,
        enemy_status=decode_status(enemy_status_byte),
        moves=moves,
        cursor_position=cursor
    )


def choose_battle_action(battle_state: BattleState, inventory: List[Dict] = None) -> Dict[str, Any]:
    """
    Choose the best battle action based on current state.
    Returns action dict for the LLM to execute.
    
    inventory format: [{'name': 'POKE BALL', 'count': 5}, ...]
    """
    if not battle_state or not battle_state.in_battle:
        return {"type": "none", "reason": "Not in battle"}
    
    hp_percent = (battle_state.player_hp / max(battle_state.player_max_hp, 1)) * 100
    
    # Flatten inventory for easier lookup
    inv_map = {}
    if inventory:
        for item in inventory:
            inv_map[item.get('name', '').upper()] = item.get('count', 1)
            
    has_potions = any(k for k in inv_map.keys() if "POTION" in k)
    
    ball_priority = ["MASTER BALL", "ULTRA BALL", "GREAT BALL", "POKE BALL"]
    available_balls = [b for b in ball_priority if inv_map.get(b, 0) > 0]
    
    # ═════════════════════════════════════════════════════════════════════════
    # PRIORITY 1: CATCH (If Wild + Weak/Statused)
    # ═════════════════════════════════════════════════════════════════════════
    if battle_state.battle_type == "wild" and available_balls:
        # Conditions to throw ball:
        # 1. Very low HP (<25%)
        # 2. Statused AND Low HP (<50%)
        # 3. Rare pokemon (Not implemented yet, but could be)
        
        should_throw = False
        catch_reason = ""
        
        if battle_state.enemy_hp_percent < 25:
            should_throw = True
            catch_reason = f"Enemy weak ({battle_state.enemy_hp_percent}%)"
        elif battle_state.enemy_status != "OK" and battle_state.enemy_hp_percent < 50:
            should_throw = True
            catch_reason = f"Enemy statused ({battle_state.enemy_status}) and weak"
            
        if should_throw:
            ball_to_use = available_balls[0] # Use best available or standard? Let's use best for now or generic logic
            # Using safest ball logic:
            if "POKE BALL" in available_balls and battle_state.enemy_level < 20: 
                ball_to_use = "POKE BALL"
            
            return {
                "type": "catch",
                "action": "D;D;A;", # Navigate to Item (approximate) - LLM usually handles menu nav better with specific instruction
                "reason": f"CATCH CHANCE! {catch_reason}. Use {ball_to_use} now!",
                "item": ball_to_use
            }

    # ═════════════════════════════════════════════════════════════════════════
    # PRIORITY 2: SURVIVAL
    # ═════════════════════════════════════════════════════════════════════════
    # Heal if critical HP and have potions
    if hp_percent < 25 and has_potions:
        return {
            "type": "item",
            "action": "D;D;A;",  # Navigate to BAG
            "reason": f"HP critical ({hp_percent:.0f}%), use Potion from Bag"
        }
    
    # Run from wild if very weak and no items
    if battle_state.battle_type == "wild" and hp_percent < 20:
        return {
            "type": "run",
            "action": "D;D;D;A;",  # Navigate to RUN
            "reason": f"HP critical ({hp_percent:.0f}%), attempting to flee"
        }
    
    # ═════════════════════════════════════════════════════════════════════════
    # PRIORITY 3: FIGHTING
    # ═════════════════════════════════════════════════════════════════════════
    best_move = None
    best_score = -1
    
    for move in battle_state.moves:
        if move["pp"] <= 0:
            continue
            
        # Base score is power
        score = move["power"]
        
        # Adjust for type effectiveness
        if move["effect"] == "damage":
            effectiveness = get_type_effectiveness(move["type"], battle_state.enemy_types)
            score *= effectiveness
        
        # Status move logic
        if move["effect"] == "status":
            # Don't use status if enemy already has status
            if battle_state.enemy_status != "OK":
                score = 0
            else:
                # High priority to status moves on healthy enemies
                if battle_state.enemy_hp_percent > 50:
                    score = 80 # Comparable to strong move
        
        if score > best_score:
            best_score = score
            best_move = move
    
    if best_move:
        # Navigate to FIGHT and select the move
        move_nav = "A;"  # Select FIGHT
        # Navigate to the move (0-indexed)
        for _ in range(best_move["index"]):
            move_nav += "D;"
        move_nav += "A;"  # Confirm move
        
        reason = f"Use {best_move['name']} "
        
        if best_move["effect"] == "damage":
            effectiveness = get_type_effectiveness(best_move["type"], battle_state.enemy_types)
            if effectiveness > 1:
                reason += "(SUPER EFFECTIVE)"
            elif effectiveness < 1:
                reason += "(NVE)"
        elif best_move["effect"] == "status":
             reason += f"(Inflict {best_move['name']})"
        
        return {
            "type": "fight",
            "action": move_nav,
            "move": best_move["name"],
            "reason": reason
        }
    
    # Fallback: Struggle or first available move
    return {
        "type": "fight",
        "action": "A;A;",
        "reason": "No optimal move/PP left, using Struggle/first move"
    }


def get_battle_context(sock, inventory: List[Dict] = None) -> Optional[str]:
    """
    Get a compact battle context string for the LLM.
    Returns None if not in battle.
    """
    battle_state = read_battle_state(sock)
    if not battle_state:
        return None
    
    action = choose_battle_action(battle_state, inventory)
    
    # Format status for display
    p_status = f"[{battle_state.player_status}]" if battle_state.player_status != "OK" else ""
    e_status = f"[{battle_state.enemy_status}]" if battle_state.enemy_status != "OK" else ""
    
    context = f"""🥊 BATTLE: {battle_state.player_pokemon}{p_status} (Lv{battle_state.player_level}, HP:{battle_state.player_hp}/{battle_state.player_max_hp}) vs {battle_state.enemy_pokemon}{e_status} (Lv{battle_state.enemy_level}, ~{battle_state.enemy_hp_percent}% HP)
RECOMMENDED: {action['reason']}
ACTION: {action.get('action', 'decide yourself')}"""
    
    return context
