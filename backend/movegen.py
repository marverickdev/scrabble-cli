"""
movegen.py - Steven Gordon's GADDAG Move Generation Algorithm for Scrabble.
Generates all legal Across and Down moves, evaluating cross-checks and blanks.
"""

from typing import List, Tuple, Set, Optional, Dict, Any
from backend.gaddag import GADDAG, GADDAGNode
from backend.board import Board
import backend.crosscheck as crosscheck
import backend.fitness as fitness


class ScrabbleMove:
    """
    Represents a candidate Scrabble move on the board.
    Fully compatible with fitness.py and montecarlo.py.
    """
    __slots__ = [
        'word', 'row', 'col', 'direction',
        'score', 'tiles_played', 'blank_indices',
        'words_formed', 'heuristic_fitness'
    ]

    def __init__(
        self,
        word: str,
        row: int,
        col: int,
        direction: str,
        score: int,
        tiles_played: List[str],
        blank_indices: Optional[List[int]] = None,
        words_formed: Optional[List[str]] = None,
        heuristic_fitness: float = 0.0
    ):
        self.word = word.upper()
        self.row = row
        self.col = col
        self.direction = direction.upper()
        self.score = score
        self.tiles_played = tiles_played
        self.blank_indices = blank_indices or []
        self.words_formed = words_formed or [self.word]
        self.heuristic_fitness = heuristic_fitness

    def __repr__(self) -> str:
        coords = f"({self.row},{self.col}) {self.direction}"
        return (
            f"Move({self.word} at {coords}, score={self.score}, "
            f"fitness={self.heuristic_fitness:.1f})"
        )

    def __lt__(self, other: "ScrabbleMove") -> bool:
        # Default sort by heuristic fitness descending, then score descending
        if self.heuristic_fitness != other.heuristic_fitness:
            return self.heuristic_fitness < other.heuristic_fitness
        return self.score < other.score


# Alias for compatibility with montecarlo.py
Move = ScrabbleMove


def _find_row_anchors(board: Any, row: int, is_first_move: bool) -> List[int]:
    """
    Identifies all anchor columns in a given row.
    - If opening move: anchor is only column 7 (center star H8) on row 7.
    - If subsequent move: an anchor is any empty square adjacent to an occupied tile.
    """
    if is_first_move:
        return [7] if row == 7 else []

    anchors = []
    for c in range(15):
        if board[row][c] is not None:
            continue  # Occupied square cannot be an anchor

        # Check orthogonal adjacency (up, down, left, right)
        is_anchor = False
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, c + dc
            if 0 <= nr < 15 and 0 <= nc < 15:
                if board[nr][nc] is not None:
                    is_anchor = True
                    break

        if is_anchor:
            anchors.append(c)

    return anchors


def _generate_row_moves(
    board: Any,
    row: int,
    anchors: List[int],
    rack_tiles: List[str],
    gaddag: GADDAG,
    cross_checks: Dict[Tuple[int, int], Set[str]],
    seen_moves: Set[Tuple[str, int, int, Tuple[int, ...]]],
    output_moves: List[Tuple[str, int, int, List[int], List[str]]]
) -> None:
    """
    Executes Steven Gordon's GADDAG traversal for all anchors in a single row.
    Populates output_moves with (word, row, start_col, blank_indices, tiles_played).
    """
    prev_anchor = -1

    for anchor_c in anchors:
        min_c = prev_anchor + 1

        def traverse(
            curr_c: int,
            node: GADDAGNode,
            rem_rack: List[str],
            word_tiles: List[Tuple[int, str, bool, bool]],  # (col, letter, is_blank, is_new)
            direction: str
        ):
            if direction == "LEFT":
                # 1. Pivot check: transition across delimiter '>' to moving RIGHT
                if gaddag.delimiter in node.children:
                    # Can only pivot if the square to the left is empty or off-board
                    if curr_c < 0 or board[row][curr_c] is None:
                        traverse(
                            anchor_c + 1,
                            node.children[gaddag.delimiter],
                            rem_rack,
                            word_tiles,
                            "RIGHT"
                        )

                # 2. Continue moving LEFT
                if curr_c >= 0:
                    existing = board[row][curr_c]
                    if existing is not None:
                        letter = str(existing)
                        if letter in node.children:
                            traverse(
                                curr_c - 1,
                                node.children[letter],
                                rem_rack,
                                word_tiles + [(curr_c, letter, False, False)],
                                "LEFT"
                            )
                    elif curr_c >= min_c:
                        valid_letters = cross_checks.get((row, curr_c), set())
                        unique_tiles = set(rem_rack)

                        for t in unique_tiles:
                            if t != '?':
                                if t in valid_letters and t in node.children:
                                    new_rack = rem_rack.copy()
                                    new_rack.remove(t)
                                    traverse(
                                        curr_c - 1,
                                        node.children[t],
                                        new_rack,
                                        word_tiles + [(curr_c, t, False, True)],
                                        "LEFT"
                                    )
                            else:
                                # Blank tile can represent any valid letter
                                for letter in sorted(node.children.keys()):
                                    if letter != gaddag.delimiter and letter in valid_letters:
                                        new_rack = rem_rack.copy()
                                        new_rack.remove('?')
                                        traverse(
                                            curr_c - 1,
                                            node.children[letter],
                                            new_rack,
                                            word_tiles + [(curr_c, letter, True, True)],
                                            "LEFT"
                                        )

            elif direction == "RIGHT":
                # 1. Move acceptance check
                if node.is_word:
                    # Must not cut an existing tile on the right
                    if curr_c >= 15 or board[row][curr_c] is None:
                        # Must have placed at least one tile from rack
                        if any(is_new for _, _, _, is_new in word_tiles):
                            sorted_tiles = sorted(word_tiles, key=lambda x: x[0])
                            start_c = sorted_tiles[0][0]
                            full_word = "".join(l for _, l, _, _ in sorted_tiles)

                            if len(full_word) >= 2:
                                blanks = [
                                    idx for idx, (_, _, is_b, _) in enumerate(sorted_tiles)
                                    if is_b
                                ]
                                key = (full_word, row, start_c, tuple(blanks))
                                if key not in seen_moves:
                                    seen_moves.add(key)
                                    tiles_played = [
                                        ('?' if is_b else l)
                                        for _, l, is_b, is_new in sorted_tiles
                                        if is_new
                                    ]
                                    output_moves.append(
                                        (full_word, row, start_c, blanks, tiles_played)
                                    )

                # 2. Continue moving RIGHT
                if curr_c < 15:
                    existing = board[row][curr_c]
                    if existing is not None:
                        letter = str(existing)
                        if letter in node.children:
                            traverse(
                                curr_c + 1,
                                node.children[letter],
                                rem_rack,
                                word_tiles + [(curr_c, letter, False, False)],
                                "RIGHT"
                            )
                    else:
                        valid_letters = cross_checks.get((row, curr_c), set())
                        unique_tiles = set(rem_rack)

                        for t in unique_tiles:
                            if t != '?':
                                if t in valid_letters and t in node.children:
                                    new_rack = rem_rack.copy()
                                    new_rack.remove(t)
                                    traverse(
                                        curr_c + 1,
                                        node.children[t],
                                        new_rack,
                                        word_tiles + [(curr_c, t, False, True)],
                                        "RIGHT"
                                    )
                            else:
                                for letter in sorted(node.children.keys()):
                                    if letter != gaddag.delimiter and letter in valid_letters:
                                        new_rack = rem_rack.copy()
                                        new_rack.remove('?')
                                        traverse(
                                            curr_c + 1,
                                            node.children[letter],
                                            new_rack,
                                            word_tiles + [(curr_c, letter, True, True)],
                                            "RIGHT"
                                        )

        # Start traversal at anchor_c moving LEFT
        traverse(anchor_c, gaddag.root, rack_tiles, [], "LEFT")
        prev_anchor = anchor_c


def generate_all_moves(
    board: Board,
    rack: Any,
    gaddag: GADDAG,
    top_n: Optional[int] = None,
    sort_by: str = "fitness"
) -> List[ScrabbleMove]:
    """
    Generates all legal moves (Across and Down) for the current board and rack.
    Scores each move and computes its heuristic fitness.

    Args:
        board: The current Board instance.
        rack: List of tile strings or a Rack object (e.g. ['C', 'A', 'T', '?']).
        gaddag: The populated GADDAG lexicon.
        top_n: Optional limit on the number of returned moves.
        sort_by: "fitness" (default) or "score".

    Returns:
        Sorted list of legal ScrabbleMove objects.
    """
    rack_tiles = [str(t).upper() for t in rack]
    is_first = board.is_first_move()
    candidate_moves: List[ScrabbleMove] = []

    # ---------------------------------------------------------
    # 1. HORIZONTAL (Across) MOVES
    # ---------------------------------------------------------
    cross_checks_h = crosscheck.calculate_cross_checks(board, gaddag)
    seen_h: Set[Tuple[str, int, int, Tuple[int, ...]]] = set()
    raw_h: List[Tuple[str, int, int, List[int], List[str]]] = []

    for r in range(15):
        anchors = _find_row_anchors(board, r, is_first)
        if anchors:
            _generate_row_moves(
                board, r, anchors, rack_tiles, gaddag,
                cross_checks_h, seen_h, raw_h
            )

    for word, r, c, blanks, tiles_played in raw_h:
        score, words_formed = board.score_move(word, r, c, "H", blanks)
        move = ScrabbleMove(
            word=word,
            row=r,
            col=c,
            direction="H",
            score=score,
            tiles_played=tiles_played,
            blank_indices=blanks,
            words_formed=words_formed
        )
        move.heuristic_fitness = fitness.evaluate_move(move, rack_tiles, board)
        candidate_moves.append(move)

    # ---------------------------------------------------------
    # 2. VERTICAL (Down) MOVES (via Transposition)
    # ---------------------------------------------------------
    # Create transposed board grid where t_board[r][c] = board[c][r]
    t_board = [[board[c][r] for c in range(15)] for r in range(15)]
    cross_checks_v = crosscheck.calculate_cross_checks(t_board, gaddag)
    seen_v: Set[Tuple[str, int, int, Tuple[int, ...]]] = set()
    raw_v: List[Tuple[str, int, int, List[int], List[str]]] = []

    for r in range(15):
        anchors = _find_row_anchors(t_board, r, is_first)
        if anchors:
            _generate_row_moves(
                t_board, r, anchors, rack_tiles, gaddag,
                cross_checks_v, seen_v, raw_v
            )

    for word, t_r, t_c, blanks, tiles_played in raw_v:
        # Re-map coordinates from transposed board to original:
        # row in original = t_c (col in transposed)
        # col in original = t_r (row in transposed)
        orig_row = t_c
        orig_col = t_r

        # If opening move, horizontal and vertical are symmetric.
        # To avoid identical plays on turn 1, skip if (word, orig_row, orig_col, "H") already recorded
        if is_first and orig_row == orig_col:
            pass  # keep both as valid options or include both

        score, words_formed = board.score_move(word, orig_row, orig_col, "V", blanks)
        move = ScrabbleMove(
            word=word,
            row=orig_row,
            col=orig_col,
            direction="V",
            score=score,
            tiles_played=tiles_played,
            blank_indices=blanks,
            words_formed=words_formed
        )
        move.heuristic_fitness = fitness.evaluate_move(move, rack_tiles, board)
        candidate_moves.append(move)

    # ---------------------------------------------------------
    # 3. SORTING AND FILTERING
    # ---------------------------------------------------------
    if sort_by == "score":
        candidate_moves.sort(key=lambda m: (m.score, m.heuristic_fitness), reverse=True)
    else:
        candidate_moves.sort(key=lambda m: (m.heuristic_fitness, m.score), reverse=True)

    if top_n is not None and top_n > 0:
        return candidate_moves[:top_n]

    return candidate_moves
