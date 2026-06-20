"""
クリーチャーを破壊するアクションのデータを保持するクラス。
"""

from actions.base_action import (
    BaseAction
)


class DestroyAction(BaseAction):

    def __init__(
        self,
        player,
        target_card,
    ):

        super().__init__(player)

        self.target_card = target_card
