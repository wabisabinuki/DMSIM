"""
ターンを終了するアクションのデータを保持するクラス。
"""

from actions.base_action import BaseAction


class EndTurnAction(BaseAction):

    def __init__(self, player):
        super().__init__(player)

    def __str__(self):

        return "End Turn"
