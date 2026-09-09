"""
frontend/input_handler.py - Command parser for user input in Scrabble CLI.
"""

from typing import Dict, Any, List, Tuple


class InputHandler:
    """
    Parses and normalizes CLI input strings from the user.
    """
    @staticmethod
    def parse_command(user_input: str) -> Dict[str, Any]:
        """
        Parses raw user input into a command dictionary.

        Possible actions:
        - {"action": "play", "word": str, "coord": str, "direction": str, "blanks": List[int]}
        - {"action": "exchange", "tiles": List[str]}
        - {"action": "pass"}
        - {"action": "board"}
        - {"action": "help"}
        - {"action": "quit"}
        - {"action": "error", "message": str}
        """
        raw = user_input.strip()
        if not raw:
            return {"action": "error", "message": "Please enter a command. Type 'help' for options."}

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            return {"action": "quit"}

        if cmd in ("help", "?", "commands"):
            return {"action": "help"}

        if cmd in ("pass", "skip"):
            return {"action": "pass"}

        if cmd in ("board", "b", "show"):
            return {"action": "board"}

        if cmd in ("exchange", "swap", "ex"):
            if len(parts) < 2:
                return {
                    "action": "error",
                    "message": "Usage: exchange <TILES> (e.g., 'exchange QZ' or 'exchange EEE')"
                }
            # Gather all tiles after the command keyword
            tiles_str = "".join(parts[1:]).upper()
            tiles = [t for t in tiles_str if t.isalpha() or t == '?']
            if not tiles:
                return {
                    "action": "error",
                    "message": "No valid letters specified to exchange."
                }
            return {"action": "exchange", "tiles": tiles}

        if cmd in ("play", "p"):
            if len(parts) < 4:
                return {
                    "action": "error",
                    "message": "Usage: play <WORD> <COORD> <H|V> (e.g., 'play CAT H8 H')"
                }

            raw_word = parts[1]
            coord_str = parts[2].upper()
            direction = parts[3].upper()

            if direction not in ("H", "V", "ACROSS", "DOWN"):
                return {
                    "action": "error",
                    "message": f"Invalid direction '{direction}'. Use 'H' (across) or 'V' (down)."
                }

            # Detect blanks from lowercase letters (standard Scrabble notation: e.g. 'cAT' -> blank is 'C')
            clean_word = ""
            blank_indices: List[int] = []

            for idx, char in enumerate(raw_word):
                if char.islower():
                    blank_indices.append(idx)
                    clean_word += char.upper()
                elif char.isupper():
                    clean_word += char
                else:
                    return {
                        "action": "error",
                        "message": f"Invalid character '{char}' in word. Only letters are allowed."
                    }

            if len(clean_word) < 2:
                return {
                    "action": "error",
                    "message": "Words must be at least 2 letters long."
                }

            return {
                "action": "play",
                "word": clean_word,
                "coord": coord_str,
                "direction": direction,
                "blanks": blank_indices
            }

        return {
            "action": "error",
            "message": f"Unknown command: '{cmd}'. Type 'help' for a list of valid commands."
        }

