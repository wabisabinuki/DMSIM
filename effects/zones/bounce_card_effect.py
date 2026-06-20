"""
バトルゾーンのカード1枚を手札へ戻す効果。
進化クリーチャーをクリーチャーとしてではなくカードとして扱う。
"""

from effects.base.base_effect import (
    BaseEffect
)

from core.pending_cards import is_card_pending

from zones.zone_type import (
    ZoneType
)

from ui.card_display import format_card_name


class BounceCardEffect(BaseEffect):

    def __init__(
        self,
        target,
        game,
    ):
        super().__init__()

        self.target = target
        self.game = game

    def resolve(self):

        if (
            self.target.zone != ZoneType.BATTLE
            or is_card_pending(self.target)
        ):
            print(
                f"{format_card_name(self.target)} "
                "is no longer in battle zone"
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
            reason="bounce_card",
            evolution_mode="card",
        )

        print(
            f"{target_name} "
            "was bounced as a card"
        )
