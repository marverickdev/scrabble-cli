"""
board.py - Scrabble Board representation, premium square map,
move validation, and complete Scrabble scoring engine.
"""

from typing import List, Tuple, Optional, Dict, Any
from backend.bag import TILE_SCORES

# Premium Square Constants
NORMAL = ".."
DL = "2L"  # Double Letter
TL = "3L"  # Triple Letter
DW = "2W"  # Double Word
TW = "3W"  # Triple Word
STAR = "★ "  # Center Star (Double Word on first move)

# Standard 15x15 Scrabble Premium Squares Layout
PREMIUM_MAP: List[List[str]] = [[NORMAL] * 15 for _ in range(15)]

# Triple Word Squares
for r, c in [
    (0, 0), (0, 7), (0, 14),
    (7, 0),         (7, 14),
    (14, 0), (14, 7), (14, 14)
]:
    PREMIUM_MAP[r][c] = TW

# Double Word Squares
for r, c in [
    (1, 1), (2, 2), (3, 3), (4, 4),
    (1, 13), (2, 12), (3, 11), (4, 10),
    (13, 1), (12, 2), (11, 3), (10, 4),
    (13, 13), (12, 12), (11, 11), (10, 10)
]:
    PREMIUM_MAP[r][c] = DW

# Triple Letter Squares
for r, c in [
    (1, 5), (1, 9),
    (5, 1), (5, 5), (5, 9), (5, 13),
    (9, 1), (9, 5), (9, 9), (9, 13),
    (13, 5), (13, 9)
]:
    PREMIUM_MAP[r][c] = TL

# Double Letter Squares
for r, c in [
    (0, 3), (0, 11),
    (2, 6), (2, 8),
    (3, 0), (3, 7), (3, 14),
    (6, 2), (6, 6), (6, 8), (6, 12),
    (7, 3), (7, 11),
    (8, 2), (8, 6), (8, 8), (8, 12),
    (11, 0), (11, 7), (11, 14),
    (12, 6), (12, 8),
    (14, 3), (14, 11)
]:
    PREMIUM_MAP[r][c] = DL

# Center Star
PREMIUM_MAP[7][7] = STAR


def parse_coords(coord_str: str) -> Tuple[int, int]:
    """
    Parses coordinate string like 'H8', '8H', 'A1', '15O' into (row, col) indices (0-14).
    Columns: A-O -> 0-14
    Rows: 1-15 -> 0-14
    """
    s = coord_str.strip().upper()
    if not s:
        raise ValueError("Empty coordinate string.")

    col_char = None
    row_str = ""
    for ch in s:
        if ch.isalpha():
            if col_char is not None:
                raise ValueError(f"Invalid coordinate: '{coord_str}'")
            col_char = ch
        elif ch.isdigit():
            row_str += ch
        else:
            raise ValueError(f"Invalid character in coordinate: '{ch}'")

    if col_char is None or not row_str:
        raise ValueError(f"Invalid coordinate format: '{coord_str}'. Expected e.g. 'H8'.")

    col = ord(col_char) - ord('A')
    row = int(row_str) - 1

    if not (0 <= row < 15 and 0 <= col < 15):
        raise ValueError(f"Coordinate '{coord_str}' is out of bounds (1-15, A-O).")

    return row, col


def format_coords(row: int, col: int) -> str:
    """Formats (row, col) as standard coordinate string, e.g. (7, 7) -> 'H8'."""
    col_char = chr(ord('A') + col)
    row_num = row + 1
    return f"{col_char}{row_num}"


class PlacedTile:
    """
    Represents a tile currently placed on the board.
    Tracks whether it was placed as a blank ('?') so it scores 0 points.
    """
    __slots__ = ['letter', 'is_blank', 'score']

    def __init__(self, letter: str, is_blank: bool = False):
        self.letter = letter.upper()
        self.is_blank = is_blank
        self.score = 0 if is_blank else TILE_SCORES.get(self.letter, 0)

    def __str__(self) -> str:
        return self.letter

    def __repr__(self) -> str:
        return f"PlacedTile('{self.letter}', is_blank={self.is_blank})"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PlacedTile):
            return self.letter == other.letter and self.is_blank == other.is_blank
        if isinstance(other, str):
            return self.letter == other.upper()
        return False


class BoardRowProxy:
    """
    Proxy allowing 2D list-like indexing `board[row][col]`.
    Returns letter string (e.g. 'A') or None, for direct compatibility with crosscheck.py.
    """
    def __init__(self, row_tiles: List[Optional[PlacedTile]]):
        self._tiles = row_tiles

    def __getitem__(self, col: int) -> Optional[str]:
        tile = self._tiles[col]
        return tile.letter if tile is not None else None

    def __len__(self) -> int:
        return len(self._tiles)

    def __iter__(self):
        for tile in self._tiles:
            yield tile.letter if tile is not None else None


class Board:
    """
    15x15 Scrabble Board.
    Maintains tile grid, move validation, cross-word detection, and scoring engine.
    """
    def __init__(self):
        self.grid: List[List[Optional[PlacedTile]]] = [
            [None for _ in range(15)] for _ in range(15)
        ]

    def __getitem__(self, row: int) -> BoardRowProxy:
        """
        Enables `board[row][col]` access, returning the letter string or None.
        Provides 100% backward compatibility with crosscheck.py and gaddag.py.
        """
        return BoardRowProxy(self.grid[row])

    def __len__(self) -> int:
        return 15

    def get_tile(self, row: int, col: int) -> Optional[PlacedTile]:
        """Returns the PlacedTile object at (row, col), or None if empty."""
        if 0 <= row < 15 and 0 <= col < 15:
            return self.grid[row][col]
        return None

    def is_empty_square(self, row: int, col: int) -> bool:
        """Returns True if the square is within bounds and unoccupied."""
        return 0 <= row < 15 and 0 <= col < 15 and self.grid[row][col] is None

    def is_first_move(self) -> bool:
        """Returns True if no tiles have been placed on the board yet."""
        for r in range(15):
            for c in range(15):
                if self.grid[r][c] is not None:
                    return False
        return True

    def _normalize_direction(self, direction: str) -> str:
        d = direction.strip().upper()
        if d in ("H", "ACROSS", "HORIZONTAL", "RIGHT"):
            return "H"
        if d in ("V", "DOWN", "VERTICAL"):
            return "V"
        raise ValueError(f"Invalid direction: '{direction}'. Expected 'H' (across) or 'V' (down).")

    def is_valid_placement(
        self,
        word: str,
        row: int,
        col: int,
        direction: str
    ) -> Tuple[bool, str, List[str]]:
        """
        Validates whether a word placement complies with Scrabble board rules.

        Returns:
            (is_valid: bool, reason: str, tiles_needed_from_rack: List[str])
        """
        word = word.strip().upper()
        if len(word) < 2:
            return False, "Word must be at least 2 letters long.", []

        d = self._normalize_direction(direction)
        dr, dc = (0, 1) if d == "H" else (1, 0)

        # 1. Check boundary limits
        end_r = row + dr * (len(word) - 1)
        end_c = col + dc * (len(word) - 1)
        if not (0 <= row < 15 and 0 <= col < 15 and 0 <= end_r < 15 and 0 <= end_c < 15):
            return False, "Word extends beyond board boundaries.", []

        # 2. Check overlap consistency and collect newly placed letters
        new_tiles_needed = []
        touches_existing = False
        covers_center = False
        placed_any_new = False

        for i, letter in enumerate(word):
            curr_r = row + dr * i
            curr_c = col + dc * i

            if (curr_r, curr_c) == (7, 7):
                covers_center = True

            existing = self.grid[curr_r][curr_c]
            if existing is not None:
                if existing.letter != letter:
                    return False, f"Letter '{letter}' at {format_coords(curr_r, curr_c)} conflicts with existing '{existing.letter}'.", []
                touches_existing = True
            else:
                placed_any_new = True
                new_tiles_needed.append(letter)
                # Check adjacency in all 4 directions for newly placed tiles
                for adj_r, adj_c in [
                    (curr_r - 1, curr_c), (curr_r + 1, curr_c),
                    (curr_r, curr_c - 1), (curr_r, curr_c + 1)
                ]:
                    if 0 <= adj_r < 15 and 0 <= adj_c < 15:
                        if self.grid[adj_r][adj_c] is not None:
                            touches_existing = True

        if not placed_any_new:
            return False, "At least one new tile must be placed from your rack.", []

        # 3. First move must cover center square (7, 7)
        if self.is_first_move():
            if not covers_center:
                return False, "First move must cover the center star (H8).", []
        else:
            # Subsequent moves must connect to an existing tile
            if not touches_existing:
                return False, "Move must connect to or overlap at least one existing tile on the board.", []

        return True, "Valid placement.", new_tiles_needed

    def score_move(
        self,
        word: str,
        row: int,
        col: int,
        direction: str,
        blank_indices: Optional[List[int]] = None
    ) -> Tuple[int, List[str]]:
        """
        Calculates the score for placing `word` at (row, col) in `direction`.

        Scoring Rules:
        - Premium squares (DL, TL, DW, TW, Center) only apply to NEWLY PLACED tiles.
        - Blank tiles score 0 points (even if on DL/TL).
        - Multiple word multipliers stack multiplicatively (e.g. 2x and 3x = 6x).
        - Detects and scores any perpendicular cross-words formed on that turn.
        - +50 points Bingo bonus if exactly 7 tiles from the rack are placed.

        Returns:
            (total_score: int, words_formed: List[str])
        """
        word = word.strip().upper()
        d = self._normalize_direction(direction)
        dr, dc = (0, 1) if d == "H" else (1, 0)
        blank_set = set(blank_indices) if blank_indices else set()

        main_word_letters_score = 0
        main_word_mult = 1
        new_tiles_count = 0
        cross_words_score = 0
        words_formed = [word]

        for i, letter in enumerate(word):
            curr_r = row + dr * i
            curr_c = col + dc * i
            existing = self.grid[curr_r][curr_c]

            if existing is not None:
                # Existing tile: counts base score only, no multipliers
                main_word_letters_score += existing.score
            else:
                # Newly placed tile
                new_tiles_count += 1
                is_blank = (i in blank_set)
                tile_val = 0 if is_blank else TILE_SCORES.get(letter, 0)

                prem = PREMIUM_MAP[curr_r][curr_c]
                let_mult = 1

                if prem == DL:
                    let_mult = 2
                elif prem == TL:
                    let_mult = 3
                elif prem in (DW, STAR):
                    main_word_mult *= 2
                elif prem == TW:
                    main_word_mult *= 3

                main_word_letters_score += tile_val * let_mult

                # Check for perpendicular cross-word formed at (curr_r, curr_c)
                # For horizontal move, check vertical; for vertical move, check horizontal.
                p_dr, p_dc = (1, 0) if d == "H" else (0, 1)

                # Scan backwards in perpendicular direction
                r_start, c_start = curr_r, curr_c
                while (0 <= r_start - p_dr < 15 and 0 <= c_start - p_dc < 15 and
                       self.grid[r_start - p_dr][c_start - p_dc] is not None):
                    r_start -= p_dr
                    c_start -= p_dc

                # Scan forwards in perpendicular direction
                r_end, c_end = curr_r, curr_c
                while (0 <= r_end + p_dr < 15 and 0 <= c_end + p_dc < 15 and
                       self.grid[r_end + p_dr][c_end + p_dc] is not None):
                    r_end += p_dr
                    c_end += p_dc

                # If perpendicular span is greater than 1 square, a cross-word was formed!
                if (r_start, c_start) != (r_end, c_end):
                    cross_score = 0
                    cross_mult = 1
                    cross_word_letters = []

                    # Apply word multiplier to cross word if current square has one
                    if prem in (DW, STAR):
                        cross_mult *= 2
                    elif prem == TW:
                        cross_mult *= 3

                    scan_r, scan_c = r_start, c_start
                    steps = max(abs(r_end - r_start), abs(c_end - c_start)) + 1
                    for _ in range(steps):
                        if (scan_r, scan_c) == (curr_r, curr_c):
                            cross_score += tile_val * let_mult
                            cross_word_letters.append(letter)
                        else:
                            tile = self.grid[scan_r][scan_c]
                            if tile is not None:
                                cross_score += tile.score
                                cross_word_letters.append(tile.letter)
                        scan_r += p_dr
                        scan_c += p_dc

                    cross_total = cross_score * cross_mult
                    cross_words_score += cross_total
                    words_formed.append("".join(cross_word_letters))

        main_total = main_word_letters_score * main_word_mult
        total_score = main_total + cross_words_score

        # Bingo bonus: 50 points if playing all 7 tiles from rack
        if new_tiles_count == 7:
            total_score += 50

        return total_score, words_formed

    def place_move(
        self,
        word: str,
        row: int,
        col: int,
        direction: str,
        blank_indices: Optional[List[int]] = None
    ) -> Tuple[int, List[str]]:
        """
        Scores and permanently places `word` on the board.

        Returns:
            (score: int, words_formed: List[str])
        """
        score, words_formed = self.score_move(
            word, row, col, direction, blank_indices
        )

        d = self._normalize_direction(direction)
        dr, dc = (0, 1) if d == "H" else (1, 0)
        blank_set = set(blank_indices) if blank_indices else set()

        for i, letter in enumerate(word.upper()):
            curr_r = row + dr * i
            curr_c = col + dc * i
            if self.grid[curr_r][curr_c] is None:
                is_blank = (i in blank_set)
                self.grid[curr_r][curr_c] = PlacedTile(letter, is_blank=is_blank)

        return score, words_formed

    def render(self, color: bool = True) -> str:
        """
        Renders an ANSI colorized 15x15 board with coordinate headers (A-O, 1-15).
        """
        col_headers = "     " + "   ".join(chr(ord('A') + c) for c in range(15))
        separator = "   +" + "---+" * 15
        lines = [col_headers, separator]

        for r in range(15):
            row_label = f"{r + 1:2} |"
            row_parts = []
            for c in range(15):
                tile = self.grid[r][c]
                prem = PREMIUM_MAP[r][c]

                if tile is not None:
                    # Placed tile: distinct background
                    score = tile.score
                    letter = tile.letter.lower() if tile.is_blank else tile.letter
                    if color:
                        # Bright white text on blue/green tile
                        bg = "\033[1;30;47m" if not tile.is_blank else "\033[1;30;43m"
                        row_parts.append(f"{bg} {letter} \033[0m")
                    else:
                        row_parts.append(f" {letter} ")
                else:
                    # Empty square: show premium code or dot
                    if prem == TW:
                        text = "3W"
                        bg = "\033[1;37;41m" if color else ""
                    elif prem == DW:
                        text = "2W"
                        bg = "\033[1;37;45m" if color else ""
                    elif prem == TL:
                        text = "3L"
                        bg = "\033[1;37;44m" if color else ""
                    elif prem == DL:
                        text = "2L"
                        bg = "\033[1;37;46m" if color else ""
                    elif prem == STAR:
                        text = "★ "
                        bg = "\033[1;30;43m" if color else ""
                    else:
                        text = "· "
                        bg = "\033[90m" if color else ""

                    if color:
                        row_parts.append(f"{bg} {text}\033[0m")
                    else:
                        row_parts.append(f" {text}")

            line = row_label + "|".join(row_parts) + f"| {r + 1}"
            lines.append(line)
            lines.append(separator)

        lines.append(col_headers)
        return "\n".join(lines)

