"""Look at cards from a zone and optionally store them."""

from effects.base.base_effect import BaseEffect
from effects.composition.card_source_resolver import resolve_card_source


class LookEffect(BaseEffect):
    """Save the top or bottom N cards of a zone without moving them."""

    def __init__(
        self,
        game,
        player,
        zone,
        amount,
        target_player="self",
        position="top",
        store_key=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.zone = zone
        self.amount = amount
        self.target_player = target_player
        self.position = position or "top"
        self.store_key = store_key

    def resolve(self):
        cards = resolve_card_source(
            {
                "source": "zone",
                "zone": self.zone,
                "player": self.target_player,
                "amount": self.amount,
                "from": self.position,
            },
            self.game,
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )

        if self.store_key:
            self.package_context[self.store_key] = cards

        return bool(cards)
