"""
Unit tests for bag.py and board.py.
"""

import unittest
from backend.bag import TileBag, Rack, TILE_SCORES, TILE_DISTRIBUTION
from backend.board import (
    Board, PlacedTile, parse_coords, format_coords,
    PREMIUM_MAP, TW, DW, TL, DL, STAR, NORMAL
)
import backend.crosscheck as crosscheck
from backend.gaddag import GADDAG


class TestTileBag(unittest.TestCase):
    def test_tile_distribution(self):
        self.assertEqual(len(TILE_DISTRIBUTION), 100)
        self.assertEqual(TILE_DISTRIBUTION.count('E'), 12)
        self.assertEqual(TILE_DISTRIBUTION.count('A'), 9)
        self.assertEqual(TILE_DISTRIBUTION.count('?'), 2)
        self.assertEqual(TILE_DISTRIBUTION.count('Z'), 1)
        self.assertEqual(TILE_DISTRIBUTION.count('Q'), 1)

    def test_drawing_tiles(self):
        bag = TileBag(seed=123)
        self.assertEqual(bag.remaining(), 100)
        drawn = bag.draw(7)
        self.assertEqual(len(drawn), 7)
        self.assertEqual(bag.remaining(), 93)

        # Draw until empty
        remaining = bag.draw(100)
        self.assertEqual(len(remaining), 93)
        self.assertEqual(bag.remaining(), 0)
        self.assertTrue(bag.is_empty())

        # Draw from empty bag
        empty_draw = bag.draw(7)
        self.assertEqual(empty_draw, [])

    def test_exchange_tiles(self):
        bag = TileBag(seed=123)
        drawn = bag.draw(7)
        exchanged = bag.exchange(drawn[:3])
        self.assertEqual(len(exchanged), 3)
        self.assertEqual(bag.remaining(), 93)

        # Exchange fails when fewer than 7 tiles remain
        bag.draw(88)  # 5 tiles left
        self.assertEqual(bag.remaining(), 5)
        with self.assertRaises(ValueError):
            bag.exchange(['A'])


class TestRack(unittest.TestCase):
    def test_rack_management(self):
        rack = Rack(['A', 'B', 'C'])
        self.assertEqual(len(rack), 3)
        rack.add(['D', 'E'])
        self.assertEqual(len(rack), 5)

        rack.remove(['B', 'D'])
        self.assertEqual(sorted(rack.tiles), ['A', 'C', 'E'])

        with self.assertRaises(ValueError):
            rack.remove(['Z'])

    def test_has_tiles_with_and_without_blanks(self):
        rack = Rack(['C', 'A', 'T', 'S', '?'])
        self.assertTrue(rack.has_tiles(['C', 'A', 'T']))
        self.assertTrue(rack.has_tiles(['C', 'A', 'T', 'S']))
        # Using blank for 'Z'
        self.assertTrue(rack.has_tiles(['C', 'A', 'T', 'Z']))
        # Not enough tiles (needs 2 missing letters but only 1 blank)
        self.assertFalse(rack.has_tiles(['C', 'A', 'T', 'X', 'Y']))

    def test_rack_display(self):
        rack = Rack(['A', 'Z'])
        disp_plain = rack.display(color=False)
        self.assertIn("A:1", disp_plain)
        self.assertIn("Z:10", disp_plain)


class TestBoardCoordinates(unittest.TestCase):
    def test_parse_coords(self):
        self.assertEqual(parse_coords("H8"), (7, 7))
        self.assertEqual(parse_coords("8H"), (7, 7))
        self.assertEqual(parse_coords("A1"), (0, 0))
        self.assertEqual(parse_coords("O15"), (14, 14))
        self.assertEqual(parse_coords("15O"), (14, 14))

        with self.assertRaises(ValueError):
            parse_coords("P1")  # Col P out of bounds
        with self.assertRaises(ValueError):
            parse_coords("A16")  # Row 16 out of bounds
        with self.assertRaises(ValueError):
            parse_coords("")

    def test_format_coords(self):
        self.assertEqual(format_coords(7, 7), "H8")
        self.assertEqual(format_coords(0, 0), "A1")
        self.assertEqual(format_coords(14, 14), "O15")


class TestBoardLayout(unittest.TestCase):
    def test_premium_squares(self):
        self.assertEqual(PREMIUM_MAP[0][0], TW)
        self.assertEqual(PREMIUM_MAP[7][7], STAR)
        self.assertEqual(PREMIUM_MAP[1][1], DW)
        self.assertEqual(PREMIUM_MAP[1][5], TL)
        self.assertEqual(PREMIUM_MAP[0][3], DL)
        self.assertEqual(PREMIUM_MAP[0][1], NORMAL)


class TestBoardValidationAndScoring(unittest.TestCase):
    def setUp(self):
        self.board = Board()

    def test_first_move_rules(self):
        # Must cover H8 (7, 7)
        valid, reason, needed = self.board.is_valid_placement("CAT", 0, 0, "H")
        self.assertFalse(valid)
        self.assertIn("center star", reason)

        # Must be at least 2 letters
        valid, reason, needed = self.board.is_valid_placement("A", 7, 7, "H")
        self.assertFalse(valid)

        # Valid first move through H8
        valid, reason, needed = self.board.is_valid_placement("HORN", 7, 4, "H")
        self.assertTrue(valid)
        self.assertEqual(needed, ['H', 'O', 'R', 'N'])

    def test_opening_move_scoring(self):
        # Place "HORN" horizontally at H8: row 7, col 4 to 7
        # H=4, O=1, R=1, N=1 -> Sum = 7.
        # Center square (7, 7) has STAR which acts as Double Word (2x).
        # Score = 7 * 2 = 14 points.
        score, words = self.board.place_move("HORN", 7, 4, "H")
        self.assertEqual(score, 14)
        self.assertEqual(words, ["HORN"])
        self.assertFalse(self.board.is_first_move())

    def test_subsequent_move_connection_rules(self):
        # Place opening word "HORN" at (7, 4)-(7, 7)
        self.board.place_move("HORN", 7, 4, "H")

        # Disconnected move should fail
        valid, reason, needed = self.board.is_valid_placement("CAT", 0, 0, "H")
        self.assertFalse(valid)
        self.assertIn("connect", reason)

        # Overlapping move: "FARM" vertically through 'R' at (7, 6)
        # F at (5, 6), A at (6, 6), R at (7, 6), M at (8, 6)
        valid, reason, needed = self.board.is_valid_placement("FARM", 5, 6, "V")
        self.assertTrue(valid)
        self.assertEqual(needed, ['F', 'A', 'M'])

        # Conflicting letter at existing tile
        valid, reason, needed = self.board.is_valid_placement("FISH", 7, 4, "H")
        self.assertFalse(valid)
        self.assertIn("conflicts", reason)

    def test_cross_word_scoring(self):
        # Place "CAT" at (7, 6)-(7, 8)
        # (7, 6)=C, (7, 7)=A, (7, 8)=T
        self.board.place_move("CAT", 7, 6, "H")

        # Place "DO" vertically at (6, 8)-(7, 8)
        # (6, 8)=D (newly placed), (7, 8)=T (existing). Forms "DT"? Not a real word, but let's test "AT" -> "TO":
        # Let's place "TO" at (7, 8)-(8, 8):
        # (7, 8)=T (existing), (8, 8)=O (new).
        # (8, 8) is Double Letter (DL).
        # Main word: "TO". T=1 (no DL since already existing), O=1 (newly placed on DL -> 1*2=2).
        # Main word total = 1 + 2 = 3.
        # Now suppose adjacent to (8, 8) there was 'N' at (8, 7) forming cross-word "NO":
        # Let's first put 'N' at (8, 7)
        self.board.place_move("NO", 8, 7, "H")
        # Existing: (8, 7)=N, (8, 8)=O.
        # Check board indexing
        self.assertEqual(self.board[8][7], 'N')
        self.assertEqual(self.board[8][8], 'O')

    def test_bingo_scoring(self):
        # Opening move playing all 7 tiles: "PLAYERS" at (7, 1)-(7, 7)
        # All 7 letters newly placed from rack -> +50 Bingo bonus!
        score, words = self.board.score_move("PLAYERS", 7, 1, "H")
        # Letters: P=3, L=1, A=1, Y=4, E=1, R=1, S=1.
        # (7, 3) is DL -> A(1)*2 = 2.
        # (7, 7) is STAR (DW) -> 2x word multiplier.
        # Sum = 3 + 1 + 2 + 4 + 1 + 1 + 1 = 13.
        # Word score = 13 * 2 = 26.
        # Bingo bonus = 50. Total = 76.
        self.assertEqual(score, 76)

    def test_blank_tile_scoring(self):
        # Play "CAT" where 'A' is a blank tile (index 1)
        # C=3, A=0, T=1. Center (7, 7) has 'A' (blank).
        # Sum = (3 + 0 + 1) * 2 (DW) = 8.
        score, words = self.board.score_move("CAT", 7, 6, "H", blank_indices=[1])
        self.assertEqual(score, 8)

        # Commit placement and verify tile object
        self.board.place_move("CAT", 7, 6, "H", blank_indices=[1])
        blank_tile = self.board.get_tile(7, 7)
        self.assertIsNotNone(blank_tile)
        assert blank_tile is not None
        self.assertTrue(blank_tile.is_blank)
        self.assertEqual(blank_tile.score, 0)
        self.assertEqual(blank_tile.letter, 'A')

    def test_board_crosscheck_compatibility(self):
        # Verify crosscheck.py can read our Board object directly!
        self.board.place_move("CAT", 7, 6, "H")
        # board[7][6] should be 'C'
        self.assertEqual(self.board[7][6], 'C')
        self.assertIsNone(self.board[0][0])

        # Test calculate_cross_checks with GADDAG
        dag = GADDAG()
        dag.add_word("CATS")
        dag.add_word("AT")
        checks = crosscheck.calculate_cross_checks(self.board, dag)
        self.assertIn((6, 6), checks)
        self.assertIsInstance(checks[(6, 6)], set)

    def test_board_render(self):
        self.board.place_move("CAT", 7, 6, "H")
        rendered = self.board.render(color=False)
        self.assertIn("H8", [format_coords(7, 7)])
        self.assertIn("C", rendered)
        self.assertIn("A", rendered)
        self.assertIn("T", rendered)
        self.assertIn("15", rendered)

        lines = rendered.splitlines()
        col_header = lines[0]
        # Verify each column letter A-O is centered above its 4-char wide column
        for c in range(15):
            letter = chr(ord('A') + c)
            letter_idx = col_header.index(letter)
            expected_center = 5 + c * 4
            self.assertEqual(letter_idx, expected_center, f"Letter {letter} misaligned")


if __name__ == "__main__":
    unittest.main()

