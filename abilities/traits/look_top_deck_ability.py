"""Passive ability: controller may look at top card of their deck at any time."""

from abilities.base.base_ability import BaseAbility
from zones.zone_type import ZoneType


class LookTopDeckDuringTurnAbility(BaseAbility):

    def __init__(self, owner_card):
        super().__init__()
        self.owner_card = owner_card
        self.ability_id = "look_top_of_deck"

    def is_active(self, player):
        return (
            getattr(self.owner_card, "zone", None) == ZoneType.BATTLE
            and getattr(self.owner_card, "owner", None) is player
        )
