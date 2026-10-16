"""
main.py - Scrabble PyQt6 GUI Application Entrypoint.
"""

import sys
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from frontend.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(description="Scrabble - Drag-and-Drop GUI vs AI")
    parser.add_argument(
        "--lexicon", "--dict",
        type=str,
        default="NASPA",
        help="Tournament lexicon: 'NASPA' (North American NWL23) or 'CSW24' (Collins International)"
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatable game")
    args = parser.parse_args()

    # Determine initial lexicon
    selected_lexicon = "CSW24" if "CSW" in args.lexicon.upper() else "NASPA"

    # Set up high-DPI scaling attributes if available
    app = QApplication(sys.argv)
    app.setApplicationName("Scrabble")
    app.setStyle("Fusion")

    window = MainWindow(lexicon=selected_lexicon, seed=args.seed)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
