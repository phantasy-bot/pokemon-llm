import unittest
from unittest.mock import MagicMock
from core.battle_strategy import choose_battle_action, BattleState, MOVES

class TestBattleStrategy(unittest.TestCase):
    def setUp(self):
        # Base setup for a generic battle state
        self.base_state = BattleState(
            in_battle=True,
            battle_type="wild",
            player_pokemon="Pikachu",
            player_hp=50,
            player_max_hp=100,
            player_level=10,
            player_types=("Electric", None),
            player_status="OK",
            enemy_pokemon="Pidgety",
            enemy_hp_percent=100,
            enemy_types=("Normal", "Flying"),
            enemy_level=8,
            enemy_status="OK",
            moves=[
                {"index": 0, "name": "Thundershock", "power": 40, "type": "Electric", "pp": 30, "max_pp": 30, "effect": "damage"},
                {"index": 1, "name": "Growl", "power": 0, "type": "Normal", "pp": 40, "max_pp": 40, "effect": "stat"},
            ],
            cursor_position=0
        )

    def test_catch_wild_low_hp(self):
        """Should use Pokeball if wild and low HP"""
        state = self.base_state
        state.battle_type = "wild"
        state.enemy_hp_percent = 20 # Low HP
        
        inventory = [{"name": "POKE BALL", "count": 5}]
        action = choose_battle_action(state, inventory)
        
        self.assertEqual(action["type"], "catch")
        self.assertEqual(action["item"], "POKE BALL")

    def test_catch_wild_statused(self):
        """Should use Pokeball if wild, statused, and moderately low HP"""
        state = self.base_state
        state.battle_type = "wild"
        state.enemy_hp_percent = 40 # Moderate HP 
        state.enemy_status = "SLP"
        
        inventory = [{"name": "POKE BALL", "count": 5}]
        action = choose_battle_action(state, inventory)
        
        self.assertEqual(action["type"], "catch")

    def test_dont_catch_trainer(self):
        """Should NOT catch trainer pokemon"""
        state = self.base_state
        state.battle_type = "trainer"
        state.enemy_hp_percent = 10
        
        inventory = [{"name": "POKE BALL", "count": 5}]
        action = choose_battle_action(state, inventory)
        
        self.assertNotEqual(action["type"], "catch")
        self.assertEqual(action["type"], "fight")

    def test_type_effectiveness(self):
        """Should choose super effective move"""
        state = self.base_state
        # Electric vs Water (Super effective)
        state.enemy_types = ("Water", None)
        state.moves = [
             {"index": 0, "name": "Tackle", "power": 40, "type": "Normal", "pp": 30, "effect": "damage"},
             {"index": 1, "name": "Thundershock", "power": 40, "type": "Electric", "pp": 30, "effect": "damage"},
        ]
        
        action = choose_battle_action(state)
        # Electric (40 * 2 = 80) should beat Normal (40 * 1 = 40)
        self.assertEqual(action["move"], "Thundershock")
        self.assertIn("SUPER EFFECTIVE", action["reason"])

    def test_heal_priority(self):
        """Should priority heal when critical"""
        state = self.base_state
        state.player_hp = 10 # 10% HP
        state.player_max_hp = 100
        
        inventory = [{"name": "POTION", "count": 1}]
        action = choose_battle_action(state, inventory)
        
        self.assertEqual(action["type"], "item")
        self.assertIn("HP critical", action["reason"])

    def test_no_double_status(self):
        """Should not use Sleep Powder if enemy already sleeping"""
        state = self.base_state
        state.enemy_status = "SLP"
        state.moves = [
            {"index": 0, "name": "Sleep Powder", "power": 0, "type": "Grass", "pp": 15, "effect": "status"},
            {"index": 1, "name": "Tackle", "power": 35, "type": "Normal", "pp": 35, "effect": "damage"},
        ]
        
        action = choose_battle_action(state)
        # Should choose Tackle because Sleep Powder score is 0 on sleeping enemy
        self.assertEqual(action["move"], "Tackle")

if __name__ == '__main__':
    unittest.main()
