"""
frontend/rack_widget.py - Draggable Scrabble Rack & Tile Widgets.
"""

from typing import List, Optional, Callable
import random

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QMimeData, pyqtSignal
from PyQt6.QtGui import (
    QMouseEvent, QDrag, QPainter, QColor, QFont, QPen,
    QDragEnterEvent, QDragMoveEvent, QDropEvent
)

from backend.bag import TILE_SCORES


class DraggableTileWidget(QFrame):
    """
    A single Scrabble tile on the player's rack.
    Supports initiating a QDrag when dragged by the user.
    """
    def __init__(
        self,
        letter: str,
        rack_index: int,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.letter = letter.upper()
        self.is_blank = (self.letter == '?')
        self.rack_index = rack_index
        self.drag_start_pos: Optional[QPoint] = None

        self.setFixedSize(50, 50)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setStyleSheet("""
            DraggableTileWidget {
                background-color: #f7ecd5;
                border: 2px solid #b38f5e;
                border-radius: 6px;
            }
            DraggableTileWidget:hover {
                background-color: #fffaee;
                border: 2px solid #855928;
            }
        """)

        tile_layout = QHBoxLayout(self)
        tile_layout.setContentsMargins(2, 2, 4, 4)

        # Main letter
        display_char = " " if self.is_blank else self.letter
        self.letter_label = QLabel(display_char, self)
        self.letter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.letter_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        self.letter_label.setStyleSheet("color: #2b1d0c; background: transparent; border: none;")

        # Subscript score
        score_val = 0 if self.is_blank else TILE_SCORES.get(self.letter, 0)
        score_str = "" if self.is_blank else str(score_val)
        self.score_label = QLabel(score_str, self)
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        self.score_label.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        self.score_label.setStyleSheet("color: #5a4224; background: transparent; border: none;")

        tile_layout.addWidget(self.letter_label, 1)
        tile_layout.addWidget(self.score_label, 0)

    def mousePressEvent(self, a0: Optional[QMouseEvent]):
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = a0.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        if a0 is not None:
            super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0: Optional[QMouseEvent]):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if a0 is not None:
            super().mouseReleaseEvent(a0)

    def mouseMoveEvent(self, a0: Optional[QMouseEvent]):
        if a0 is None:
            return
        if not (a0.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.drag_start_pos is None:
            return
        if (a0.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        # Start Drag
        drag = QDrag(self)
        mime_data = QMimeData()
        payload = f"{self.letter}:{self.rack_index}:{1 if self.is_blank else 0}"
        mime_data.setData("application/x-scrabble-tile", payload.encode("utf-8"))
        mime_data.setText(payload)
        drag.setMimeData(mime_data)

        # Render preview pixmap
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Hide widget during drag
        self.hide()
        drop_action = drag.exec(Qt.DropAction.MoveAction)

        # If drag was cancelled or rejected, restore tile
        if drop_action == Qt.DropAction.IgnoreAction:
            self.show()
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class RackWidget(QFrame):
    """
    Container representing the wooden tile rack of the human player.
    Holds up to 7 DraggableTileWidgets and supports recall, shuffling,
    and receiving dragged tiles dropped back onto the rack.
    """
    tile_recalled_signal = pyqtSignal(int)  # emits rack_index when dropped back

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(76)
        self.setStyleSheet("""
            RackWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8c572a, stop:1 #5c3514);
                border: 3px solid #3c1e08;
                border-radius: 8px;
                padding: 4px;
            }
        """)

        self.rack_layout = QHBoxLayout(self)
        self.rack_layout.setContentsMargins(16, 8, 16, 8)
        self.rack_layout.setSpacing(12)
        self.rack_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tiles_data: List[str] = []
        self.tile_widgets: List[DraggableTileWidget] = []
        self.on_recall_callback: Optional[Callable[[int], None]] = None

    def set_tiles(self, tiles: List[str]):
        """Populates the rack with a list of tile characters."""
        self.tiles_data = list(tiles)
        self._rebuild_widgets()

    def _rebuild_widgets(self):
        # Clear existing
        while self.rack_layout.count():
            item = self.rack_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        self.tile_widgets.clear()

        for idx, letter in enumerate(self.tiles_data):
            tile_w = DraggableTileWidget(letter, rack_index=idx, parent=self)
            self.tile_widgets.append(tile_w)
            self.rack_layout.addWidget(tile_w)

    def mark_tile_placed(self, rack_index: int):
        """Hides the tile widget because it was dropped onto the board."""
        if 0 <= rack_index < len(self.tile_widgets):
            self.tile_widgets[rack_index].hide()

    def restore_tile(self, rack_index: int):
        """Unhides the tile widget because it was removed from the board."""
        if 0 <= rack_index < len(self.tile_widgets):
            self.tile_widgets[rack_index].show()

    def restore_all(self):
        """Unhides all tile widgets."""
        for tw in self.tile_widgets:
            tw.show()

    def shuffle_tiles(self):
        """Shuffles the display order of the current rack tiles."""
        if not self.tiles_data:
            return
        # We can shuffle the list and rebuild
        random.shuffle(self.tiles_data)
        self._rebuild_widgets()

    def dragEnterEvent(self, a0: Optional[QDragEnterEvent]):
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is not None and mime.hasFormat("application/x-scrabble-tile"):
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dragMoveEvent(self, a0: Optional[QDragMoveEvent]):
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is not None and mime.hasFormat("application/x-scrabble-tile"):
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dropEvent(self, a0: Optional[QDropEvent]):
        if a0 is None:
            return
        mime = a0.mimeData()
        if mime is not None and mime.hasFormat("application/x-scrabble-tile"):
            raw = mime.data("application/x-scrabble-tile").data().decode("utf-8")
            parts = raw.split(":")
            if len(parts) >= 2:
                rack_idx = int(parts[1])
                self.restore_tile(rack_idx)
                self.tile_recalled_signal.emit(rack_idx)
                if self.on_recall_callback:
                    self.on_recall_callback(rack_idx)
            a0.acceptProposedAction()
        else:
            a0.ignore()
