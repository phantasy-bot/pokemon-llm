
import os
import re
import logging

log = logging.getLogger(__name__)

# Path to the hints file
HINTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs', 'game_hints.md')

def load_hints_map():
    """
    Parses the docs/game_hints.md file and builds a mapping of sections to content.
    This is a simple parser that splits by Headers.
    """
    if not os.path.exists(HINTS_FILE):
        log.warning(f"Hints file not found at {HINTS_FILE}")
        return {}

    hints = {}
    current_section = None
    buffer = []

    try:
        with open(HINTS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                # Detect headers like "## 📍 PALLET TOWN & ROUTE 1"
                match = re.match(r'^##\s+(.*)', line)
                if match:
                    # Save previous section
                    if current_section and buffer:
                        hints[current_section] = "".join(buffer).strip()
                    
                    # Start new section
                    current_section = match.group(1).strip()
                    # Remove emojis for cleaner keys if needed, but let's keep it simple for now
                    # normalized_key = re.sub(r'[^\w\s]', '', current_section).strip().upper()
                    buffer = []
                elif current_section:
                    buffer.append(line)
            
            # Save last section
            if current_section and buffer:
                hints[current_section] = "".join(buffer).strip()
                
    except Exception as e:
        log.error(f"Error parsing hints file: {e}")

    return hints

# Cache the hints in memory
_HINTS_CACHE = load_hints_map()

def get_area_hint(gamestate: dict) -> str:
    """
    Determines the most relevant hint based on the current gamestate.
    
    Args:
        gamestate: The dictionary returned by state.prep_llm(), containing
                   map_name, map_id, inventory, event_flags, etc.
                   
    Returns:
        A string containing the relevant hint section, or None if no specific hint applies.
    """
    if not gamestate:
        return None
        
    map_name = (gamestate.get('map_name') or '').upper()
    inventory = gamestate.get('inventory', [])
    flags = gamestate.get('event_flags', {})
    
    # Helper to check for item
    def has_item(name_part):
        return any(name_part.lower() in item.get('name', '').lower() for item in inventory)

    inventory_names = [i.get('name', '') for i in inventory]

    # ════════════════════════════════════════════════════════════════════════
    # HINT SELECTION LOGIC
    # ════════════════════════════════════════════════════════════════════════
    
    # default fallback
    matching_section_key = None
    
    # 1. PALLET TOWN & ROUTE 1 (including Player's House)
    if "PALLET" in map_name or "REDS_HOUSE" in map_name or "OAKS_LAB" in map_name or "PLAYERS_HOUSE" in map_name:
        # Specific navigation help for leaving Pallet Town
        if map_name == "PALLET_TOWN" and not has_item("POKEDEX") and not has_item("PARCEL"):
             return "🚪 ROUTE 1 EXIT: Walk to [10,1] or [11,1] (north edge) to trigger Oak scene and access Route 1."

        # Check if we have Pokedex
        if has_item("POKEDEX"):
            # If we have Pokedex, we are done with initial quest, likely heading to Viridian or Route 1
            matching_section_key = "PALLET TOWN & ROUTE 1" 
        elif has_item("PARCEL"):
            matching_section_key = "BACK TO PALLET (Delivering Parcel)"
        else:
            # Determining if we are Pre-Parcel or Post-Parcel?
            # If we don't have Pokedex and don't have Parcel, we need to go get it.
            # Unless we already delivered it? No flags for that easily available yet.
            # Assuming standard flow: Start -> Parcel -> Pokedex.
            matching_section_key = "PALLET TOWN & ROUTE 1"
            
    elif "ROUTE_1" in map_name:
         matching_section_key = "PALLET TOWN & ROUTE 1"

    # 2. VIRIDIAN CITY & FOREST
    elif "VIRIDIAN" in map_name:
        if "FOREST" in map_name:
            matching_section_key = "PEWTER CITY & MT MOON" # Forest leads to Pewter
        else:
            # In Viridian City
            if has_item("POKEDEX"):
                # Done with parcel quest, heading to forest/gym
                # Actually, Viridian Gym is closed. Heading North.
                matching_section_key = "PEWTER CITY & MT MOON"
            elif has_item("PARCEL"):
                # Have parcel, need to go back
                matching_section_key = "VIRIDIAN CITY (The Parcel Quest)" 
            else:
                # Need to get parcel
                matching_section_key = "VIRIDIAN CITY (The Parcel Quest)"

    # 3. PEWTER CITY & MT MOON
    elif "PEWTER" in map_name or "ROUTE_3" in map_name:
        matching_section_key = "PEWTER CITY & MT MOON"
        
    elif "MT_MOON" in map_name:
        matching_section_key = "PEWTER CITY & MT MOON"

    # 4. ROUTE 4 & CERULEAN
    elif "ROUTE_4" in map_name:
        matching_section_key = "ROUTE 4 & CERULEAN"
        
    elif "CERULEAN" in map_name or "ROUTE_24" in map_name or "ROUTE_25" in map_name or "BILLS" in map_name:
        matching_section_key = "ROUTE 4 & CERULEAN"
        
    elif "ROUTE_5" in map_name:
        matching_section_key = "ROUTE 4 & CERULEAN" # Bottom part leads to vermillion

    # 5. VERMILLION CITY
    elif "VERMILION" in map_name or "SS_ANNE" in map_name or "ROUTE_6" in map_name or "ROUTE_11" in map_name:
        matching_section_key = "VERMILLION CITY (SS Anne)"

    # 6. ROCK TUNNEL / LAVENDER
    elif "ROUTE_9" in map_name or "ROUTE_10" in map_name or "ROCK_TUNNEL" in map_name:
        matching_section_key = "ROCK TUNNEL & LAVENDER TOWN"
        
    elif "LAVENDER" in map_name or "POKEMON_TOWER" in map_name or "ROUTE_8" in map_name or "ROUTE_7" in map_name:
        # Route 7/8/Lavender usually grouped together here
        matching_section_key = "ROCK TUNNEL & LAVENDER TOWN"

    # 7. CELADON CITY
    elif "CELADON" in map_name or "GAME_CORNER" in map_name or "ROCKET_HIDEOUT" in map_name:
        matching_section_key = "CELADON CITY (The Big City)"

    # 8. SAFFRON CITY / SILPH CO
    elif "SAFFRON" in map_name or "SILPH_CO" in map_name:
        matching_section_key = "SAFFRON CITY (Silph Co)"

    # 9. FUCHSIA CITY / SAFARI
    elif "FUCHSIA" in map_name or "SAFARI" in map_name or "ROUTE_17" in map_name or "ROUTE_18" in map_name or "ROUTE_12" in map_name or "ROUTE_13" in map_name or "ROUTE_14" in map_name or "ROUTE_15" in map_name: 
        matching_section_key = "FUCHSIA CITY (Safari & Koga)"

    # 10. CINNABAR
    elif "CINNABAR" in map_name or "MANSION" in map_name or "ROUTE_19" in map_name or "ROUTE_20" in map_name or "ROUTE_21" in map_name:
        matching_section_key = "CINNABAR ISLAND"
        
    # 11. VICTORY ROAD / INDIGO
    elif "ROUTE_22" in map_name or "ROUTE_23" in map_name or "VICTORY_ROAD" in map_name or "INDIGO" in map_name or "CHAMPION" in map_name or "LORELEI" in map_name or "BRUNO" in map_name or "AGATHA" in map_name or "LANCE" in map_name:
        matching_section_key = "VICTORY ROAD" if "VICTORY" in map_name or "ROUTE" in map_name else "INDIGO PLATEAU (Elite Four)"
        
    
    # ════════════════════════════════════════════════════════════════════════
    # RETRIEVE CONTENT
    # ════════════════════════════════════════════════════════════════════════
    
    if matching_section_key:
        # Try exact match first
        full_key_match = None
        for key in _HINTS_CACHE.keys():
            if matching_section_key in key:
                full_key_match = key
                break
        
        if full_key_match:
            return _HINTS_CACHE.get(full_key_match)
            
    return None

