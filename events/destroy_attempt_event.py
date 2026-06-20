"""Destruction attempt event for replacement effects."""

from events.base_event import BaseEvent
from ui.card_display import format_card_name
from zones.zone_type import ZoneType


class DestroyAttemptEvent(BaseEvent):

    def __init__(
        self,
        card,
        owner,
    ):
        super().__init__()
        self.card = card
        self.owner = owner
        self.from_zone = ZoneType.BATTLE
        self.to_zone = ZoneType.GRAVEYARD
        self.reason = "destroy"
        self.replaced = False
        self.cancelled = False

    def __str__(
        self,
    ):
        return (
            "DestroyAttemptEvent("
            f"{format_card_name(self.card)} "
            f"owned by {self.owner.name}"
            ")"
        )
