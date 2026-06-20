"""
攻撃ステップ（攻撃側・防御側の全処理）の終了を通知する内部アクションクラス。
"""

from actions.base_action import BaseAction


class FinishAttackStepAction(BaseAction):

    def __init__(self, player):
        super().__init__(player)

    def __str__(self):

        return "Finish Attack Step"
