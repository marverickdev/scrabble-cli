"""
main.py - Scrabble CLI Interactive Game Entrypoint.
"""

import sys
import time
import argparse
from backend.game import ScrabbleGame
from backend.lexicon import get_default_gaddag
from frontend.cli_renderer import CLIRenderer
from frontend.input_handler import InputHandler


def run_cli_game():
    parser = argparse.ArgumentParser(description="Scrabble CLI - Play against AI in your terminal")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI terminal colors")
    parser.add_argument("--name", type=str, default="Player", help="Your player name")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for repeatable game")
    args = parser.parse_args()

    renderer = CLIRenderer(use_color=not args.no_color)

    print(renderer.render_banner())
    print("\n  Loading dictionary, please wait...")
    t0 = time.time()
    dag = get_default_gaddag()
    print(f"  Dictionary loaded in {time.time() - t0:.2f}s.\n")

    game = ScrabbleGame(
        gaddag=dag,
        human_name=args.name,
        ai_name="Computer",
        seed=args.seed
    )
    game.start_game()

    # Initial Screen
    print(renderer.render_screen(game))

    # Main Interactive Game Loop
    while not game.is_game_over:
        if game.current_turn == "HUMAN":
            try:
                user_input = input("\n  Scrabble > ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\n  Game aborted. Thanks for playing!\n")
                return

            cmd = InputHandler.parse_command(user_input)
            action = cmd["action"]

            if action == "quit":
                print("\n  Thanks for playing Scrabble! Goodbye.\n")
                return

            elif action == "help":
                print(renderer.render_help())
                continue

            elif action == "board":
                print(renderer.render_screen(game))
                continue

            elif action == "error":
                print(renderer.color("1;31", f"\n  Error: {cmd['message']}"))
                continue

            elif action == "pass":
                game.pass_human_turn()
                print(renderer.render_screen(game))

            elif action == "exchange":
                success, msg = game.exchange_human_tiles(cmd["tiles"])
                if not success:
                    print(renderer.color("1;31", f"\n  Error: {msg}"))
                    continue
                print(renderer.render_screen(game))

            elif action == "play":
                success, msg = game.play_human_move(
                    cmd["word"], cmd["coord"], cmd["direction"], cmd["blanks"]
                )
                if not success:
                    print(renderer.color("1;31", f"\n  Error: {msg}"))
                    continue
                print(renderer.render_screen(game))

        elif game.current_turn == "AI":
            print(f"\n  {game.ai_player.name} is thinking...")
            time.sleep(0.4)
            game.play_ai_turn()
            print(renderer.render_screen(game))

    # Display Game Over Screen
    print(renderer.render_game_over(game))


if __name__ == "__main__":
    run_cli_game()

