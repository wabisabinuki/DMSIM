"""Reveal cards from a generic card source and store them."""

from effects.base.base_effect import BaseEffect
from effects.composition.card_source_resolver import resolve_card_source


class RevealCardsEffect(BaseEffect):
    """Reveal N cards without moving them, then save the revealed cards."""

    def __init__(
        self,
        game,
        player,
        source,
        store_as=None,
        as_list=False,
        optional=False,
        prompt=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.source = source
        self.store_as = store_as
        self.as_list = as_list
        self.optional = optional
        self.prompt = prompt or "Reveal the top card?"

    def resolve(self):
        if self.optional and not self._confirm():
            if self.store_as:
                self.package_context[self.store_as] = (
                    [] if self.as_list else None
                )
            return False

        cards = resolve_card_source(
            self.source,
            self.game,
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
            default_source="zone",
        )

        for card in cards:
            print(f"{card.name} was revealed")

        if self.store_as:
            self.package_context[self.store_as] = self._stored_value(cards)

        return bool(cards)

    def _stored_value(self, cards):
        if self.as_list or len(cards) != 1:
            return cards
        return cards[0]

    def _confirm(self):
        return bool(
            self.game.choice_manager.select(
                self.player,
                [True, False],
                prompt=self.prompt,
            )
        )
