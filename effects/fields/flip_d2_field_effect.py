"""D2フィールドを「上下逆さま」にする（Dスイッチ）Effect。

Dスイッチの共通部分。発生源の D2フィールド（``source_card``）をゲーム中で1度だけ
上下逆さまにする。「上下逆さまにする」こと自体はゲーム動作に影響しない表示上の状態だが、
1度使うと再び使えなくなる目印として ``d_switch_flipped`` を立てる。

「上下逆さまにしてもよい」は任意のため、プレイヤーが断れば反転せず、後続（そうしたら …）
は実行されない。反転したかどうかを resolve() の真偽で返し、後続効果に
``connector: "then"`` を付けることで「反転した時だけ後続を使う」を表現する。
"""

from effects.base.base_effect import BaseEffect
from zones.zone_type import ZoneType


class FlipD2FieldEffect(BaseEffect):

    def __init__(
        self,
        game,
        player,
        prompt=None,
    ):
        super().__init__()
        self.game = game
        self.player = player
        self.prompt = (
            prompt
            or "このD2フィールドを上下逆さまにしますか？"
        )

    def can_attempt(self):
        field = self.source_card
        return (
            field is not None
            and getattr(field, "zone", None) == ZoneType.BATTLE
            and not getattr(field, "d_switch_flipped", False)
        )

    def resolve(self):
        if not self.can_attempt():
            return False

        flip = self.game.choice_manager.select(
            self.player,
            [
                True,
                False,
            ],
            prompt=self.prompt,
        )
        if not flip:
            return False

        self.source_card.d_switch_flipped = True
        return True
