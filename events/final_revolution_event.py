"""「ファイナル革命」「極限ファイナル革命」が使われたことを通知するイベント。

ファイナル革命の発動条件は「そのターンに（極限はこのゲーム中に）他の
『ファイナル革命』を使っていなければ」という共有カウントを参照する。
能力が解決される際にこのイベントを publish し、TurnStatsManager が
per-turn / per-game の使用回数（stat: ``final_revolutions_used``）を加算する。
"""

from events.base_event import BaseEvent


class FinalRevolutionUsedEvent(BaseEvent):

    def __init__(
        self,
        player,
        card=None,
    ):
        super().__init__()

        self.player = player
        self.card = card

    def __str__(self):
        return (
            f"FinalRevolutionUsedEvent("
            f"player={getattr(self.player, 'name', self.player)}"
            f")"
        )
