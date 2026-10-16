"""
tests/test_game_loop.py - Unit tests for game controller, turn loop, and GUI move reconstruction.
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from backend.game import ScrabbleGame
from backend.lexicon import get_default_gaddag
from backend.bag import TILE_SCORES
from backend.board import Board

from PyQt6.QtWidgets import QApplication
# Ensure single QApplication instance for headless unit tests
_qapp = QApplication.instance() or QApplication([])
from frontend.board_widget import BoardWidget


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
            self.game.consecutive_passes += 1
            self.game.current_turn = "HUMAN"

        self.game.consecutive_passes = 6
        self.assertTrue(self.game._check_game_over())
        self.assertTrue(self.game.is_game_over)
        self.assertIn("6 consecutive", self.game.game_over_reason)


class TestLexiconSelection(unittest.TestCase):
    def test_lexicon_selection_naspa_vs_csw(self):
        # 1. NASPA Game: 'ZO' must be invalid
        naspa_game = ScrabbleGame(lexicon_name="NASPA", seed=42)
        naspa_game.start_game()
        naspa_game.human_player.rack.tiles = ['Z', 'O', 'A', 'B', 'C', 'D', 'E']
        success, msg = naspa_game.play_human_move("ZO", "H8", "H")
        self.assertFalse(success)
        self.assertIn("not in the dictionary", msg)

        # 2. CSW24 Game: 'ZO' and 'CH' must be valid!
        csw_game = ScrabbleGame(lexicon_name="CSW24", seed=42)
        csw_game.start_game()
        csw_game.human_player.rack.tiles = ['Z', 'O', 'A', 'B', 'C', 'D', 'E']
        success, msg = csw_game.play_human_move("ZO", "H8", "H")
        self.assertTrue(success)
        self.assertIn("You played ZO", msg)
        self.assertIn("CSW24", csw_game.lexicon_name)


class TestBoardWidgetMoveReconstruction(unittest.TestCase):
    def setUp(self):
        self.board = Board()
        self.board_widget = BoardWidget()

    def test_no_tiles_placed(self):
        move, err = self.board_widget.get_pending_move(self.board)
        self.assertIsNone(move)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("Place tiles on the board", err)

    def test_non_linear_tiles_rejected(self):
        # Place tiles across different rows and columns
        self.board_widget.record_tile_placed(7, 7, {"letter": "C", "represented_letter": "C", "rack_index": 0, "is_blank": False})
        self.board_widget.record_tile_placed(8, 8, {"letter": "A", "represented_letter": "A", "rack_index": 1, "is_blank": False})

        move, err = self.board_widget.get_pending_move(self.board)
        self.assertIsNone(move)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("single straight row or column", err)

    def test_horizontal_placement_reconstruction(self):
        # Place 'CAT' at (7, 7), (7, 8), (7, 9)
        self.board_widget.record_tile_placed(7, 7, {"letter": "C", "represented_letter": "C", "rack_index": 0, "is_blank": False})
        self.board_widget.record_tile_placed(7, 8, {"letter": "A", "represented_letter": "A", "rack_index": 1, "is_blank": False})
        self.board_widget.record_tile_placed(7, 9, {"letter": "T", "represented_letter": "T", "rack_index": 2, "is_blank": False})

        move, err = self.board_widget.get_pending_move(self.board)
        self.assertIsNone(err)
        self.assertIsNotNone(move)
        assert move is not None
        word, coord_str, direction, blank_indices = move
        self.assertEqual(word, "CAT")
        self.assertEqual(coord_str, "H8")
        self.assertEqual(direction, "H")
        self.assertEqual(blank_indices, [])

    def test_blank_tile_reconstruction(self):
        # Place 'D' as blank at (7, 7) and 'O' at (7, 8) -> 'DO'
        self.board_widget.record_tile_placed(7, 7, {"letter": "?", "represented_letter": "D", "rack_index": 0, "is_blank": True})
        self.board_widget.record_tile_placed(7, 8, {"letter": "O", "represented_letter": "O", "rack_index": 1, "is_blank": False})

        move, err = self.board_widget.get_pending_move(self.board)
        self.assertIsNone(err)
        self.assertIsNotNone(move)
        assert move is not None
        word, coord_str, direction, blank_indices = move
        self.assertEqual(word, "DO")
        self.assertEqual(coord_str, "H8")
        self.assertEqual(direction, "H")
        self.assertEqual(blank_indices, [0])

    def test_gap_in_placement_rejected(self):
        # Place at (7, 7) and (7, 9) with empty gap at (7, 8)
        self.board_widget.record_tile_placed(7, 7, {"letter": "C", "represented_letter": "C", "rack_index": 0, "is_blank": False})
        self.board_widget.record_tile_placed(7, 9, {"letter": "T", "represented_letter": "T", "rack_index": 1, "is_blank": False})

        move, err = self.board_widget.get_pending_move(self.board)
        self.assertIsNone(move)
        self.assertIsNotNone(err)
        assert err is not None
        self.assertIn("contiguous word without empty gaps", err)


if __name__ == "__main__":
    unittest.main()
