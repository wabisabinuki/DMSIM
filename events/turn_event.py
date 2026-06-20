"""
ターンの開始または終了を通知するイベントクラス。
"""

from events.base_event import BaseEvent


class TurnStartEvent(BaseEvent):

    def __init__(self, player):
        super().__init__()

        self.player = player


class TurnEndEvent(BaseEvent):

    def __init__(self, player):
        super().__init__()

        self.player = player
