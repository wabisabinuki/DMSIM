"""
複数のクリーチャーを同時に破壊するアクションのデータを保持するクラス。
"""

from actions.base_action import (
    BaseAction
)


class DestroyMultipleAction(BaseAction):

    def __init__(
        self,
        player,
        cards,
    ):

        super().__init__(player)

        self.cards = list(cards)
