"""「ファイナル革命」を使ったことを記録する効果。

ファイナル革命 / 極限ファイナル革命の能力パッケージの先頭に置かれ、解決時に
FinalRevolutionUsedEvent を publish する。TurnStatsManager がこのイベントを
購読し、per-turn / per-game の使用回数（``final_revolutions_used``）を加算する。
これにより、同じプレイヤーが「ターン内に1つ」「ゲーム内に1つ（極限）」だけ
ファイナル革命を使える、という共有カウントを成立させる。
"""

from effects.base.base_effect import BaseEffect
from events.final_revolution_event import FinalRevolutionUsedEvent


class MarkFinalRevolutionUsedEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
    ):
        super().__init__()
        self.game = game
        self.player = player

    def resolve(
        self,
    ):
        player = (
            getattr(self.source_card, "owner", None)
            or self.player
        )
        self.game.event_manager.publish(
            FinalRevolutionUsedEvent(
                player=player,
                card=self.source_card,
            )
        )
        return True
