"""
frontend - PyQt6 Graphical User Interface package for Scrabble.
"""

from frontend.main_window import MainWindow
from frontend.board_widget import BoardWidget
from frontend.rack_widget import RackWidget
from frontend.dialogs import BlankTileDialog, ExchangeDialog, GameOverDialog, DictionarySelectorDialog

__all__ = [
    "MainWindow",
    "BoardWidget",
    "RackWidget",
    "BlankTileDialog",
    "ExchangeDialog",
    "GameOverDialog",
    "DictionarySelectorDialog",
]
