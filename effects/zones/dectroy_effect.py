"""
クリーチャーをバトルゾーンから墓地へ移動させる破壊（デストロイ）効果を処理するクラス。
"""

from actions.destroy_action import (
    DestroyAction
)

from effects.base.base_effect import (
    BaseEffect
)

from core.protocols import PlayableContext
from core.pending_cards import is_card_pending

from zones.zone_type import ZoneType


class DestroyEffect(
    BaseEffect
):

    def __init__(
        self,
        target,
        game: PlayableContext,
    ):

        super().__init__()

        self.target = target

        self.game = game

    def resolve(self):

        # 解決時不適正チェック
        if (
            self.target.zone
            != ZoneType.BATTLE
            or is_card_pending(self.target)
        ):

            print(
                "Target is no longer "
                "in battle zone"
            )

            return

        action = DestroyAction(
            self.target.owner,
            self.target,
        )

        self.game.action_processor.process(action)
