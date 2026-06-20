"""Reveal cards from stored, selected, or zone sources."""

from effects.base.base_effect import BaseEffect
from effects.composition.card_source_resolver import resolve_card_source


class RevealEffect(BaseEffect):
    """Reveal every card resolved by a generic card source spec."""

    def __init__(
        self,
        game,
        player,
        source,
        store_key=None,
        reveal_to=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.source = source
        self.store_key = store_key
        self.reveal_to = reveal_to

    def resolve(self):
        cards = resolve_card_source(
            {
                "source": self.source,
                "store_key": self.store_key,
            },
            self.game,
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )

        for card in cards:
            if self.reveal_to:
                print(f"{card.name} was revealed to {self.reveal_to}")
            else:
                print(f"{card.name} was revealed")

        return bool(cards)
