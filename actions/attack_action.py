"""
プレイヤーまたはシールドを対象とした攻撃アクションのデータを保持するクラス。
"""

from actions.base_action import BaseAction
from ui.card_display import format_card_name


class AttackAction(BaseAction):

    def __init__(
        self,
        player,
        attacker,
        target
    ):
        super().__init__(player)

        self.attacker = attacker

        self.target = target

    def __str__(self):

        return (
            f"{format_card_name(self.attacker)} "
            f"attacks "
            f"{format_card_name(self.target)}"
        )
