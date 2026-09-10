"""
tests/test_game_loop.py - Unit tests for game controller, turn loop, and frontend input parsing.
"""

import unittest
from backend.game import ScrabbleGame
from backend.lexicon import get_default_gaddag
from backend.bag import TILE_SCORES
from frontend.input_handler import InputHandler
from frontend.cli_renderer import CLIRenderer


class TestGameController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dag = get_default_gaddag()

    def setUp(self):
        self.game = ScrabbleGame(gaddag=self.dag, seed=42)
        self.game.start_game()

    def test_game_initialization(self):
        self.assertEqual(len(self.game.human_player.rack), 7)
        self.assertEqual(len(self.game.ai_player.rack), 7)
        self.assertEqual(len(self.game.bag), 86)
        self.assertEqual(self.game.current_turn, "HUMAN")
        self.assertEqual(self.game.human_player.score, 0)
        self.assertEqual(self.game.ai_player.score, 0)
        self.assertFalse(self.game.is_game_over)

    def test_human_move_success_and_turn_advance(self):
        # Force a known rack for repeatable testing
        self.game.human_player.rack.tiles = ['C', 'A', 'T', 'S', 'E', 'R', 'D']
        success, msg = self.game.play_human_move("CAT", "H8", "H")

        self.assertTrue(success)
        self.assertIn("You played CAT", msg)
        self.assertGreater(self.game.human_player.score, 0)
        # Rack should be refilled back to 7
        self.assertEqual(len(self.game.human_player.rack), 7)
        # Turn should advance to AI
        self.assertEqual(self.game.current_turn, "AI")

    def test_human_move_missing_tiles(self):
        self.game.human_player.rack.tiles = ['A', 'B', 'C']
        success, msg = self.game.play_human_move("ZOOM", "H8", "H")
        self.assertFalse(success)
        self.assertIn("do not have the required tiles", msg)
        self.assertEqual(self.game.current_turn, "HUMAN")

    def test_human_move_invalid_dictionary_word(self):
        self.game.human_player.rack.tiles = ['X', 'Y', 'Z', 'Z', 'Y', 'A', 'B']
        success, msg = self.game.play_human_move("XYZ", "H8", "H")
        self.assertFalse(success)
        self.assertIn("not in the dictionary", msg)

    def test_human_move_blank_tile(self):
        # Rack has blank '?' and 'A', 'T'
        self.game.human_player.rack.tiles = ['?', 'A', 'T', 'E', 'R', 'S', 'D']
        # Play 'CAT' where 'C' is played as a blank (blank_indices=[0])
        success, msg = self.game.play_human_move("CAT", "H8", "H", blank_indices=[0])
        self.assertTrue(success)
        # Verify '?' was removed from rack
        self.assertNotIn('?', self.game.human_player.rack.tiles[:4])

    def test_ai_turn_execution(self):
        # Human plays first move
        self.game.human_player.rack.tiles = ['C', 'A', 'T', 'S', 'E', 'R', 'D']
        self.game.play_human_move("CAT", "H8", "H")
        self.assertEqual(self.game.current_turn, "AI")

        # Give AI playable tiles
        self.game.ai_player.rack.tiles = ['S', 'P', 'I', 'N', 'E', 'R', 'T']
        ai_success, ai_msg = self.game.play_ai_turn()

        self.assertTrue(ai_success)
        self.assertGreater(self.game.ai_player.score, 0)
        self.assertEqual(self.game.current_turn, "HUMAN")
        self.assertEqual(len(self.game.ai_player.rack), 7)

    def test_pass_turn(self):
        self.assertEqual(self.game.consecutive_passes, 0)
        success, msg = self.game.pass_human_turn()
        self.assertTrue(success)
        self.assertEqual(self.game.consecutive_passes, 1)
        self.assertEqual(self.game.current_turn, "AI")

    def test_exchange_tiles(self):
        self.game.human_player.rack.tiles = ['Q', 'Z', 'A', 'B', 'C', 'D', 'E']
        success, msg = self.game.exchange_human_tiles(['Q', 'Z'])
        self.assertTrue(success)
        self.assertIn("exchanged 2 tiles", msg)
        self.assertEqual(len(self.game.human_player.rack), 7)
        self.assertEqual(self.game.consecutive_passes, 1)
        self.assertEqual(self.game.current_turn, "AI")

    def test_six_consecutive_passes_ends_game(self):
        # Simulate 6 passes
        for _ in range(3):
            self.game.pass_human_turn()
            # Force AI to pass by giving it an empty rack and bag
            self.game.consecutive_passes += 1
            self.game.current_turn = "HUMAN"

        self.game.consecutive_passes = 6
        self.assertTrue(self.game._check_game_over())
        self.assertTrue(self.game.is_game_over)
        self.assertIn("6 consecutive", self.game.game_over_reason)


class TestFrontendInputAndRenderer(unittest.TestCase):
    def test_input_handler_parsing(self):
        p1 = InputHandler.parse_command("play CAT H8 H")
        self.assertEqual(p1["action"], "play")
        self.assertEqual(p1["word"], "CAT")
        self.assertEqual(p1["coord"], "H8")
        self.assertEqual(p1["direction"], "H")
        self.assertEqual(p1["blanks"], [])

        # Lowercase indicates blank tile
        p2 = InputHandler.parse_command("play cAT H8 V")
        self.assertEqual(p2["action"], "play")
        self.assertEqual(p2["word"], "CAT")
        self.assertEqual(p2["blanks"], [0])

        p3 = InputHandler.parse_command("exchange QZ")
        self.assertEqual(p3["action"], "exchange")
        self.assertEqual(p3["tiles"], ["Q", "Z"])

        p4 = InputHandler.parse_command("pass")
        self.assertEqual(p4["action"], "pass")

        p5 = InputHandler.parse_command("quit")
        self.assertEqual(p5["action"], "quit")

    def test_renderer_output(self):
        game = ScrabbleGame(seed=42)
        game.start_game()
        renderer = CLIRenderer(use_color=False)

        screen = renderer.render_screen(game)
        self.assertIn("YOUR RACK", screen)
        self.assertIn("COMPUTER", screen)

        help_txt = renderer.render_help()
        self.assertIn("COMMANDS GUIDE", help_txt)


if __name__ == "__main__":
    unittest.main()
