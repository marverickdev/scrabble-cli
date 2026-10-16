"""
frontend/board_widget.py - Interactive 15x15 Scrabble Board Widget with Drag-and-Drop.
"""

from typing import Dict, Tuple, Optional, Any, List
from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QLabel, QFrame, QVBoxLayout, QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import (
    QFont, QColor, QMouseEvent, QDragEnterEvent, QDragMoveEvent, QDropEvent
)

from backend.board import PREMIUM_MAP, format_coords, parse_coords, Board
from backend.bag import TILE_SCORES
from frontend.dialogs import BlankTileDialog


# Colors and labels for premium squares
PREMIUM_COLORS = {
    "3W": {"bg": "#b71c1c", "text": "3W\nWORD", "color": "#ffffff", "font_size": 7},
    "2W": {"bg": "#e57373", "text": "2W\nWORD", "color": "#ffffff", "font_size": 7},
    "3L": {"bg": "#1565c0", "text": "3L\nLTR", "color": "#ffffff", "font_size": 7},
    "2L": {"bg": "#81d4fa", "text": "2L\nLTR", "color": "#01579b", "font_size": 7},
    "★ ": {"bg": "#ffd54f", "text": "★", "color": "#5d4037", "font_size": 13},
    "..": {"bg": "#f5eedc", "text": "", "color": "#000000", "font_size": 7}
}


class BoardSquareWidget(QFrame):
    """
    Represents an individual square (cell) on the 15x15 Scrabble board.
    Supports accepting drops from DraggableTileWidget and clicking to recall temporary tiles.
    """
    def __init__(self, row: int, col: int, board_widget: 'BoardWidget'):
        super().__init__(board_widget)
        self.row = row
        self.col = col
        self.board_widget = board_widget
        self.setAcceptDrops(True)
        self.setFixedSize(38, 38)

        self.premium_type = PREMIUM_MAP[row][col]
        self.committed_tile: Optional[Dict[str, Any]] = None  # permanently placed tile
        self.uncommitted_tile: Optional[Dict[str, Any]] = None  # placed this turn

        # Layout
        self.cell_layout = QVBoxLayout(self)
        self.cell_layout.setContentsMargins(1, 1, 1, 1)
        self.cell_layout.setSpacing(0)

        self.main_label = QLabel(self)
        self.main_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cell_layout.addWidget(self.main_label)

        self.render_state()

    def render_state(self):
        """Updates background color, border, and text based on tile state."""
        if self.committed_tile is not None:
            # Permanent tile on board
            letter = self.committed_tile["letter"]
            is_blank = self.committed_tile.get("is_blank", False)
            score = 0 if is_blank else TILE_SCORES.get(letter, 0)
            score_txt = "" if is_blank else f"<sub style='font-size:7px;'>{score}</sub>"
            self.setStyleSheet("""
                BoardSquareWidget {
                    background-color: #f7ecd5;
                    border: 1px solid #a68453;
                    border-radius: 3px;
                }
            """)
            self.main_label.setText(f"<b>{letter}</b>{score_txt}")
            self.main_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            self.main_label.setStyleSheet("color: #2b1d0c;")
            self.setCursor(Qt.CursorShape.ArrowCursor)

        elif self.uncommitted_tile is not None:
            # Tile placed this turn (temporary)
            letter = self.uncommitted_tile.get("represented_letter", self.uncommitted_tile["letter"])
            is_blank = self.uncommitted_tile.get("is_blank", False)
            score = 0 if is_blank else TILE_SCORES.get(self.uncommitted_tile["letter"], 0)
            score_txt = "" if is_blank else f"<sub style='font-size:7px;'>{score}</sub>"
            self.setStyleSheet("""
                BoardSquareWidget {
                    background-color: #fff9c4;
                    border: 2px solid #ff9800;
                    border-radius: 4px;
                }
                BoardSquareWidget:hover {
                    background-color: #ffe082;
                    border: 2px solid #e65100;
                }
            """)
            self.main_label.setText(f"<b>{letter}</b>{score_txt}")
            self.main_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            self.main_label.setStyleSheet("color: #b71c1c;" if is_blank else "color: #2b1d0c;")
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        else:
            # Empty premium or normal square
            style = PREMIUM_COLORS.get(self.premium_type, PREMIUM_COLORS[".."])
            bg = style["bg"]
            self.setStyleSheet(f"""
                BoardSquareWidget {{
                    background-color: {bg};
                    border: 1px solid #d4c5a9;
                    border-radius: 2px;
                }}
            """)
            self.main_label.setText(style["text"])
            self.main_label.setFont(QFont("Arial", style["font_size"], QFont.Weight.Bold))
            self.main_label.setStyleSheet(f"color: {style['color']};")
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, a0: Optional[QMouseEvent]):
        # Clicking an uncommitted tile removes it and returns it to the rack
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton and self.uncommitted_tile is not None:
            rack_idx = self.uncommitted_tile["rack_index"]
            self.board_widget.recall_tile(self.row, self.col, rack_idx)
        if a0 is not None:
            super().mousePressEvent(a0)

    def dragEnterEvent(self, a0: Optional[QDragEnterEvent]):
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is None or not mime.hasFormat("application/x-scrabble-tile"):
            a0.ignore()
            return
        # Reject if square already occupied
        if self.committed_tile is not None or self.uncommitted_tile is not None:
            a0.ignore()
            return
        a0.acceptProposedAction()

    def dragMoveEvent(self, a0: Optional[QDragMoveEvent]):
        if a0 is not None:
            if self.committed_tile is None and self.uncommitted_tile is None:
                a0.acceptProposedAction()
            else:
                a0.ignore()

    def dropEvent(self, a0: Optional[QDropEvent]):
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is None or not mime.hasFormat("application/x-scrabble-tile"):
            a0.ignore()
            return

        raw = mime.data("application/x-scrabble-tile").data().decode("utf-8")
        parts = raw.split(":")
        if len(parts) < 3:
            a0.ignore()
            return

        letter = parts[0]
        rack_idx = int(parts[1])
        is_blank = (parts[2] == "1")

        represented = letter
        if is_blank:
            # Prompt for letter assignment
            dialog = BlankTileDialog(self)
            if dialog.exec() and dialog.selected_letter:
                represented = dialog.selected_letter.upper()
            else:
                # Cancelled: restore tile to rack
                self.board_widget.tile_cancelled_signal.emit(rack_idx)
                a0.ignore()
                return

        tile_data = {
            "letter": letter,
            "represented_letter": represented,
            "rack_index": rack_idx,
            "is_blank": is_blank
        }
        self.uncommitted_tile = tile_data
        self.render_state()

        self.board_widget.record_tile_placed(self.row, self.col, tile_data)
        a0.acceptProposedAction()


class BoardWidget(QWidget):
    """
    15x15 Scrabble Board Widget with coordinate headers and move reconstruction.
    """
    tile_placed_signal = pyqtSignal(int)      # emits rack_index
    tile_recalled_signal = pyqtSignal(int)    # emits rack_index
    tile_cancelled_signal = pyqtSignal(int)   # emits rack_index

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.pending_placements: Dict[Tuple[int, int], Dict[str, Any]] = {}
        self.cells: List[List[BoardSquareWidget]] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        grid = QGridLayout()
        grid.setSpacing(2)

        # Top column headers A - O
        for c in range(15):
            col_letter = chr(ord('A') + c)
            lbl = QLabel(col_letter)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #5c3514;")
            lbl.setFixedWidth(38)
            grid.addWidget(lbl, 0, c + 1)

        # Left row headers 1 - 15 and 15x15 squares
        for r in range(15):
            row_lbl = QLabel(str(r + 1))
            row_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_lbl.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            row_lbl.setStyleSheet("color: #5c3514;")
            row_lbl.setFixedHeight(38)
            grid.addWidget(row_lbl, r + 1, 0)

            row_cells = []
            for c in range(15):
                cell = BoardSquareWidget(r, c, self)
                grid.addWidget(cell, r + 1, c + 1)
                row_cells.append(cell)
            self.cells.append(row_cells)

        main_layout.addLayout(grid)

    def record_tile_placed(self, row: int, col: int, tile_data: Dict[str, Any]):
        self.pending_placements[(row, col)] = tile_data
        self.tile_placed_signal.emit(tile_data["rack_index"])

    def recall_tile(self, row: int, col: int, rack_idx: int):
        if (row, col) in self.pending_placements:
            del self.pending_placements[(row, col)]
        self.cells[row][col].uncommitted_tile = None
        self.cells[row][col].render_state()
        self.tile_recalled_signal.emit(rack_idx)

    def recall_all_pending(self):
        """Recalls all pending uncommitted tiles back to the rack."""
        coords = list(self.pending_placements.keys())
        for r, c in coords:
            tile_data = self.pending_placements[r, c]
            rack_idx = tile_data["rack_index"]
            self.cells[r][c].uncommitted_tile = None
            self.cells[r][c].render_state()
            self.tile_recalled_signal.emit(rack_idx)
        self.pending_placements.clear()

    def sync_board_state(self, board: Board):
        """Syncs committed tiles from the Scrabble board model."""
        self.pending_placements.clear()
        for r in range(15):
            for c in range(15):
                pt = board.get_tile(r, c)
                cell = self.cells[r][c]
                cell.uncommitted_tile = None
                if pt is not None:
                    cell.committed_tile = {
                        "letter": pt.letter,
                        "is_blank": pt.is_blank
                    }
                else:
                    cell.committed_tile = None
                cell.render_state()

    def get_pending_move(self, board: Board) -> Tuple[Optional[Tuple[str, str, str, List[int]]], Optional[str]]:
        """
        Reconstructs the move from uncommitted tiles on the board.
        Returns:
            ((word, coord_str, direction, blank_indices), None) on success,
            (None, error_message) on failure.
        """
        if not self.pending_placements:
            return None, "Place tiles on the board first, or Pass / Exchange."

        coords = list(self.pending_placements.keys())

        # Check linearity
        rows = {r for r, c in coords}
        cols = {c for r, c in coords}

        if len(rows) > 1 and len(cols) > 1:
            return None, "All placed tiles must be in a single straight row or column."

        # Case 1: Exactly 1 tile placed
        if len(coords) == 1:
            r, c = coords[0]
            tile_data = self.pending_placements[(r, c)]
            tile_char = tile_data["represented_letter"]
            is_blank = tile_data["is_blank"]

            # Check if board is empty (first move requires at least 2 letters)
            if board.is_first_move():
                return None, "First move must be a word of at least 2 letters covering center (H8)."

            # Detect horizontal vs vertical connectivity
            has_h = (c > 0 and board.grid[r][c - 1] is not None) or (c < 14 and board.grid[r][c + 1] is not None)
            has_v = (r > 0 and board.grid[r - 1][c] is not None) or (r < 14 and board.grid[r + 1][c] is not None)

            if not has_h and not has_v:
                return None, "Placed tile must connect to existing tiles on the board."

            # Determine main direction (prefer the longer word or H)
            # Reconstruct H word
            h_word, h_coord, h_blanks = self._reconstruct_line(board, r, c, c, "H")
            # Reconstruct V word
            v_word, v_coord, v_blanks = self._reconstruct_line(board, c, r, r, "V")

            if len(h_word) >= 2 and len(v_word) >= 2:
                # Both valid words formed; prefer horizontal or whichever is longer
                if len(v_word) > len(h_word):
                    return (v_word, v_coord, "V", v_blanks), None
                return (h_word, h_coord, "H", h_blanks), None
            elif len(h_word) >= 2:
                return (h_word, h_coord, "H", h_blanks), None
            elif len(v_word) >= 2:
                return (v_word, v_coord, "V", v_blanks), None
            else:
                return None, "Move does not form a valid word with adjacent tiles."

        # Case 2: Multiple tiles placed horizontally
        if len(rows) == 1:
            fixed_row = next(iter(rows))
            min_c = min(cols)
            max_c = max(cols)

            # Check for gaps between min_c and max_c
            for col in range(min_c, max_c + 1):
                if (fixed_row, col) not in self.pending_placements and board.grid[fixed_row][col] is None:
                    return None, "Placed tiles must form a contiguous word without empty gaps."

            word, coord_str, blank_indices = self._reconstruct_line(board, fixed_row, min_c, max_c, "H")
            return (word, coord_str, "H", blank_indices), None

        # Case 3: Multiple tiles placed vertically
        else:
            fixed_col = next(iter(cols))
            min_r = min(rows)
            max_r = max(rows)

            # Check for gaps between min_r and max_r
            for row in range(min_r, max_r + 1):
                if (row, fixed_col) not in self.pending_placements and board.grid[row][fixed_col] is None:
                    return None, "Placed tiles must form a contiguous word without empty gaps."

            word, coord_str, blank_indices = self._reconstruct_line(board, fixed_col, min_r, max_r, "V")
            return (word, coord_str, "V", blank_indices), None

    def _reconstruct_line(
        self,
        board: Board,
        fixed_idx: int,
        min_idx: int,
        max_idx: int,
        direction: str
    ) -> Tuple[str, str, List[int]]:
        """
        Expands outwards along row or col to form full word and track blank indices.
        """
        # Expand backwards to start of contiguous word
        start_idx = min_idx
        while start_idx > 0:
            check_r = fixed_idx if direction == "H" else start_idx - 1
            check_c = start_idx - 1 if direction == "H" else fixed_idx
            if board.grid[check_r][check_c] is not None:
                start_idx -= 1
            else:
                break

        # Expand forwards to end of contiguous word
        end_idx = max_idx
        while end_idx < 14:
            check_r = fixed_idx if direction == "H" else end_idx + 1
            check_c = end_idx + 1 if direction == "H" else fixed_idx
            if board.grid[check_r][check_c] is not None:
                end_idx += 1
            else:
                break

        # Construct full word and blank indices
        full_word = []
        blank_indices = []

        for idx_offset, pos in enumerate(range(start_idx, end_idx + 1)):
            curr_r = fixed_idx if direction == "H" else pos
            curr_c = pos if direction == "H" else fixed_idx

            if (curr_r, curr_c) in self.pending_placements:
                p = self.pending_placements[(curr_r, curr_c)]
                full_word.append(p["represented_letter"])
                if p["is_blank"]:
                    blank_indices.append(idx_offset)
            else:
                tile = board.grid[curr_r][curr_c]
                if tile is not None:
                    full_word.append(tile.letter)

        word_str = "".join(full_word)
        start_r = fixed_idx if direction == "H" else start_idx
        start_c = start_idx if direction == "H" else fixed_idx
        coord_str = format_coords(start_r, start_c)

        return word_str, coord_str, blank_indices
