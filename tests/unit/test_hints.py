
import sys
import os
import unittest

# Add repo root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyAIAgent.game.hints import get_area_hint

class TestAreaHints(unittest.TestCase):
    
    def test_pallet_town_initial(self):
        state = {
            'map_name': 'PALLET_TOWN',
            'inventory': [],
            'event_flags': {}
        }
        hint = get_area_hint(state)
        print(f"Pallet Initial Hint: {hint[:50]}...")
        self.assertIn("Player's House", hint)
        self.assertIn("Oak", hint)

    def test_viridian_parcel_quest(self):
        state = {
            'map_name': 'VIRIDIAN_CITY',
            'inventory': [], # No parcel, no pokedex
            'event_flags': {}
        }
        hint = get_area_hint(state)
        print(f"Viridian Hint: {hint[:50]}...")
        self.assertIn("Parcel", hint)
        self.assertIn("Pokemart", hint)

    def test_mt_moon(self):
        state = {
            'map_name': 'MT_MOON_1F',
            'inventory': [{'name': 'POKEDEX'}],
            'event_flags': {}
        }
        hint = get_area_hint(state)
        print(f"Mt Moon Hint: {hint[:50]}...")
        self.assertIn("Fossil", hint)
        self.assertIn("Exit", hint)

    def test_ss_anne(self):
        state = {
            'map_name': 'SS_ANNE_1F',
            'inventory': [{'name': 'SS_TICKET'}], 
            'event_flags': {}
        }
        hint = get_area_hint(state)
        print(f"SS Anne Hint: {hint[:50]}...")
        self.assertIn("Captain", hint)
        self.assertIn("Rub his back", hint)
    
    def test_victory_road(self):
        state = {
            'map_name': 'VICTORY_ROAD_3F',
            'inventory': [], 
            'event_flags': {}
        }
        hint = get_area_hint(state)
        print(f"Victory Road Hint: {hint[:50]}...")
        # Check that it falls into VICTORY ROAD section, not just Elite Four list
        self.assertIn("Strength", hint)

if __name__ == '__main__':
    unittest.main()
