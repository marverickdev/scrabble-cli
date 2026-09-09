"""
bag.py - Standard Scrabble Tile Bag and Player Rack Management.
"""

import random
from typing import List, Optional

# Standard English Scrabble letter values
TILE_SCORES = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1,
    'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8,
    'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1,
    'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1,
    'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4,
    'Z': 10, '?': 0
}

# Standard English / NASPA 100-tile distribution
TILE_DISTRIBUTION = (
    ['?'] * 2 +
    ['E'] * 12 +
    ['A'] * 9 +
    ['I'] * 9 +
    ['O'] * 8 +
    ['N'] * 6 +
    ['R'] * 6 +
    ['T'] * 6 +
    ['L'] * 4 +
    ['S'] * 4 +
    ['U'] * 4 +
    ['D'] * 4 +
    ['G'] * 3 +
    ['B'] * 2 +
    ['C'] * 2 +
    ['M'] * 2 +
    ['P'] * 2 +
    ['F'] * 2 +
    ['H'] * 2 +
    ['V'] * 2 +
    ['W'] * 2 +
    ['Y'] * 2 +
    ['K'] * 1 +
    ['J'] * 1 +
    ['X'] * 1 +
    ['Q'] * 1 +
    ['Z'] * 1
)


class TileBag:
    """
    Manages the 100 Scrabble tiles, drawing, and exchanging tiles.
    """
    def __init__(self, seed: Optional[int] = None):
        self._random = random.Random(seed)
        self.tiles: List[str] = list(TILE_DISTRIBUTION)
        self._random.shuffle(self.tiles)

    def draw(self, count: int = 7) -> List[str]:
        """
        Draws up to `count` tiles from the bag without replacement.
        """
        drawn = []
        for _ in range(min(count, len(self.tiles))):
            drawn.append(self.tiles.pop())
        return drawn

    def exchange(self, tiles_to_return: List[str]) -> List[str]:
        """
        Exchanges tiles with the bag according to standard rules:
        Tiles are returned to the bag, shuffled, and the same number of tiles are drawn.
        Standard rule: Can only exchange if bag has at least 7 tiles.
        """
        if len(self.tiles) < 7:
            raise ValueError("Cannot exchange tiles when bag has fewer than 7 tiles.")
        if len(tiles_to_return) > len(self.tiles):
            raise ValueError("Cannot exchange more tiles than remain in the bag.")

        drawn = self.draw(len(tiles_to_return))
        self.tiles.extend(tiles_to_return)
        self._random.shuffle(self.tiles)
        return drawn

    def remaining(self) -> int:
        """Returns the number of tiles left in the bag."""
        return len(self.tiles)

    def is_empty(self) -> bool:
        """Returns True if no tiles remain in the bag."""
        return len(self.tiles) == 0

    def __len__(self) -> int:
        return len(self.tiles)


class Rack:
    """
    Encapsulates a player's tile rack (typically 7 tiles).
    """
    def __init__(self, initial_tiles: Optional[List[str]] = None):
        self.tiles: List[str] = list(initial_tiles) if initial_tiles else []

    def add(self, new_tiles: List[str]) -> None:
        """Adds drawn tiles to the rack."""
        self.tiles.extend(new_tiles)

    def remove(self, tiles_to_remove: List[str]) -> None:
        """
        Removes specified tiles from the rack.
        Raises ValueError if any tile is not present.
        """
        temp = self.tiles.copy()
        for t in tiles_to_remove:
            if t in temp:
                temp.remove(t)
            else:
                raise ValueError(f"Tile '{t}' is not in the rack.")
        self.tiles = temp

    def has_tiles(self, needed_tiles: List[str]) -> bool:
        """
        Checks whether the rack contains the required tiles.
        Supports blanks: if a letter is not found in rack, a '?' can be used.
        """
        available = self.tiles.copy()
        for t in needed_tiles:
            if t in available:
                available.remove(t)
            elif '?' in available:
                available.remove('?')
            else:
                return False
        return True

    def count(self) -> int:
        """Returns number of tiles in the rack."""
        return len(self.tiles)

    def is_empty(self) -> bool:
        return len(self.tiles) == 0

    def display(self, color: bool = True) -> str:
        """
        Returns a formatted CLI representation of the rack with points.
        Example: [ A:1  E:1  R:1  T:1  S:1  B:3  ?:0 ]
        """
        parts = []
        for t in sorted(self.tiles):
            score = TILE_SCORES.get(t, 0)
            if color:
                parts.append(f"\033[1;37;44m {t} \033[0m\033[90m:{score}\033[0m")
            else:
                parts.append(f"{t}:{score}")
        return "[ " + "  ".join(parts) + " ]"

    def __iter__(self):
        return iter(self.tiles)

    def __len__(self) -> int:
        return len(self.tiles)

    def __repr__(self) -> str:
        return f"Rack({self.tiles})"

