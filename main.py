"""
DMSIMシミュレータのエントリーポイント。テスト用デッキの構築とゲームループの簡易実行デモを行います。
"""

import argparse

from core.game_controller import GameController
from core.player import Player
from cli.cli_choice_manager import CLIChoiceManager
from ui.game_presenter import CLIGamePresenter

from card_db import (
    DEFAULT_CARD_DIR,
    DEFAULT_PLAYER1_DECK_PATH,
    DEFAULT_PLAYER2_DECK_PATH,
    register_player_decks,
)

class GameExit(Exception):
    pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Run the DMSIM CLI demo."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show event, trigger, effect, and board debug logs.",
    )
    parser.add_argument(
        "--player1-deck",
        default=str(DEFAULT_PLAYER1_DECK_PATH),
        dest="player1_deck",
        help="Deck JSON file for Player1.",
    )
    parser.add_argument(
        "--player2-deck",
        default=str(DEFAULT_PLAYER2_DECK_PATH),
        dest="player2_deck",
        help="Deck JSON file for Player2.",
    )
    parser.add_argument(
        "--card-dir",
        default=str(DEFAULT_CARD_DIR),
        help="Directory containing card JSON files.",
    )
    parser.add_argument(
        "--metadata-dir",
        default=None,
        help="Optional directory containing card metadata JSON files.",
    )
    args = parser.parse_args()

    player1 = Player("Player1")
    player2 = Player("Player2")

    choice_manager = CLIChoiceManager()
    presenter = CLIGamePresenter(
        debug=args.debug,
    )
    game = GameController(
        [player1, player2],
        choice_manager,
        presenter,
    )

    register_player_decks(
        game,
        player1_deck_path=args.player1_deck,
        player2_deck_path=args.player2_deck,
        card_dir=args.card_dir,
        metadata_dir=args.metadata_dir,
    )

    game.start_game()

    try:

        for _ in range(99):

            if game.state.game_over:
                break

            game.turn_manager.run_turn()

    except GameExit:

        print("Game ended")
