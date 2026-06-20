"""
シールド・トリガーなどによってコストを支払わずにカードを即時使用する効果。
"""

from effects.base.base_effect import (
    BaseEffect
)

from core.protocols import PlayableContext


class UseCardEffect(
    BaseEffect
):

    def __init__(
        self,
        card,
        player,
        ignore_cost,
        game: PlayableContext,
    ):

        super().__init__()

        self.card = card

        self.player = player

        self.ignore_cost = (
            ignore_cost
        )

        self.game = game

    def resolve(self):

        self.card.use(
            self.game,
            self.player,
            self.ignore_cost,
        )
