"""Count cards from a generic source and store the result."""

from core.card_filter_evaluator import matches_card_filter_dsl_or_legacy
from effects.base.base_effect import BaseEffect
from effects.composition.card_source_resolver import resolve_card_source


class CountEffect(BaseEffect):
    """Count source cards matching a condition and save the count."""

    def __init__(
        self,
        game,
        player,
        source,
        condition,
        count_key,
        store_key=None,
        zone=None,
        target_player="self",
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.source = source
        self.condition = condition or {}
        self.count_key = count_key
        self.store_key = store_key
        self.zone = zone
        self.target_player = target_player
        if self.count_key is None:
            raise ValueError("count requires count_key")

    def resolve(self):
        cards = resolve_card_source(
            {
                "source": self.source,
                "store_key": self.store_key,
                "zone": self.zone,
                "player": self.target_player,
            },
            self.game,
            self.player,
            source_card=self.source_card,
            package_context=self.package_context,
        )
        context = {
            **self.package_context,
            "player": self.player,
            "controller": self.player,
            "source_card": self.source_card,
        }
        count = sum(
            1
            for card in cards
            if matches_card_filter_dsl_or_legacy(
                self.game,
                card,
                self.condition,
                context=context,
            )
        )
        self.package_context[self.count_key] = count
        return True
