"""Shield Saver keyword replacement ability."""

from abilities.base.destroy_self_instead_ability import (
    DestroySelfInsteadAbility,
)
from events.shield_break_attempt_event import ShieldBreakAttemptEvent
from core.pending_cards import is_card_pending
from zones.zone_type import ZoneType


class ShieldSaverAbility(DestroySelfInsteadAbility):

    confirm_prompt = "Use Shield Saver?"

    def applies(
        self,
        event,
    ):
        return (
            isinstance(event, ShieldBreakAttemptEvent)
            and event.player == self.owner_card.owner
            and self.owner_card.zone == ZoneType.BATTLE
            and not is_card_pending(self.owner_card)
        )
