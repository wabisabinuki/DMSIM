"""このクリーチャーのコントローラーの特定の領域にあるカード1枚につき、
自身のパワーを継続的に強化する常在型能力（PowerPerCardInZoneAbility）を定義。
"""

from abilities.base.continuous_ability import ContinuousAbility
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


_ZONE_NAMES = {
    "deck": ZoneType.DECK,
    "hand": ZoneType.HAND,
    "mana": ZoneType.MANA,
    "battle": ZoneType.BATTLE,
    "battle_zone": ZoneType.BATTLE,
    "shield": ZoneType.SHIELD,
    "graveyard": ZoneType.GRAVEYARD,
}


class PowerPerCardInZoneAbility(ContinuousAbility):

    def __init__(
        self,
        owner_card,
        amount=1000,
        zone="mana",
    ):
        super().__init__()
        self.owner_card = owner_card
        self.amount = amount
        self.zone_type = _ZONE_NAMES.get(
            str(zone).lower(),
            ZoneType.MANA,
        )

    def modify_power(
        self,
        creature,
        power,
    ):
        # 常在型能力はバトルゾーンにいる間だけ機能する。
        if getattr(creature, "zone", None) != ZoneType.BATTLE:
            return power

        owner = getattr(creature, "owner", None)
        if owner is None:
            return power

        zone = owner.get_zone(self.zone_type)

        count = sum(
            1
            for card in zone.cards
            if not is_card_pending(card)
        )

        return power + self.amount * count


def build_power_per_card_in_zone_ability(
    spec,
    card,
    game,
):
    return PowerPerCardInZoneAbility(
        owner_card=card,
        amount=spec.get("amount", 1000),
        zone=spec.get("zone", "mana"),
    )
