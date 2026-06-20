"""
攻撃宣言後の各処理フェーズ（ブロック選択等）へ遷移させるための内部アクションクラス。
"""

from actions.base_action import BaseAction


class ProceedToAttackStepAction(BaseAction):

    def __init__(self, player):
        super().__init__(player)

    def __str__(self):

        return "Proceed to Attack Step"
