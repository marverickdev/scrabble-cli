"""
frontend/main_window.py - Main PyQt6 Application Window for Scrabble.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTextEdit, QMessageBox, QFrame,
    QSplitter, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from backend.game import ScrabbleGame
from backend.lexicon import get_default_gaddag
from frontend.board_widget import BoardWidget
from frontend.rack_widget import RackWidget
from frontend.dialogs import ExchangeDialog, GameOverDialog, DictionarySelectorDialog


class AIWorker(QThread):
    """
    Background worker thread to run Gordon's GADDAG AI move generation
    and evaluation without freezing the PyQt6 GUI.
    """
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, game: ScrabbleGame):
        super().__init__()
        self.game = game

    def run(self):
        success, msg = self.game.play_ai_turn()
        self.finished_signal.emit(success, msg)


class MainWindow(QMainWindow):
    """
    Main Scrabble Application Window.
    Integrates BoardWidget, RackWidget, Action Buttons, Scoreboard, and AI Worker.
    """
    def __init__(self, lexicon: str = "NASPA", seed: Optional[int] = None):
        super().__init__()
        self.setWindowTitle("Scrabble - Human vs. AI")
        self.setMinimumSize(980, 720)

        self.lexicon_name = lexicon.upper()
        self.seed = seed
        self.ai_worker: Optional[AIWorker] = None

        # Initialize Game Engine
        self.game = ScrabbleGame(
            lexicon_name=self.lexicon_name,
            human_name="Player",
            ai_name="Computer",
            seed=self.seed
        )
        self.game.start_game()

        self._init_ui()
        self._sync_all()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # 1. Top Bar: Title, Lexicon, New Game, Bag Count, Status
        top_bar = self._create_top_bar()
        root_layout.addLayout(top_bar)

        # 2. Main Content Split: Left = Board + Rack + Controls; Right = Scoreboard + Log
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left Column: Board, Rack, Action Buttons
        left_box = QVBoxLayout()
        left_box.setSpacing(8)
        left_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.board_widget = BoardWidget(self)
        left_box.addWidget(self.board_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # Rack widget
        self.rack_widget = RackWidget(self)
        left_box.addWidget(self.rack_widget, 0, Qt.AlignmentFlag.AlignCenter)

        # Action Buttons Row
        btn_bar = self._create_action_bar()
        left_box.addLayout(btn_bar)

        content_layout.addLayout(left_box, 3)

        # Right Column: Scoreboard, Event Banner, Game Log
        right_box = self._create_sidebar()
        content_layout.addLayout(right_box, 1)

        root_layout.addLayout(content_layout)

        # Connect Drag-and-Drop Board & Rack signals
        self.board_widget.tile_placed_signal.connect(self.rack_widget.mark_tile_placed)
        self.board_widget.tile_recalled_signal.connect(self.rack_widget.restore_tile)
        self.board_widget.tile_cancelled_signal.connect(self.rack_widget.restore_tile)
        self.rack_widget.tile_recalled_signal.connect(self._on_rack_recalled_from_board)

    def _create_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(12)

        title = QLabel("SCRABBLE")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #3e2723; letter-spacing: 2px;")
        bar.addWidget(title)

        bar.addSpacing(16)

        # Lexicon Selector
        lex_lbl = QLabel("Dictionary:")
        lex_lbl.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        bar.addWidget(lex_lbl)

        self.lex_combo = QComboBox()
        self.lex_combo.addItems(["NASPA (NWL23 - North American)", "CSW24 (Collins International)"])
        if "CSW" in self.lexicon_name:
            self.lex_combo.setCurrentIndex(1)
        else:
            self.lex_combo.setCurrentIndex(0)
        self.lex_combo.currentIndexChanged.connect(self._on_lexicon_combo_changed)
        bar.addWidget(self.lex_combo)

        # New Game Button
        self.new_game_btn = QPushButton("New Game")
        self.new_game_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d4037;
                color: white;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3e2723;
            }
        """)
        self.new_game_btn.clicked.connect(self._on_new_game_clicked)
        bar.addWidget(self.new_game_btn)

        bar.addStretch()

        # Bag count indicator
        self.bag_label = QLabel("Bag: 86 tiles")
        self.bag_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.bag_label.setStyleSheet("color: #4e342e; padding: 4px 8px; background: #efebe9; border-radius: 4px;")
        bar.addWidget(self.bag_label)

        # Turn indicator
        self.turn_label = QLabel("Turn: Your Turn")
        self.turn_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.turn_label.setStyleSheet("color: white; background: #2e7d32; padding: 4px 10px; border-radius: 4px;")
        bar.addWidget(self.turn_label)

        return bar

    def _create_action_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(10)
        bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Play Turn Button
        self.play_btn = QPushButton("Play Turn")
        self.play_btn.setFixedSize(110, 38)
        self.play_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
            QPushButton:disabled {
                background-color: #a5d6a7;
            }
        """)
        self.play_btn.clicked.connect(self._on_play_turn_clicked)
        bar.addWidget(self.play_btn)

        # Exchange Button
        self.exchange_btn = QPushButton("Exchange")
        self.exchange_btn.setFixedSize(100, 38)
        self.exchange_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.exchange_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #90caf9;
            }
        """)
        self.exchange_btn.clicked.connect(self._on_exchange_clicked)
        bar.addWidget(self.exchange_btn)

        # Pass Button
        self.pass_btn = QPushButton("Pass")
        self.pass_btn.setFixedSize(90, 38)
        self.pass_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.pass_btn.setStyleSheet("""
            QPushButton {
                background-color: #e65100;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #bf360c;
            }
            QPushButton:disabled {
                background-color: #ffcc80;
            }
        """)
        self.pass_btn.clicked.connect(self._on_pass_clicked)
        bar.addWidget(self.pass_btn)

        # Recall Button
        self.recall_btn = QPushButton("Recall")
        self.recall_btn.setFixedSize(90, 38)
        self.recall_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.recall_btn.setStyleSheet("""
            QPushButton {
                background-color: #616161;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #424242;
            }
        """)
        self.recall_btn.clicked.connect(self._on_recall_clicked)
        bar.addWidget(self.recall_btn)

        # Shuffle Button
        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.setFixedSize(90, 38)
        self.shuffle_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.shuffle_btn.setStyleSheet("""
            QPushButton {
                background-color: #795548;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4e342e;
            }
        """)
        self.shuffle_btn.clicked.connect(self._on_shuffle_clicked)
        bar.addWidget(self.shuffle_btn)

        return bar

    def _create_sidebar(self) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(10)

        # Score Cards
        score_card = QFrame()
        score_card.setStyleSheet("""
            QFrame {
                background-color: #fdfbf7;
                border: 2px solid #d7ccc8;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        card_layout = QVBoxLayout(score_card)

        score_title = QLabel("SCOREBOARD")
        score_title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        score_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_title.setStyleSheet("color: #4e342e;")
        card_layout.addWidget(score_title)

        # Human Score
        h_row = QHBoxLayout()
        self.human_name_lbl = QLabel("You (Player):")
        self.human_name_lbl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.human_score_lbl = QLabel("0")
        self.human_score_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.human_score_lbl.setStyleSheet("color: #2e7d32;")
        h_row.addWidget(self.human_name_lbl)
        h_row.addStretch()
        h_row.addWidget(self.human_score_lbl)
        card_layout.addLayout(h_row)

        # AI Score
        a_row = QHBoxLayout()
        self.ai_name_lbl = QLabel("Computer (AI):")
        self.ai_name_lbl.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.ai_score_lbl = QLabel("0")
        self.ai_score_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.ai_score_lbl.setStyleSheet("color: #c62828;")
        a_row.addWidget(self.ai_name_lbl)
        a_row.addStretch()
        a_row.addWidget(self.ai_score_lbl)
        card_layout.addLayout(a_row)

        box.addWidget(score_card)

        # Event Message Box
        self.status_box = QLabel("Welcome to Scrabble! Drag tiles onto the board to play.")
        self.status_box.setWordWrap(True)
        self.status_box.setStyleSheet("""
            background-color: #e8f5e9;
            color: #1b5e20;
            font-weight: bold;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid #c8e6c9;
        """)
        box.addWidget(self.status_box)

        # Move History / Game Log
        log_title = QLabel("GAME LOG")
        log_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        log_title.setStyleSheet("color: #4e342e; margin-top: 6px;")
        box.addWidget(log_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #cfd8dc;
                border-radius: 4px;
                font-family: monospace;
                font-size: 11px;
                color: #263238;
            }
        """)
        box.addWidget(self.log_text, 1)

        return box

    def _sync_all(self):
        """Synchronizes GUI widgets with backend game state."""
        # 1. Sync board
        self.board_widget.sync_board_state(self.game.board)

        # 2. Sync rack
        self.rack_widget.set_tiles(self.game.human_player.rack.tiles)

        # 3. Sync scores
        self.human_score_lbl.setText(str(self.game.human_player.score))
        self.ai_score_lbl.setText(str(self.game.ai_player.score))
        self.bag_label.setText(f"Bag: {len(self.game.bag)} tiles")

        # 4. Turn Status
        if self.game.is_game_over:
            self.turn_label.setText("Turn: Game Over")
            self.turn_label.setStyleSheet("color: white; background: #616161; padding: 4px 10px; border-radius: 4px;")
            self._set_buttons_enabled(False)
        elif self.game.current_turn == "HUMAN":
            self.turn_label.setText("Turn: Your Turn")
            self.turn_label.setStyleSheet("color: white; background: #2e7d32; padding: 4px 10px; border-radius: 4px;")
            self._set_buttons_enabled(True)
        else:
            self.turn_label.setText("Turn: Computer Thinking...")
            self.turn_label.setStyleSheet("color: white; background: #f57f17; padding: 4px 10px; border-radius: 4px;")
            self._set_buttons_enabled(False)

        # 5. Status message
        if self.game.last_event_message:
            self.status_box.setText(self.game.last_event_message)

    def _set_buttons_enabled(self, enabled: bool):
        self.play_btn.setEnabled(enabled)
        self.exchange_btn.setEnabled(enabled)
        self.pass_btn.setEnabled(enabled)
        self.recall_btn.setEnabled(enabled)
        self.shuffle_btn.setEnabled(enabled)

    def _log_event(self, text: str):
        self.log_text.append(text)

    def _on_play_turn_clicked(self):
        if self.game.current_turn != "HUMAN" or self.game.is_game_over:
            return

        # Reconstruct word from uncommitted board tiles
        move_info, err = self.board_widget.get_pending_move(self.game.board)
        if err is not None or move_info is None:
            QMessageBox.warning(self, "Invalid Placement", err or "Invalid move")
            return

        word, coord_str, direction, blank_indices = move_info

        # Execute move in backend
        success, msg = self.game.play_human_move(word, coord_str, direction, blank_indices)
        if not success:
            QMessageBox.warning(self, "Illegal Move", msg)
            return

        # Move was successful!
        self._log_event(f"▶ You: {msg}")
        self._sync_all()

        if self._check_and_show_game_over():
            return

        # Trigger AI turn
        self._start_ai_turn()

    def _on_exchange_clicked(self):
        if self.game.current_turn != "HUMAN" or self.game.is_game_over:
            return

        if len(self.game.bag) < 7:
            QMessageBox.warning(
                self, "Cannot Exchange",
                "Cannot exchange tiles when fewer than 7 tiles remain in the bag."
            )
            return

        # Recall any tiles on the board first
        self.board_widget.recall_all_pending()
        self.rack_widget.restore_all()

        dialog = ExchangeDialog(self.game.human_player.rack.tiles, len(self.game.bag), self)
        if dialog.exec():
            selected = dialog.get_selected_tiles()
            success, msg = self.game.exchange_human_tiles(selected)
            if success:
                self._log_event(f"▶ You: {msg}")
                self._sync_all()
                if not self._check_and_show_game_over():
                    self._start_ai_turn()
            else:
                QMessageBox.warning(self, "Exchange Failed", msg)

    def _on_pass_clicked(self):
        if self.game.current_turn != "HUMAN" or self.game.is_game_over:
            return

        reply = QMessageBox.question(
            self, "Pass Turn", "Are you sure you want to pass your turn?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.board_widget.recall_all_pending()
            self.rack_widget.restore_all()

            success, msg = self.game.pass_human_turn()
            self._log_event(f"▶ You: {msg}")
            self._sync_all()

            if not self._check_and_show_game_over():
                self._start_ai_turn()

    def _on_recall_clicked(self):
        self.board_widget.recall_all_pending()
        self.rack_widget.restore_all()

    def _on_shuffle_clicked(self):
        self.board_widget.recall_all_pending()
        self.rack_widget.shuffle_tiles()

    def _on_rack_recalled_from_board(self, rack_idx: int):
        # Remove from board pending placements if dropped back to rack
        coords = list(self.board_widget.pending_placements.keys())
        for r, c in coords:
            if self.board_widget.pending_placements[r, c]["rack_index"] == rack_idx:
                del self.board_widget.pending_placements[r, c]
                self.board_widget.cells[r][c].uncommitted_tile = None
                self.board_widget.cells[r][c].render_state()

    def _start_ai_turn(self):
        self._set_buttons_enabled(False)
        self.turn_label.setText("Turn: Computer Thinking...")
        self.turn_label.setStyleSheet("color: white; background: #f57f17; padding: 4px 10px; border-radius: 4px;")
        self.status_box.setText("Computer is thinking...")

        self.ai_worker = AIWorker(self.game)
        self.ai_worker.finished_signal.connect(self._on_ai_turn_finished)
        self.ai_worker.start()

    def _on_ai_turn_finished(self, success: bool, msg: str):
        self._log_event(f"🤖 Computer: {msg}")
        self._sync_all()
        self._check_and_show_game_over()

    def _check_and_show_game_over(self) -> bool:
        if self.game.is_game_over:
            self._sync_all()
            dialog = GameOverDialog(
                self.game.human_player.name,
                self.game.human_player.score,
                self.game.ai_player.name,
                self.game.ai_player.score,
                self.game.game_over_reason,
                self
            )
            dialog.exec()
            return True
        return False

    def _on_lexicon_combo_changed(self, index: int):
        new_lex = "CSW24" if index == 1 else "NASPA"
        if new_lex != self.lexicon_name:
            reply = QMessageBox.question(
                self, "Switch Dictionary",
                f"Switching to {new_lex} will start a New Game. Do you wish to proceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.lexicon_name = new_lex
                self._start_new_game()
            else:
                # Revert selection
                self.lex_combo.blockSignals(True)
                self.lex_combo.setCurrentIndex(1 if "CSW" in self.lexicon_name else 0)
                self.lex_combo.blockSignals(False)

    def _on_new_game_clicked(self):
        reply = QMessageBox.question(
            self, "New Game", "Are you sure you want to start a new game?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._start_new_game()

    def _start_new_game(self):
        self.game = ScrabbleGame(
            lexicon_name=self.lexicon_name,
            human_name="Player",
            ai_name="Computer",
            seed=self.seed
        )
        self.game.start_game()
        self.log_text.clear()
        self._log_event(f"=== New Game Started ({self.lexicon_name} Dictionary) ===")
        self._sync_all()

