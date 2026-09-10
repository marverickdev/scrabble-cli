"""
backend/game.py - Main Scrabble Game State Controller & Turn Manager.
"""

from typing import List, Tuple, Optional, Dict, Any
try:
    from backend.board import Board, format_coords, parse_coords
    from backend.bag import TileBag, Rack, TILE_SCORES
    from backend.gaddag import GADDAG
    from backend.lexicon import get_default_gaddag
    from backend.movegen import generate_all_moves, ScrabbleMove
except ImportError:
    from board import Board, format_coords, parse_coords
    from bag import TileBag, Rack, TILE_SCORES
    from gaddag import GADDAG
    from lexicon import get_default_gaddag
    from movegen import generate_all_moves, ScrabbleMove


class Player:
    """
    Represents a Scrabble player (Human or AI).
    """
    def __init__(self, name: str, is_ai: bool = False):
        self.name = name
        self.is_ai = is_ai
        self.rack = Rack()
        self.score = 0

    def __repr__(self) -> str:
        return f"Player({self.name}, score={self.score}, tiles={len(self.rack)})"


class ScrabbleGame:
    """
    Main Scrabble game controller managing board state, tile bag, player turns,
    move validation, dictionary checks, AI turns, and endgame resolution.
    """
    def __init__(
        self,
        gaddag: Optional[GADDAG] = None,
        lexicon_name: str = "NASPA",
        human_name: str = "Player",
        ai_name: str = "Computer",
        seed: Optional[int] = None
    ):
        self.board = Board()
        self.bag = TileBag(seed=seed)
        self.gaddag = gaddag if gaddag is not None else get_default_gaddag()
        self.lexicon_name = lexicon_name.upper()
        self.gaddag = gaddag if gaddag is not None else get_default_gaddag(self.lexicon_name)

        self.human_player = Player(name=human_name, is_ai=False)
        self.ai_player = Player(name=ai_name, is_ai=True)

        self.current_turn = "HUMAN"
        self.consecutive_passes = 0
        self.is_game_over = False
        self.game_over_reason = ""
        self.winner: Optional[Player] = None

        self.move_history: List[Dict[str, Any]] = []
        self.last_event_message = "Welcome to Scrabble! Type 'help' for commands."

    def start_game(self) -> None:
        """
        Deals 7 tiles to each player and starts the game.
        """
        self.human_player.rack.add(self.bag.draw(7))
        self.ai_player.rack.add(self.bag.draw(7))
        self.current_turn = "HUMAN"
        self.consecutive_passes = 0
        self.is_game_over = False
        self.last_event_message = "Game started! Your turn."

    def play_human_move(
        self,
        word: str,
        coord_str: str,
        direction: str,
        blank_indices: Optional[List[int]] = None
    ) -> Tuple[bool, str]:
        """
        Validates and executes a human move.
        Returns: (success: bool, message: str)
        """
        if self.is_game_over:
            return False, "The game is already over."

        if self.current_turn != "HUMAN":
            return False, "It is not your turn."

        word = word.strip().upper()
        blank_set = set(blank_indices) if blank_indices else set()

        # 1. Parse coordinates and direction
        try:
            row, col = parse_coords(coord_str)
        except ValueError as e:
            return False, str(e)

        try:
            d = self.board._normalize_direction(direction)
        except ValueError as e:
            return False, str(e)

        # 2. Check board placement legality
        valid, reason, tiles_needed = self.board.is_valid_placement(word, row, col, d)
        if not valid:
            return False, reason

        # 3. Determine required rack tiles, accounting for blanks
        dr, dc = (0, 1) if d == "H" else (1, 0)
        required_from_rack = []

        for i in range(len(word)):
            curr_r = row + dr * i
            curr_c = col + dc * i
            if self.board.grid[curr_r][curr_c] is None:
                # Square is empty, tile comes from rack
                if i in blank_set:
                    required_from_rack.append('?')
                else:
                    required_from_rack.append(word[i])
            else:
                # Square already has a tile, cannot place blank on existing tile
                if i in blank_set:
                    return False, f"Cannot declare blank tile at existing board square {format_coords(curr_r, curr_c)}."

        # 4. Check that player possesses the required tiles
        if not self.human_player.rack.has_tiles(required_from_rack):
            return False, f"You do not have the required tiles in your rack: {required_from_rack}"

        # 5. Score move and detect all formed words (main word + cross-words)
        score, words_formed = self.board.score_move(word, row, col, d, list(blank_set))

        # 6. Validate all formed words in the dictionary
        for w in words_formed:
            if not self.gaddag.is_valid_word(w):
                return False, f"Invalid word: '{w}' is not in the dictionary!"

        # 7. Commit move to the board
        self.board.place_move(word, row, col, d, list(blank_set))

        # 8. Deduct tiles from player's rack
        self.human_player.rack.remove(required_from_rack)

        # 9. Replenish rack from tile bag
        drawn = self.bag.draw(len(required_from_rack))
        self.human_player.rack.add(drawn)

        # 10. Update score and state
        self.human_player.score += score
        self.consecutive_passes = 0

        words_summary = ", ".join(words_formed)
        msg = f"You played {word} at {format_coords(row, col)} {d} for {score} pts! ({words_summary})"
        self.last_event_message = msg
        self.move_history.append({
            "player": self.human_player.name,
            "action": "play",
            "word": word,
            "coords": format_coords(row, col),
            "dir": d,
            "score": score,
            "words_formed": words_formed
        })

        # 11. Check endgame condition (bag empty and rack empty)
        if self._check_game_over():
            return True, msg

        # 12. Advance turn
        self.current_turn = "AI"
        return True, msg

    def exchange_human_tiles(self, tiles_to_exchange: List[str]) -> Tuple[bool, str]:
        """
        Exchanges specified tiles from the human rack with the tile bag.
        Standard rule: Bag must contain at least 7 tiles.
        """
        if self.is_game_over:
            return False, "The game is already over."

        if self.current_turn != "HUMAN":
            return False, "It is not your turn."

        if len(self.bag) < 7:
            return False, "Cannot exchange tiles when fewer than 7 tiles remain in the bag."

        tiles_clean = [t.upper() for t in tiles_to_exchange]
        if not self.human_player.rack.has_tiles(tiles_clean):
            return False, "You do not have those tiles in your rack."

        # Perform exchange
        self.human_player.rack.remove(tiles_clean)
        new_tiles = self.bag.exchange(tiles_clean)
        self.human_player.rack.add(new_tiles)

        self.consecutive_passes += 1
        msg = f"You exchanged {len(tiles_clean)} tiles."
        self.last_event_message = msg
        self.move_history.append({
            "player": self.human_player.name,
            "action": "exchange",
            "count": len(tiles_clean)
        })

        if self._check_game_over():
            return True, msg

        self.current_turn = "AI"
        return True, msg

    def pass_human_turn(self) -> Tuple[bool, str]:
        """
        Passes the human turn without playing or exchanging.
        """
        if self.is_game_over:
            return False, "The game is already over."

        if self.current_turn != "HUMAN":
            return False, "It is not your turn."

        self.consecutive_passes += 1
        msg = "You passed your turn."
        self.last_event_message = msg
        self.move_history.append({
            "player": self.human_player.name,
            "action": "pass"
        })

        if self._check_game_over():
            return True, msg

        self.current_turn = "AI"
        return True, msg

    def play_ai_turn(self) -> Tuple[bool, str]:
        """
        Executes the AI's turn using movegen GADDAG search and heuristic ranking.
        """
        if self.is_game_over:
            return False, "The game is already over."

        if self.current_turn != "AI":
            return False, "It is not the AI's turn."

        # 1. Generate legal moves
        candidates = generate_all_moves(
            self.board, self.ai_player.rack.tiles, self.gaddag, top_n=10, sort_by="fitness"
        )

        if candidates:
            # Pick top heuristic candidate
            best = candidates[0]

            # Commit move to board
            score, words_formed = self.board.place_move(
                best.word, best.row, best.col, best.direction, best.blank_indices
            )

            # Deduct tiles from AI rack
            self.ai_player.rack.remove(best.tiles_played)

            # Draw replacements
            drawn = self.bag.draw(len(best.tiles_played))
            self.ai_player.rack.add(drawn)

            # Update score
            self.ai_player.score += score
            self.consecutive_passes = 0

            coord_str = format_coords(best.row, best.col)
            words_summary = ", ".join(words_formed)
            msg = f"{self.ai_player.name} played {best.word} at {coord_str} {best.direction} for {score} pts! ({words_summary})"
            self.last_event_message = msg
            self.move_history.append({
                "player": self.ai_player.name,
                "action": "play",
                "word": best.word,
                "coords": coord_str,
                "dir": best.direction,
                "score": score,
                "words_formed": words_formed
            })

        else:
            # No valid moves found
            if len(self.bag) >= 7 and len(self.ai_player.rack) > 0:
                # Exchange vowels or consonants if unbalanced, or exchange all
                to_exchange = list(self.ai_player.rack.tiles[:min(3, len(self.ai_player.rack))])
                self.ai_player.rack.remove(to_exchange)
                new_tiles = self.bag.exchange(to_exchange)
                self.ai_player.rack.add(new_tiles)

                self.consecutive_passes += 1
                msg = f"{self.ai_player.name} exchanged {len(to_exchange)} tiles."
                self.last_event_message = msg
                self.move_history.append({
                    "player": self.ai_player.name,
                    "action": "exchange",
                    "count": len(to_exchange)
                })
            else:
                self.consecutive_passes += 1
                msg = f"{self.ai_player.name} passed."
                self.last_event_message = msg
                self.move_history.append({
                    "player": self.ai_player.name,
                    "action": "pass"
                })

        if self._check_game_over():
            return True, msg

        self.current_turn = "HUMAN"
        return True, msg

    def _check_game_over(self) -> bool:
        """
        Evaluates endgame conditions and applies final score adjustments.
        """
        # Condition 1: Bag is empty and a player has emptied their rack
        if self.bag.is_empty():
            if self.human_player.rack.is_empty():
                # Human went out: gains remaining AI tile values
                ai_remaining_val = sum(TILE_SCORES.get(t, 0) for t in self.ai_player.rack.tiles)
                self.human_player.score += ai_remaining_val * 2
                self.ai_player.score -= ai_remaining_val
                self.is_game_over = True
                self.game_over_reason = f"{self.human_player.name} emptied their rack with an empty bag!"
                self._determine_winner()
                return True

            if self.ai_player.rack.is_empty():
                # AI went out: gains remaining human tile values
                human_remaining_val = sum(TILE_SCORES.get(t, 0) for t in self.human_player.rack.tiles)
                self.ai_player.score += human_remaining_val * 2
                self.human_player.score -= human_remaining_val
                self.is_game_over = True
                self.game_over_reason = f"{self.ai_player.name} emptied their rack with an empty bag!"
                self._determine_winner()
                return True

        # Condition 2: 6 consecutive passes or exchanges (3 scoreless turns each)
        if self.consecutive_passes >= 6:
            # Deduct remaining rack tile points from each player
            human_rem = sum(TILE_SCORES.get(t, 0) for t in self.human_player.rack.tiles)
            ai_rem = sum(TILE_SCORES.get(t, 0) for t in self.ai_player.rack.tiles)
            self.human_player.score -= human_rem
            self.ai_player.score -= ai_rem

            self.is_game_over = True
            self.game_over_reason = "Game ended after 6 consecutive scoreless passes."
            self._determine_winner()
            return True

        return False

    def _determine_winner(self) -> None:
        """Determines winner based on final adjusted scores."""
        if self.human_player.score > self.ai_player.score:
            self.winner = self.human_player
        elif self.ai_player.score > self.human_player.score:
            self.winner = self.ai_player
        else:
            self.winner = None  # Tie

