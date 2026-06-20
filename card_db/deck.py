import json
from pathlib import Path

from card_db.factory import CardFactory


DEFAULT_CARD_DIR = Path("data/impl_cards")
DEFAULT_PLAYER1_DECK_PATH = Path("data/decks/player1_deck.json")
DEFAULT_PLAYER2_DECK_PATH = Path("data/decks/player2_deck.json")


def load_deck(
    path,
    factory,
    game=None,
    owner=None,
):
    with Path(path).open(
        "r",
        encoding="utf-8",
    ) as file:
        deck = json.load(file)

    cards = factory.create_many(
        deck.get("cards", []),
        game=game,
    )

    if owner is not None:
        for card in cards:
            card.owner = owner

    return cards


def register_player_decks(
    game,
    player1_deck_path=DEFAULT_PLAYER1_DECK_PATH,
    player2_deck_path=DEFAULT_PLAYER2_DECK_PATH,
    card_dir=DEFAULT_CARD_DIR,
    metadata_dir=None,
    factory=None,
):
    """Load separate deck files for player 1 and player 2."""

    players = list(game.state.players)
    if len(players) < 2:
        raise ValueError(
            "register_player_decks requires at least two players"
        )

    if factory is None:
        factory = CardFactory.from_dir(
            card_dir,
            metadata_directory=metadata_dir,
        )

    player, opponent = players[:2]
    player.deck.cards = load_deck(
        player1_deck_path,
        factory,
        game=game,
        owner=player,
    )
    opponent.deck.cards = load_deck(
        player2_deck_path,
        factory,
        game=game,
        owner=opponent,
    )

    return {
        player: Path(player1_deck_path),
        opponent: Path(player2_deck_path),
    }
