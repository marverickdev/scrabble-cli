"""
tests/test_movegen.py - Unit tests for lexicon.py and movegen.py.
"""

import unittest
import time
from board import Board
from bag import Rack, TILE_DISTRIBUTION
from lexicon import load_dictionary, get_default_gaddag, get_dictionary_words
from movegen import generate_all_moves, ScrabbleMove
from montecarlo import get_best_move_monte_carlo, SimState


class TestLexicon(unittest.TestCase):
    def setUp(self):
        self.dag = get_default_gaddag()

    def test_lexicon_membership(self):
        self.assertTrue(self.dag.is_valid_word("QI"))
        self.assertTrue(self.dag.is_valid_word("ZA"))
        self.assertTrue(self.dag.is_valid_word("CAT"))
        self.assertTrue(self.dag.is_valid_word("SCRABBLE"))
        self.assertTrue(self.dag.is_valid_word("ZYZZYVA"))

        self.assertFalse(self.dag.is_valid_word("QIX"))
        self.assertFalse(self.dag.is_valid_word("ABCDEFG"))
        self.assertFalse(self.dag.is_valid_word(""))

    def test_word_set_lookup(self):
        words = get_dictionary_words()
        self.assertIn("QI", words)
        self.assertIn("SCRABBLE", words)
        self.assertNotIn("QIX", words)

    def test_missing_file_error(self):
        with self.assertRaises(FileNotFoundError):
            load_dictionary("data/nonexistent_dictionary.txt")


class TestMoveGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dag = get_default_gaddag()

    def test_opening_move_generation(self):
        board = Board()
        rack = ['C', 'A', 'T', 'S', 'E', 'R', 'D']

        moves = generate_all_moves(board, rack, self.dag, top_n=20)
        self.assertGreater(len(moves), 0)

        # Every opening move must cover the center star (7, 7)
        for m in moves:
            if m.direction == "H":
                self.assertEqual(m.row, 7)
                self.assertTrue(m.col <= 7 <= m.col + len(m.word) - 1)
            else:
                self.assertEqual(m.col, 7)
                self.assertTrue(m.row <= 7 <= m.row + len(m.word) - 1)

            # Check that word is a valid dictionary word
            self.assertTrue(self.dag.is_valid_word(m.word))

        # Check that top moves include bingo plays (e.g. SCARTED or REDACTS for 70+ points)
        top_move = moves[0]
        self.assertGreaterEqual(top_move.score, 70)

    def test_subsequent_moves_hooking(self):
        board = Board()
        board.place_move("HORN", 7, 4, "H")

        # Rack with 'S' to hook "HORN" -> "HORNS"
        rack = ['S', 'A', 'T']
        moves = generate_all_moves(board, rack, self.dag)

        # Should generate "HORNS"
        horns_moves = [m for m in moves if m.word == "HORNS"]
        self.assertGreater(len(horns_moves), 0)
        horn_move = horns_moves[0]
        self.assertEqual(horn_move.row, 7)
        self.assertEqual(horn_move.col, 4)
        self.assertEqual(horn_move.direction, "H")
        self.assertEqual(horn_move.tiles_played, ['S'])

    def test_blank_tile_wildcard_generation(self):
        board = Board()
        rack = ['C', 'A', 'T', '?']

        moves = generate_all_moves(board, rack, self.dag)
        blank_moves = [m for m in moves if len(m.blank_indices) > 0]
        self.assertGreater(len(blank_moves), 0)

        # Check sample blank move
        sample = blank_moves[0]
        self.assertIn('?', sample.tiles_played)
        self.assertTrue(self.dag.is_valid_word(sample.word))

    def test_cross_word_formation(self):
        board = Board()
        board.place_move("CAT", 7, 6, "H")

        # Play 'O' at (6, 5) and 'N' at (7, 5) -> "ON" vertically, where 'O' is adjacent to 'C'?
        # Let's test a move that forms cross words
        rack = ['A', 'R', 'T']
        moves = generate_all_moves(board, rack, self.dag)

        # Check that moves_formed includes more than 1 word for cross-word plays
        multi_word_moves = [m for m in moves if len(m.words_formed) > 1]
        self.assertGreater(len(multi_word_moves), 0)

    def test_montecarlo_compatibility(self):
        board = Board()
        rack = ['C', 'A', 'T', 'S', 'E', 'R', 'D']

        candidates = generate_all_moves(board, rack, self.dag, top_n=10)
        state = SimState()
        best_move, ev = get_best_move_monte_carlo(
            candidates, state, rack, TILE_DISTRIBUTION, iterations=30
        )
        self.assertIsNotNone(best_move)
        assert best_move is not None
        self.assertIsInstance(best_move, ScrabbleMove)
        self.assertGreater(best_move.score, 0)

    def test_move_generation_performance(self):
        board = Board()
        board.place_move("SCARTED", 7, 2, "H")
        rack = ['P', 'I', 'N', 'K', 'E', 'R', 'T']

        t0 = time.time()
        moves = generate_all_moves(board, rack, self.dag)
        elapsed = time.time() - t0

        print(f"\nGenerated {len(moves)} legal moves in {elapsed:.3f}s")
        # Ensure generation runs in well under 0.25 seconds
        self.assertLess(elapsed, 0.25)
        self.assertGreater(len(moves), 0)


if __name__ == "__main__":
    unittest.main()

