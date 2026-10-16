"""
frontend/dialogs.py - Interactive PyQt6 dialogs for Scrabble game actions.
"""

from typing import List, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QCheckBox, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class BlankTileDialog(QDialog):
    """
    Modal dialog prompting the player to designate a letter (A-Z)
    for a blank ('?') tile dropped on the board.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Designate Blank Tile")
        self.setModal(True)
        self.setFixedSize(360, 300)
        self.selected_letter: Optional[str] = None

        layout = QVBoxLayout(self)

        title = QLabel("Select a letter for your Blank Tile:")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(6)
        letters = [chr(ord('A') + i) for i in range(26)]

        for idx, letter in enumerate(letters):
            r = idx // 7
            c = idx % 7
            btn = QPushButton(letter)
            btn.setFixedSize(40, 40)
            btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f7ecd5;
                    border: 2px solid #b89d79;
                    border-radius: 4px;
                    color: #2b1d0c;
                }
                QPushButton:hover {
                    background-color: #dfba73;
                    border-color: #8c6721;
                }
            """)
            btn.clicked.connect(lambda checked, l=letter: self._choose_letter(l))
            grid.addWidget(btn, r, c)

        layout.addLayout(grid)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _choose_letter(self, letter: str):
        self.selected_letter = letter
        self.accept()


class ExchangeDialog(QDialog):
    """
    Modal dialog allowing the player to select which rack tiles to exchange with the bag.
    """
    def __init__(self, rack_tiles: List[str], bag_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exchange Tiles")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.rack_tiles = list(rack_tiles)
        self.bag_count = bag_count
        self.selected_indices: List[int] = []

        layout = QVBoxLayout(self)

        header = QLabel("Select the tiles you wish to exchange:")
        header.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(header)

        bag_label = QLabel(f"Tiles remaining in bag: {bag_count} (min 7 required to exchange)")
        bag_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(bag_label)

        # Tile selection row
        self.checkboxes: List[QCheckBox] = []
        tiles_layout = QHBoxLayout()
        for idx, tile in enumerate(self.rack_tiles):
            box = QVBoxLayout()
            label = QLabel(tile if tile != '?' else "★ Blank")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            label.setFixedSize(42, 42)
            label.setStyleSheet("""
                background-color: #faeccf;
                border: 2px solid #a68453;
                border-radius: 4px;
                color: #2b1d0c;
            """)

            cb = QCheckBox()
            cb.setStyleSheet("margin-left: 12px;")
            self.checkboxes.append(cb)

            box.addWidget(label)
            box.addWidget(cb)
            tiles_layout.addLayout(box)

        layout.addLayout(tiles_layout)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("Exchange Selected")
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.confirm_btn)
        layout.addLayout(btn_layout)

    def _on_confirm(self):
        self.selected_indices = [
            i for i, cb in enumerate(self.checkboxes) if cb.isChecked()
        ]
        if not self.selected_indices:
            QMessageBox.warning(self, "No Tiles Selected", "Please select at least one tile to exchange.")
            return
        if self.bag_count < 7:
            QMessageBox.warning(
                self, "Insufficient Bag Tiles",
                "Cannot exchange tiles when fewer than 7 tiles remain in the bag."
            )
            return
        self.accept()

    def get_selected_tiles(self) -> List[str]:
        return [self.rack_tiles[i] for i in self.selected_indices]


class DictionarySelectorDialog(QDialog):
    """
    Modal dialog allowing the player to select the tournament lexicon
    (NASPA NWL23 vs CSW24) when starting a new game.
    """
    def __init__(self, current_lexicon: str = "NASPA", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tournament Dictionary")
        self.setModal(True)
        self.setFixedWidth(420)
        self.selected_lexicon = current_lexicon.upper()

        layout = QVBoxLayout(self)

        title = QLabel("Select Scrabble Tournament Lexicon")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Choose the official word list for gameplay and AI generation:")
        subtitle.setStyleSheet("color: #555; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        self.btn_group = QButtonGroup(self)

        # NASPA Option
        self.naspa_radio = QRadioButton("NASPA - North American (NWL23)")
        self.naspa_radio.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        naspa_desc = QLabel("  Official North American lexicon with 196,601 valid words.\n  Used in USA and Canada tournament play.")
        naspa_desc.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 10px;")

        # CSW24 Option
        self.csw_radio = QRadioButton("CSW24 - Collins International (WESPA)")
        self.csw_radio.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        csw_desc = QLabel("  International tournament lexicon with 279,139 valid words.\n  Includes international words (e.g., ZO, CH, QI).")
        csw_desc.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 10px;")

        self.btn_group.addButton(self.naspa_radio, 1)
        self.btn_group.addButton(self.csw_radio, 2)

        if "CSW" in self.selected_lexicon:
            self.csw_radio.setChecked(True)
        else:
            self.naspa_radio.setChecked(True)

        layout.addWidget(self.naspa_radio)
        layout.addWidget(naspa_desc)
        layout.addWidget(self.csw_radio)
        layout.addWidget(csw_desc)

        # Buttons
        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("Select Lexicon")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                font-weight: bold;
                padding: 6px 14px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0d47a1;
            }
        """)
        confirm_btn.clicked.connect(self._on_confirm)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _on_confirm(self):
        if self.csw_radio.isChecked():
            self.selected_lexicon = "CSW24"
        else:
            self.selected_lexicon = "NASPA"
        self.accept()


class GameOverDialog(QDialog):
    """
    Modal dialog displayed when the game finishes.
    """
    def __init__(self, human_name: str, human_score: int, ai_name: str, ai_score: int, reason: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Game Over!")
        self.setModal(True)
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)

        if human_score > ai_score:
            outcome = "🏆 Victory! You Win!"
            color = "#2e7d32"
        elif ai_score > human_score:
            outcome = f"🤖 {ai_name} Wins!"
            color = "#c62828"
        else:
            outcome = "🤝 It's a Tie!"
            color = "#e65100"

        title = QLabel(outcome)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {color}; margin-top: 8px;")
        layout.addWidget(title)

        reason_label = QLabel(reason)
        reason_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reason_label.setStyleSheet("color: #555; font-style: italic; margin-bottom: 12px;")
        layout.addWidget(reason_label)

        # Scores box
        scores_layout = QHBoxLayout()
        h_box = QVBoxLayout()
        h_name = QLabel(human_name)
        h_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_name.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        h_val = QLabel(str(human_score))
        h_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_val.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        h_box.addWidget(h_name)
        h_box.addWidget(h_val)

        divider = QLabel("—")
        divider.setAlignment(Qt.AlignmentFlag.AlignCenter)
        divider.setFont(QFont("Arial", 20))

        a_box = QVBoxLayout()
        a_name = QLabel(ai_name)
        a_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        a_name.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        a_val = QLabel(str(ai_score))
        a_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        a_val.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        a_box.addWidget(a_name)
        a_box.addWidget(a_val)

        scores_layout.addLayout(h_box)
        scores_layout.addWidget(divider)
        scores_layout.addLayout(a_box)
        layout.addLayout(scores_layout)

        # Close button
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Close")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

