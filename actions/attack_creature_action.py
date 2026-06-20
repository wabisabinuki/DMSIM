"""
相手クリーチャーを対象とした攻撃アクションのデータを保持するクラス。
"""

from actions.base_action import (
    BaseAction
)


class AttackCreatureAction(
    BaseAction
):

    def __init__(
        self,
        player,
        attacker,
        target_creature,
    ):

        super().__init__(player)

        self.attacker = attacker

        self.target_creature = (
            target_creature
        )
