"""
frontend/cli_renderer.py - Terminal UI renderer for Scrabble CLI.
Renders the ANSI board, scoreboard, player rack, and game announcements.
"""

from typing import Optional, Any


class CLIRenderer:
    """
    Renders terminal screens, ANSI boards, player racks, and scoreboards.
    """
    def __init__(self, use_color: bool = True):
        self.use_color = use_color

    def color(self, code: str, text: str) -> str:
        if not self.use_color:
            return text
        return f"\033[{code}m{text}\033[0m"

    def render_banner(self) -> str:
        banner = """
  ╔═══════════════════════════════════════════════════════════╗
  ║           S  C  R  A  B  B  L  E     C  L  I            ║
  ╚═══════════════════════════════════════════════════════════╝"""
        return self.color("1;36", banner)

    def render_scoreboard(self, game: Any) -> str:
        h_name = game.human_player.name.upper()
        h_score = f"{game.human_player.score} pts"
        a_name = game.ai_player.name.upper()
        a_score = f"{game.ai_player.score} pts"

        turn_str = "YOUR TURN" if game.current_turn == "HUMAN" else f"{a_name}'S TURN"
        bag_str = f"{len(game.bag)} tiles left"

        p1 = f"{h_name}: {h_score}".ljust(26)
        p2 = f"{a_name}: {a_score}".ljust(26)

        t_info = f"TURN: {turn_str}".ljust(26)
        b_info = f"BAG: {bag_str}".ljust(26)

        lines = [
            "  ┌" + "─" * 59 + "┐",
            f"  │  {self.color('1;32', p1)} {self.color('1;35', p2)} │",
            f"  │  {self.color('1;33', t_info)} {self.color('90', b_info)} │",
            "  └" + "─" * 59 + "┘"
        ]
        return "\n".join(lines)

    def render_rack(self, game: Any) -> str:
        rack_str = game.human_player.rack.display(color=self.use_color)
        title = self.color("1;37", "YOUR RACK:")
        return f"  {title} {rack_str}"

    def render_status(self, message: str) -> str:
        label = self.color("1;33", "STATUS:")
        return f"  {label} {message}"

    def render_screen(self, game: Any, custom_message: Optional[str] = None) -> str:
        """
        Assembles the complete game view:
        Banner -> Scoreboard -> Board -> Rack -> Status
        """
        output = []
        output.append(self.render_banner())
        output.append(self.render_scoreboard(game))
        output.append("")
        output.append(game.board.render(color=self.use_color))
        output.append("")
        output.append(self.render_rack(game))

        status_msg = custom_message if custom_message is not None else game.last_event_message
        if status_msg:
            output.append("")
            output.append(self.render_status(status_msg))

        output.append("")
        return "\n".join(output)

    def render_help(self) -> str:
        help_text = """
  COMMANDS GUIDE:
  ─────────────────────────────────────────────────────────────
  play <WORD> <COORD> <H|V>
      Places a word on the board.
      - COORD: Row and column (e.g. 'H8', '8H', 'C3', '12F').
      - H|V: Direction ('H' = across, 'V' = down).
      - Blank tiles: Use lowercase letters for blanks!
        Example: 'play cAT H8 H' (plays blank as 'C', and 'A','T' from rack).

  exchange <TILES>
      Returns tiles to bag and draws new ones.
      - Allowed only when at least 7 tiles remain in the bag.
      - Example: 'exchange QZ' or 'exchange UUU'.

  pass
      Passes your turn. 6 consecutive passes ends the game.

  board
      Re-prints the current game board and scores.

  help
      Shows this command guide.

  quit / exit
      Quits the game.
  ─────────────────────────────────────────────────────────────"""
        return self.color("36", help_text)

    def render_game_over(self, game: Any) -> str:
        banner = self.color("1;31", "\n  ════════════════════════ G A M E   O V E R ════════════════════════")
        reason = self.color("33", f"  Reason: {game.game_over_reason}")
        scores = (
            f"  Final Scores:\n"
            f"    {game.human_player.name}: {game.human_player.score} pts\n"
            f"    {game.ai_player.name}: {game.ai_player.score} pts"
        )
        if game.winner:
            w_msg = self.color("1;32", f"  WINNER: {game.winner.name.upper()}!")
        else:
            w_msg = self.color("1;33", "  RESULT: IT'S A TIE!")

        return f"{banner}\n{reason}\n\n{scores}\n\n{w_msg}\n  ═══════════════════════════════════════════════════════════════════\n"

