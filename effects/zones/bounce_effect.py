"""
クリーチャーをバトルゾーンから手札へ戻す効果（バウンス）を処理するクラス。
"""

# effects/bounce_effect.py

from effects.base.base_effect import (
    BaseEffect
)

from core.protocols import ZoneContext
from core.pending_cards import is_card_pending

from zones.zone_type import (
    ZoneType
)

from ui.card_display import format_card_name


class BounceEffect(
    BaseEffect
):

    def __init__(
        self,
        target,
        game: ZoneContext,
    ):

        super().__init__()

        self.target = target

        self.game = game

    def resolve(self):

        # 不正target
        if self.target.zone != (
            ZoneType.BATTLE
        ) or is_card_pending(self.target):

            print(
                f"{format_card_name(self.target)} "
                f"is no longer "
                f"in battle zone"
            )

            return

        owner = self.target.owner
        target_name = format_card_name(
            self.target
        )

        self.game.card_mover.move(
            card=self.target,
            owner=owner,
            from_zone=ZoneType.BATTLE,
            to_zone=ZoneType.HAND,
            reason="bounce",
        )

        print(
            f"{target_name} "
            f"was bounced"
        )
