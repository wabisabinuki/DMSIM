"""エターナル・Ω 置換能力。

このクリーチャーがバトルゾーンを離れる時、かわりに手札に戻す。
破壊（DestroyAttemptEvent）・マナ送り・山札送りなど、離れる移動全般に適用する。
"""

from abilities.base.replacement_ability import ReplacementAbility
from zones.zone_type import ZoneType


class EternalOmegaAbility(ReplacementAbility):

    def __init__(
        self,
        owner_card,
        game,
        label=None,
    ):
        super().__init__()
        self.owner_card = owner_card
        self.game = game
        self.replacement_label = label

    def applies(
        self,
        event,
    ):
        if getattr(event, "card", None) is not self.owner_card:
            return False

        if self.owner_card.zone != ZoneType.BATTLE:
            return False

        if getattr(event, "from_zone", None) != ZoneType.BATTLE:
            return False

        to_zone = getattr(event, "to_zone", None)
        # すでに手札に戻る、またはバトルゾーン内移動なら置換不要。
        return to_zone not in (
            ZoneType.BATTLE,
            ZoneType.HAND,
        )

    def replace(
        self,
        event,
    ):
        event.to_zone = ZoneType.HAND
        return True
